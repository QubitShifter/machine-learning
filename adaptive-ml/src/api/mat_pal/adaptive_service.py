from pathlib import Path

from src.api.mat_pal.problem_generation import (
    DEFAULT_PROBLEM_GENERATOR_REGISTRY,
)
from src.api.mat_pal.tutor_registry import (
    DEFAULT_TUTOR_REGISTRY,
    TutorRegistration,
)
from src.core.adaptive import (
    AdaptiveRecommendation,
    AdaptiveTopicState,
    RuleBasedAdaptivePolicy,
    SessionPerformanceSummary,
)
from src.core.adaptive.features import (
    build_adaptive_features,
    parse_recent_sessions,
)
from src.core.student_model.progress_store import (
    DEFAULT_PROGRESS_PATH,
    get_skill_progress,
    load_progress,
    save_progress,
    update_skill_progress,
)
from src.core.student_model.student import (
    StudentModel,
)


DEFAULT_STUDENT_ID = "local_student"

TOPIC_MASTERY_KEYS = {
    (
        "mathematics",
        "primary_school",
        "word_problems",
    ): "grade4_reverse_reasoning",
    (
        "mathematics",
        "ode",
        "first_order_linear",
    ): "linear_first_order_ode",
    (
        "mathematics",
        "ode",
        "separable_equations",
    ): "separable_equations",
}


def mastery_key_for_registration(
    registration: TutorRegistration,
) -> str:
    mapped = TOPIC_MASTERY_KEYS.get(
        (
            registration.subject,
            registration.domain,
            registration.topic,
        )
    )

    if mapped is not None:
        return mapped

    if registration.skills:
        return registration.skills[0]

    return registration.topic


def record_session_completion(
    summary: SessionPerformanceSummary,
    path: Path = DEFAULT_PROGRESS_PATH,
) -> dict:
    progress = load_progress(path)
    current = get_skill_progress(
        progress,
        summary.mastery_key,
    )

    student = StudentModel(
        student_id=DEFAULT_STUDENT_ID
    )
    student.initialize_skill(
        skill_id=summary.mastery_key,
        initial_mastery=current["mastery"],
    )

    mastery_attempts = (
        1
        if summary.first_attempt_success
        else 2
        if summary.incorrect_attempts <= 1
        else 3
    )
    updated_mastery = (
        student.update_mastery_after_question(
            skill_id=summary.mastery_key,
            attempts=mastery_attempts,
            final_evaluation={
                "correct": summary.completed,
                "parse_error": False,
            },
        )
    )
    questions_completed = (
        current["questions_completed"] + 1
        if summary.completed
        else current["questions_completed"]
    )
    first_attempt_streak = (
        current["first_attempt_streak"] + 1
        if summary.first_attempt_success
        else 0
    )
    recent_session = (
        {
            "completed": True,
            "total_attempts": summary.total_attempts,
            "incorrect_attempts": (
                summary.incorrect_attempts
            ),
            "hints_used": summary.hints_used,
            "first_attempt_success": (
                summary.first_attempt_success
            ),
            "steps_completed": summary.steps_completed,
            "total_steps": summary.total_steps,
        }
        if summary.completed
        else None
    )

    update_skill_progress(
        progress=progress,
        skill=summary.mastery_key,
        mastery=updated_mastery,
        questions_completed=questions_completed,
        first_attempt_streak=first_attempt_streak,
        last_total_attempts=summary.total_attempts,
        last_incorrect_attempts=summary.incorrect_attempts,
        last_hints_used=summary.hints_used,
        last_first_attempt_success=(
            summary.first_attempt_success
        ),
        last_completed=summary.completed,
        recent_session=recent_session,
    )
    save_progress(
        progress,
        path,
    )

    return get_skill_progress(
        progress,
        summary.mastery_key,
    )


def recommend_next(
    subject: str | None = None,
    domain: str | None = None,
    path: Path = DEFAULT_PROGRESS_PATH,
) -> AdaptiveRecommendation:
    candidates = list_topic_states(
        subject=subject,
        domain=domain,
        path=path,
    )

    return RuleBasedAdaptivePolicy().recommend_next(
        candidates
    )


def list_topic_states(
    subject: str | None,
    domain: str | None,
    path: Path,
) -> list[AdaptiveTopicState]:
    progress = load_progress(path)
    topics: dict[
        tuple[str, str, str],
        TutorRegistration,
    ] = {}

    for registration in (
        DEFAULT_TUTOR_REGISTRY
        .list_registrations(catalog_visible=True)
    ):
        if (
            subject is not None
            and registration.subject != subject
        ):
            continue

        if (
            domain is not None
            and registration.domain != domain
        ):
            continue

        key = (
            registration.subject,
            registration.domain,
            registration.topic,
        )
        topics.setdefault(
            key,
            registration,
        )

    return [
        _topic_state_from_registration(
            registration,
            progress,
        )
        for registration in topics.values()
    ]


def _topic_state_from_registration(
    registration: TutorRegistration,
    progress: dict,
) -> AdaptiveTopicState:
    mastery_key = mastery_key_for_registration(
        registration
    )
    skill_progress = get_skill_progress(
        progress,
        mastery_key,
    )
    supported_difficulties = (
        DEFAULT_PROBLEM_GENERATOR_REGISTRY
        .supported_difficulties(
            subject=registration.subject,
            domain=registration.domain,
            topic=registration.topic,
        )
    )
    generation_available = bool(
        supported_difficulties
    )
    last_total_attempts = skill_progress.get(
        "last_total_attempts",
        0,
    )
    last_incorrect_attempts = skill_progress.get(
        "last_incorrect_attempts",
        0,
    )
    last_hints_used = skill_progress.get(
        "last_hints_used",
        0,
    )
    last_first_attempt_success = skill_progress.get(
        "last_first_attempt_success",
        False,
    )
    last_completed = skill_progress.get(
        "last_completed",
        False,
    )
    recent_sessions = parse_recent_sessions(
        skill_progress.get("recent_sessions", [])
    )
    features = build_adaptive_features(
        mastery=skill_progress["mastery"],
        questions_completed=(
            skill_progress["questions_completed"]
        ),
        first_attempt_streak=(
            skill_progress["first_attempt_streak"]
        ),
        last_total_attempts=last_total_attempts,
        last_incorrect_attempts=(
            last_incorrect_attempts
        ),
        last_hints_used=last_hints_used,
        last_first_attempt_success=(
            last_first_attempt_success
        ),
        last_completed=last_completed,
        recent_sessions=recent_sessions,
    )

    return AdaptiveTopicState(
        subject=registration.subject,
        domain=registration.domain,
        topic=registration.topic,
        topic_name=registration.topic_name,
        mastery_key=mastery_key,
        mastery=skill_progress["mastery"],
        questions_completed=(
            skill_progress["questions_completed"]
        ),
        first_attempt_streak=(
            skill_progress["first_attempt_streak"]
        ),
        supported_difficulties=tuple(
            supported_difficulties
        ),
        generation_available=generation_available,
        problem_id=(
            None
            if generation_available
            else registration.problem_id
        ),
        last_total_attempts=last_total_attempts,
        last_incorrect_attempts=(
            last_incorrect_attempts
        ),
        last_hints_used=last_hints_used,
        last_first_attempt_success=(
            last_first_attempt_success
        ),
        last_completed=last_completed,
        recent_sessions=recent_sessions,
        features=features,
    )
