import threading
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
    QuestionRoute,
    QuestionTurn,
    TutorQuestionContext,
    TutorQuestionRequest,
    build_question_engine_from_env,
)
from src.core.question_engine.context import sanitize_tutor_metadata
from src.core.question_engine.guided_elaboration import (
    STATUS_DUPLICATE,
    STATUS_FAILED,
    STATUS_OFF,
    STATUS_STALE,
    STATUS_UNAVAILABLE,
    STATUS_UNSUPPORTED,
    elaboration_is_available,
    render_guided_strategy,
    select_guided_strategy,
)
from src.core.question_engine.guided_questions import (
    GuidedQuestionError,
    list_suggested_questions,
    resolve_guided_question,
    suggested_as_dicts,
)
from src.core.question_engine.sources import public_sources
from src.core.tutor_engine.contracts import (
    StudentSubmission,
    TutorResponse,
)
from src.core.tutor_engine.primary_school.generation.word_problems.templates import (
    TEMPLATES_BY_ID,
)


MAX_QUESTION_HISTORY = 3

_question_engine: GeneralTutorQuestionEngine | None = None
_elaboration_guard = threading.Lock()


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
    elaboration_in_flight: bool = False


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
        suggested_questions=suggested_as_dicts(
            _live_suggested_questions(stored_session)
        ),
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
    question_id = (question_request.question_id or "").strip()
    if question_id:
        explanation_mode = (
            question_request.explanation_mode or "local"
        )
        return _submit_guided_question(
            stored_session,
            question_id=question_id,
            live_response=live_response,
            context=context,
            language=language,
            explanation_mode=explanation_mode,
        )
    question_text = " ".join(
        (question_request.question or "").split()
    ).strip()
    if not question_text:
        raise GuidedQuestionError(
            "Provide a question or a question_id."
        )
    result = get_question_engine().answer(
        TutorQuestionRequest(
            question=question_text,
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
            question=question_text,
            answer=result.answer,
            answer_source=result.answer_source,
        )
    )
    stored_session.last_response = tutor_response

    return _to_session_response(
        stored_session,
        tutor_response,
    )


def _submit_guided_question(
    stored_session: StoredSession,
    *,
    question_id: str,
    live_response: TutorResponse,
    context: TutorQuestionContext,
    language: str,
    explanation_mode: str = "local",
) -> SessionResponse | None:
    items = _live_suggested_questions(stored_session)
    allowed = {item.question_id for item in items}
    label, answer = resolve_guided_question(
        question_id,
        allowed_ids=allowed,
        topic=stored_session.registration.topic,
        problem=getattr(stored_session.engine, "problem", None),
        live_response=live_response,
        context=context,
        language=language,
    )
    if explanation_mode == "elaborate":
        return _submit_guided_elaboration(
            stored_session,
            question_id=question_id,
            live_response=live_response,
            language=language,
            local_answer=answer,
        )
    provider_available = (
        get_question_engine().model_provider.is_available()
    )
    tutor_response = TutorResponse(
        status="concept",
        feedback=answer,
        current_step=live_response.current_step,
        total_steps=live_response.total_steps,
        completed=live_response.completed,
        hint_available=live_response.hint_available,
        suggestion=question_continue_message(language),
        expected_input_type=live_response.expected_input_type,
        sources=[],
        metadata={
            **live_response.metadata,
            "concept_question": True,
            "answer_source": "local",
            "used_web": False,
            "question_route": QuestionRoute.LOCAL_ONLY.value,
            "guided_question": True,
            "guided_question_id": question_id,
            "guided_local_explanation": answer,
            "elaboration_available": elaboration_is_available(
                question_id,
                provider_available=provider_available,
            ),
            "mathematical_source": "deterministic_backend",
            "explanation_selected_by_model": False,
        },
    )
    stored_session.question_history.append(
        QuestionTurn(
            question=label,
            answer=answer,
            answer_source="local",
        )
    )
    stored_session.last_response = tutor_response
    return _to_session_response(
        stored_session,
        tutor_response,
    )


