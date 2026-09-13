from dataclasses import dataclass
from uuid import uuid4

from src.api.mat_pal import adaptive_service
from src.core.student_model.progress_store import (
    DEFAULT_STUDENT_ID,
    normalize_student_id,
)
from src.api.mat_pal.schemas import (
    AnswerRequest,
    SessionResponse,
)
from src.api.mat_pal.generated_problem_store import (
    get_generated_problem,
)
from src.api.mat_pal.tutor_registry import (
    DEFAULT_TUTOR_REGISTRY,
    TutorRegistration,
    TutorEngine,
)
from src.core.adaptive import (
    SessionPerformanceSummary,
)
from src.core.tutor_engine.contracts import (
    StudentSubmission,
    TutorResponse,
)


@dataclass
class StoredSession:
    session_id: str
    problem_id: str
    problem_title: str
    problem_statement: str
    registration: TutorRegistration
    engine: TutorEngine
    last_response: TutorResponse
    student_id: str = DEFAULT_STUDENT_ID
    answer_submissions: int = 0
    incorrect_submissions: int = 0
    hint_requests: int = 0
    mastery_updated: bool = False


_sessions: dict[str, StoredSession] = {}


def _to_session_response(
    stored_session: StoredSession,
    tutor_response: TutorResponse,
) -> SessionResponse:
    return SessionResponse(
        session_id=stored_session.session_id,
        problem_id=stored_session.problem_id,
        problem_title=stored_session.problem_title,
        problem_statement=(
            stored_session.problem_statement
        ),
        status=tutor_response.status,
        feedback=tutor_response.feedback,
        current_step=tutor_response.current_step,
        total_steps=tutor_response.total_steps,
        completed=tutor_response.completed,
        hint_available=tutor_response.hint_available,
        expected_input_type=tutor_response.expected_input_type,
        suggestion=tutor_response.suggestion,
        metadata={
            **tutor_response.metadata,
            "student_id": stored_session.student_id,
        },
    )


def start_session(
    problem_id: str,
    student_id: str = DEFAULT_STUDENT_ID,
) -> SessionResponse:
    try:
        registration = DEFAULT_TUTOR_REGISTRY.get(
            problem_id
        )
        engine = DEFAULT_TUTOR_REGISTRY.create_engine(
            problem_id
        )

    except ValueError:
        registration = get_generated_problem(
            problem_id
        )

        if registration is None:
            raise

        engine = registration.create_engine()
    initial_response = engine.get_current_response()

    session_id = str(
        uuid4()
    )
    stored_session = StoredSession(
        session_id=session_id,
        problem_id=problem_id,
        problem_title=registration.title,
        problem_statement=(
            registration.problem_statement
        ),
        engine=engine,
        last_response=initial_response,
        registration=registration,
        student_id=normalize_student_id(student_id),
    )
    _sessions[session_id] = stored_session

    return _to_session_response(
        stored_session,
        initial_response,
    )


def get_session(
    session_id: str,
) -> SessionResponse | None:
    stored_session = _sessions.get(
        session_id
    )

    if stored_session is None:
        return None

    return _to_session_response(
        stored_session,
        stored_session.last_response,
    )


def submit_answer(
    session_id: str,
    answer_request: AnswerRequest,
) -> SessionResponse | None:
    stored_session = _sessions.get(
        session_id
    )

    if stored_session is None:
        return None

    tutor_response = stored_session.engine.submit(
        StudentSubmission(
            answer=answer_request.answer,
            input_type=answer_request.input_type,
            metadata=answer_request.metadata,
        )
    )
    stored_session.answer_submissions += 1

    if tutor_response.status == "incorrect":
        stored_session.incorrect_submissions += 1

    stored_session.last_response = tutor_response

    _update_mastery_if_completed(
        stored_session,
        tutor_response,
    )

    return _to_session_response(
        stored_session,
        tutor_response,
    )


def request_hint(
    session_id: str,
) -> SessionResponse | None:
    stored_session = _sessions.get(
        session_id
    )

    if stored_session is None:
        return None

    tutor_response = (
        stored_session.engine.request_hint()
    )
    stored_session.hint_requests += 1
    stored_session.last_response = tutor_response

    return _to_session_response(
        stored_session,
        tutor_response,
    )


def _update_mastery_if_completed(
    stored_session: StoredSession,
    tutor_response: TutorResponse,
) -> None:
    if (
        stored_session.mastery_updated
        or not tutor_response.completed
    ):
        return

    summary = _build_performance_summary(
        stored_session,
        tutor_response,
    )
    updated = (
        adaptive_service.record_session_completion(
            summary,
            student_id=stored_session.student_id,
        )
    )
    tutor_response.metadata = {
        **tutor_response.metadata,
        "performance_summary": (
            summary.__dict__
        ),
        "mastery": updated["mastery"],
        "mastery_key": summary.mastery_key,
    }
    stored_session.mastery_updated = True


def _build_performance_summary(
    stored_session: StoredSession,
    tutor_response: TutorResponse,
) -> SessionPerformanceSummary:
    registration = stored_session.registration
    metadata = registration.metadata or {}
    mastery_key = (
        adaptive_service.mastery_key_for_registration(
            registration
        )
    )
    first_attempt_success = (
        tutor_response.completed
        and stored_session.incorrect_submissions == 0
        and stored_session.hint_requests == 0
    )

    return SessionPerformanceSummary(
        problem_id=stored_session.problem_id,
        subject=registration.subject,
        domain=registration.domain,
        topic=registration.topic,
        difficulty=metadata.get("difficulty"),
        mastery_key=mastery_key,
        completed=tutor_response.completed,
        total_attempts=(
            stored_session.answer_submissions
        ),
        incorrect_attempts=(
            stored_session.incorrect_submissions
        ),
        hints_used=stored_session.hint_requests,
        first_attempt_success=first_attempt_success,
        steps_completed=tutor_response.current_step,
        total_steps=tutor_response.total_steps,
        metadata={
            "generated": bool(
                metadata.get("generated", False)
            ),
            "problem_type": registration.problem_type,
        },
    )
