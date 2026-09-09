from dataclasses import dataclass
from uuid import uuid4

from src.api.mat_pal.schemas import (
    AnswerRequest,
    SessionResponse,
)
from src.core.tutor_engine.contracts import (
    StudentSubmission,
    TutorResponse,
)
from src.core.tutor_engine.primary_school.engine import (
    PrimarySchoolTutorEngine,
)
from src.core.tutor_engine.primary_school.reverse_reasoning_solver import (
    load_reverse_reasoning_problem,
)


@dataclass
class StoredSession:
    session_id: str
    problem_id: str
    engine: PrimarySchoolTutorEngine
    last_response: TutorResponse


_sessions: dict[str, StoredSession] = {}


def _to_session_response(
    stored_session: StoredSession,
    tutor_response: TutorResponse,
) -> SessionResponse:
    return SessionResponse(
        session_id=stored_session.session_id,
        problem_id=stored_session.problem_id,
        status=tutor_response.status,
        feedback=tutor_response.feedback,
        current_step=tutor_response.current_step,
        total_steps=tutor_response.total_steps,
        completed=tutor_response.completed,
        hint_available=tutor_response.hint_available,
        expected_input_type=tutor_response.expected_input_type,
        suggestion=tutor_response.suggestion,
        metadata=tutor_response.metadata,
    )


def start_session(
    problem_id: str,
) -> SessionResponse:
    problem = load_reverse_reasoning_problem(
        problem_id
    )
    engine = PrimarySchoolTutorEngine(
        problem=problem
    )
    initial_response = engine.get_current_response()

    session_id = str(
        uuid4()
    )
    stored_session = StoredSession(
        session_id=session_id,
        problem_id=problem_id,
        engine=engine,
        last_response=initial_response,
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
    stored_session.last_response = tutor_response

    return _to_session_response(
        stored_session,
        tutor_response,
    )