def _submit_guided_elaboration(
    stored_session: StoredSession,
    *,
    question_id: str,
    live_response: TutorResponse,
    language: str,
    local_answer: str,
) -> SessionResponse | None:
    provider = get_question_engine().model_provider
    provider_available = provider.is_available()
    if not elaboration_is_available(
        question_id,
        provider_available=provider_available,
    ):
        status = _elaboration_unavailable_status(
            question_id,
            provider_available=provider_available,
        )
        return _keep_guided_explanation(
            stored_session,
            question_id=question_id,
            local_answer=local_answer,
            live_response=live_response,
            language=language,
            status=status,
        )
    if not _try_begin_elaboration(stored_session):
        return _keep_guided_explanation(
            stored_session,
            question_id=question_id,
            local_answer=local_answer,
            live_response=live_response,
            language=language,
            status=STATUS_DUPLICATE,
        )
    captured = {
        "session_id": stored_session.session_id,
        "problem_id": stored_session.problem_id,
        "current_step": live_response.current_step,
        "question_id": question_id,
    }
    try:
        selection = select_guided_strategy(
            question_id,
            language=language,
            model_provider=provider,
        )
    finally:
        _end_elaboration(stored_session)

    live_stored = _sessions.get(captured["session_id"])
    if live_stored is None:
        return None
    live = live_stored.engine.get_current_response()
    allowed = {
        item.question_id
        for item in _live_suggested_questions(live_stored)
    }
    if (
        live_stored.problem_id != captured["problem_id"]
        or live.current_step != captured["current_step"]
        or captured["question_id"] not in allowed
    ):
        if (
            live.current_step == captured["current_step"]
            and live_stored.problem_id == captured["problem_id"]
            and (live_stored.last_response.metadata or {}).get(
                "guided_question_id"
            )
            == captured["question_id"]
        ):
            return _keep_guided_explanation(
                live_stored,
                question_id=question_id,
                local_answer=local_answer,
                live_response=live,
                language=language,
                status=STATUS_STALE,
            )
        return _to_session_response(
            live_stored,
            live_stored.last_response,
        )
    original = _guided_local_explanation(
        live_stored,
        question_id=question_id,
        local_answer=local_answer,
    )
    if selection is None:
        return _keep_guided_explanation(
            live_stored,
            question_id=question_id,
            local_answer=original,
            live_response=live,
            language=language,
            status=STATUS_FAILED,
        )
    rendered = render_guided_strategy(
        question_id,
        selection,
        language=language,
        problem=getattr(live_stored.engine, "problem", None),
        live_response=live,
    )
    if not rendered:
        return _keep_guided_explanation(
            live_stored,
            question_id=question_id,
            local_answer=original,
            live_response=live,
            language=language,
            status=STATUS_FAILED,
        )
    extra = {
        "elaboration_status": "applied",
        "elaboration_strategy": selection.strategy,
        "explanation_selected_by_model": True,
        "mathematical_source": "deterministic_backend",
        "guided_local_explanation": original,
        "guided_question_id": question_id,
        "elaboration_available": True,
    }
    if selection.example_id is not None:
        extra["elaboration_example_id"] = selection.example_id
    return _replace_guided_explanation(
        live_stored,
        question_id=question_id,
        explanation=rendered,
        live_response=live,
        language=language,
        extra_metadata=extra,
    )


def _elaboration_unavailable_status(
    question_id: str,
    *,
    provider_available: bool,
) -> str:
    from src.core.question_engine.guided_elaboration import (
        ELABORATABLE_QUESTION_IDS,
        guided_ai_mode,
    )

    if guided_ai_mode() != "optional":
        return STATUS_OFF
    if not provider_available:
        return STATUS_UNAVAILABLE
    if question_id not in ELABORATABLE_QUESTION_IDS:
        return STATUS_UNSUPPORTED
    return STATUS_UNAVAILABLE


def _try_begin_elaboration(stored_session: StoredSession) -> bool:
    with _elaboration_guard:
        if stored_session.elaboration_in_flight:
            return False
        stored_session.elaboration_in_flight = True
        return True


def _end_elaboration(stored_session: StoredSession) -> None:
    with _elaboration_guard:
        stored_session.elaboration_in_flight = False


def _guided_local_explanation(
    stored_session: StoredSession,
    *,
    question_id: str,
    local_answer: str,
) -> str:
    metadata = stored_session.last_response.metadata or {}
    original = metadata.get("guided_local_explanation")
    if (
        isinstance(original, str)
        and original
        and metadata.get("guided_question_id") == question_id
    ):
        return original
    if (
        stored_session.last_response.status == "concept"
        and metadata.get("guided_question_id") == question_id
        and stored_session.last_response.feedback
    ):
        return stored_session.last_response.feedback
    return local_answer


def _keep_guided_explanation(
    stored_session: StoredSession,
    *,
    question_id: str,
    local_answer: str,
    live_response: TutorResponse,
    language: str,
    status: str,
) -> SessionResponse:
    current = stored_session.last_response
    if current.status == "concept" and current.feedback:
        metadata = {
            **(current.metadata or {}),
            "elaboration_status": status,
            "mathematical_source": "deterministic_backend",
            "explanation_selected_by_model": False,
        }
        if (current.metadata or {}).get("guided_question_id") == (
            question_id
        ):
            metadata["guided_local_explanation"] = (
                _guided_local_explanation(
                    stored_session,
                    question_id=question_id,
                    local_answer=local_answer,
                )
            )
        current.metadata = metadata
        stored_session.last_response = current
    return _to_session_response(stored_session, current)


