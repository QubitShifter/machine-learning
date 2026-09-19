from collections import deque
from dataclasses import dataclass, field
from uuid import uuid4

from src.core.i18n.locale import normalize_locale
from src.core.i18n.question import question_continue_message
from src.api.mat_pal import adaptive_service
from src.core.student_model.progress_store import (
    DEFAULT_STUDENT_ID,
    normalize_student_id,
)
from src.api.mat_pal.schemas import (
    AnswerRequest,
    QuestionRequest,
    SessionResponse,
    TutorSourceModel,
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
from src.core.question_engine import (
    GeneralTutorQuestionEngine,
    QuestionTurn,
    TutorQuestionContext,
    TutorQuestionRequest,
    build_question_engine_from_env,
)
from src.core.question_engine.context import sanitize_tutor_metadata
from src.core.question_engine.sources import public_sources
from src.core.tutor_engine.contracts import (
    StudentSubmission,
    TutorResponse,
)


MAX_QUESTION_HISTORY = 3

_question_engine: GeneralTutorQuestionEngine | None = None


def get_question_engine() -> GeneralTutorQuestionEngine:
    global _question_engine

    if _question_engine is None:
        _question_engine = build_question_engine_from_env()

    return _question_engine


def set_question_engine(
    engine: GeneralTutorQuestionEngine | None,
) -> None:
    global _question_engine
    _question_engine = engine


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
    language: str = "en"
    answer_submissions: int = 0
    incorrect_submissions: int = 0
    hint_requests: int = 0
    mastery_updated: bool = False
    question_history: deque[QuestionTurn] = field(
        default_factory=lambda: deque(
            maxlen=MAX_QUESTION_HISTORY,
        )
    )


_sessions: dict[str, StoredSession] = {}


def _to_session_response(
    stored_session: StoredSession,
    tutor_response: TutorResponse,
) -> SessionResponse:
    sources = [
        TutorSourceModel(
            title=str(item.get("title") or ""),
            url=str(item.get("url") or ""),
            domain=item.get("domain"),
        )
        for item in (
            tutor_response.sources or []
        )
        if isinstance(item, dict) and item.get("url")
    ]

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
        sources=sources,
        metadata={
            **tutor_response.metadata,
            "student_id": stored_session.student_id,
        },
    )


def start_session(
    problem_id: str,
    student_id: str = DEFAULT_STUDENT_ID,
    language: str = "en",
) -> SessionResponse:
    locale = normalize_locale(language)
    try:
        registration = DEFAULT_TUTOR_REGISTRY.get(
            problem_id
        )
        engine = DEFAULT_TUTOR_REGISTRY.create_engine(
            problem_id,
            language=locale,
        )

    except ValueError:
        registration = get_generated_problem(
            problem_id
        )

        if registration is None:
            raise

        engine = registration.create_engine(locale)
    initial_response = engine.get_current_response()
    problem_title = getattr(
        engine,
        "problem_title",
        registration.title,
    )
    problem_statement = getattr(
        engine,
        "problem_statement",
        registration.problem_statement,
    )

    session_id = str(
        uuid4()
    )
    stored_session = StoredSession(
        session_id=session_id,
        problem_id=problem_id,
        problem_title=problem_title,
        problem_statement=problem_statement,
        engine=engine,
        last_response=initial_response,
        registration=registration,
        student_id=normalize_student_id(student_id),
        language=locale,
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

    if tutor_response.status != "concept":
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


def submit_question(
    session_id: str,
    question_request: QuestionRequest,
) -> SessionResponse | None:
    stored_session = _sessions.get(
        session_id
    )

    if stored_session is None:
        return None

    live_response = (
        stored_session.engine.get_current_response()
    )
    registration = stored_session.registration
    language = normalize_locale(
        getattr(
            stored_session.engine,
            "language",
            stored_session.language,
        )
    )
    context = TutorQuestionContext(
        language=language,
        subject=registration.subject,
        domain=registration.domain,
        topic=registration.topic,
        problem_id=stored_session.problem_id,
        problem_title=stored_session.problem_title,
        problem_statement=(
            stored_session.problem_statement
        ),
        current_step=live_response.current_step,
        total_steps=live_response.total_steps,
        current_prompt=live_response.feedback,
        expected_input_type=(
            live_response.expected_input_type
        ),
        tutor_metadata=_question_tutor_metadata(
            stored_session,
            live_response,
        ),
        recent_question_history=tuple(
            stored_session.question_history
        ),
        session_id=stored_session.session_id,
        student_id=stored_session.student_id,
    )
    result = get_question_engine().answer(
        TutorQuestionRequest(
            question=question_request.question,
        ),
        context,
    )
    tutor_response = TutorResponse(
        status="concept",
        feedback=result.answer,
        current_step=live_response.current_step,
        total_steps=live_response.total_steps,
        completed=live_response.completed,
        hint_available=live_response.hint_available,
        suggestion=(
            result.metadata.get("suggestion")
            or question_continue_message(language)
        ),
        expected_input_type=(
            live_response.expected_input_type
        ),
        sources=public_sources(result.sources),
        metadata={
            **live_response.metadata,
            "concept_question": True,
            "answer_source": result.answer_source,
            "used_web": result.used_web,
            "question_route": result.route.value,
        },
    )
    stored_session.question_history.append(
        QuestionTurn(
            question=" ".join(
                question_request.question.split()
            ).strip(),
            answer=result.answer,
            answer_source=result.answer_source,
        )
    )
    stored_session.last_response = tutor_response

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


def _question_tutor_metadata(
    stored_session: StoredSession,
    live_response: TutorResponse,
) -> dict:
    metadata = dict(live_response.metadata or {})
    metadata["exercise_completed"] = bool(
        live_response.completed
    )
    problem = getattr(stored_session.engine, "problem", None)
    known = getattr(problem, "known", None)
    if isinstance(known, dict):
        for key in ("form", "equation"):
            value = known.get(key)
            if value is not None and key not in metadata:
                metadata[key] = value
    return sanitize_tutor_metadata(metadata)


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