def _replace_guided_explanation(
    stored_session: StoredSession,
    *,
    question_id: str,
    explanation: str,
    live_response: TutorResponse,
    language: str,
    extra_metadata: dict,
) -> SessionResponse:
    current = stored_session.last_response
    base_metadata = dict(current.metadata or {})
    if current.status != "concept":
        base_metadata = dict(live_response.metadata or {})
    provider_available = (
        get_question_engine().model_provider.is_available()
    )
    tutor_response = TutorResponse(
        status="concept",
        feedback=explanation,
        current_step=live_response.current_step,
        total_steps=live_response.total_steps,
        completed=live_response.completed,
        hint_available=live_response.hint_available,
        suggestion=question_continue_message(language),
        expected_input_type=live_response.expected_input_type,
        sources=[],
        metadata={
            **base_metadata,
            "concept_question": True,
            "answer_source": "local",
            "used_web": False,
            "question_route": QuestionRoute.LOCAL_ONLY.value,
            "guided_question": True,
            "guided_question_id": question_id,
            "elaboration_available": elaboration_is_available(
                question_id,
                provider_available=provider_available,
            ),
            **extra_metadata,
        },
    )
    stored_session.last_response = tutor_response
    return _to_session_response(stored_session, tutor_response)


def _live_suggested_questions(
    stored_session: StoredSession,
):
    live_response = stored_session.engine.get_current_response()
    return list_suggested_questions(
        topic=stored_session.registration.topic,
        problem=getattr(stored_session.engine, "problem", None),
        live_response=live_response,
        language=stored_session.language,
        completed=live_response.completed,
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
    metadata = tutor_response.metadata or {}
    counted = True
    if "hint_counted" in metadata:
        counted = bool(metadata["hint_counted"])
    if counted:
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
    metadata = sanitize_tutor_metadata(metadata)
    metadata.update(
        _story_question_snapshot(
            stored_session,
            live_response,
        )
    )
    metadata.update(
        _logical_question_snapshot(
            stored_session,
            live_response,
        )
    )
    return metadata


def _story_question_snapshot(
    stored_session: StoredSession,
    live_response: TutorResponse,
) -> dict:
    problem = getattr(stored_session.engine, "problem", None)
    if getattr(problem, "topic", "") != "story_problems":
        return {}
    known = getattr(problem, "known", None) or {}
    template_id = known.get("template_id")
    if not template_id:
        return {}
    template = TEMPLATES_BY_ID.get(template_id)
    params = known.get("statement_params") or {}
    if template is not None:
        statement_ids = template.statement_ids
    else:
        statement_ids = known.get("statement_ids") or tuple(
            params.keys()
        )
    visible = {
        name: int(params[name])
        for name in statement_ids
        if name in params and isinstance(params[name], int)
        and not isinstance(params[name], bool)
        and params[name] > 0
    }
    disclosed = dict(visible)
    completed_ids = []
    current_step = live_response.current_step
    for step in getattr(problem, "solution_steps", ()) or ():
        if step.step_number >= current_step:
            continue
        key = (step.metadata or {}).get("prompt_key") or ""
        if "." not in str(key):
            continue
        quantity_id = str(key).rsplit(".", 1)[-1]
        completed_ids.append(quantity_id)
        value = step.expected_answer
        if (
            quantity_id
            and isinstance(value, int)
            and not isinstance(value, bool)
            and value > 0
        ):
            disclosed[quantity_id] = int(value)
    prompt_key = ""
    current = None
    session = getattr(stored_session.engine, "session", None)
    if session is not None:
        current = session.get_current_step()
    if current is not None:
        prompt_key = (current.metadata or {}).get("prompt_key") or ""
    return {
        "template_id": template_id,
        "family": known.get("family"),
        "prompt_key": prompt_key,
        "story_visible": visible,
        "disclosed_values": disclosed,
        "completed_quantity_ids": completed_ids,
    }


def _logical_question_snapshot(
    stored_session: StoredSession,
    live_response: TutorResponse,
) -> dict:
    problem = getattr(stored_session.engine, "problem", None)
    if getattr(problem, "topic", "") != "logical_reasoning":
        return {}
    known = getattr(problem, "known", None) or {}
    current = None
    session = getattr(stored_session.engine, "session", None)
    if session is not None:
        current = session.get_current_step()
    meta = dict((current.metadata or {}) if current is not None else {})
    params = dict(meta.get("params") or {})
    return {
        "family": known.get("family"),
        "difficulty": known.get("difficulty"),
        "public_clues": list(known.get("public_clues") or ()),
        "clue_kinds": list(known.get("clue_kinds") or ()),
        "visible_numbers": list(known.get("visible_numbers") or ()),
        "target_object": known.get("target_object"),
        "milestone": meta.get("milestone"),
        "purpose": meta.get("purpose"),
        "prompt_key": meta.get("prompt_key") or "",
        "params": params,
        "logic_params": params,
    }


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
