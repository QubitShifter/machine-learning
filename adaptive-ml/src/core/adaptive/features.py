from dataclasses import dataclass
from typing import Sequence


RECENT_HISTORY_LIMIT = 5
MIN_RECENT_SESSIONS_FOR_TREND = 2

LOGICAL_REASONING_HISTORY_FAMILIES = frozenset(
    {
        "number_detective",
        "distribution_puzzles",
        "logic_detective",
    }
)

STRONG_FIRST_ATTEMPT_RATE = 0.75
STRONG_MAX_HINT_RATE = 0.25
STRONG_MAX_INCORRECT_RATE = 0.25

WEAK_HINT_RATE = 0.50
WEAK_INCORRECT_RATE = 0.50
WEAK_AVERAGE_ATTEMPTS_PER_STEP = 2.0

TREND_STRONG = "strong"
TREND_STABLE = "stable"
TREND_NEEDS_SUPPORT = "needs_support"
TREND_INSUFFICIENT = "insufficient_history"


@dataclass(frozen=True)
class RecentSession:
    completed: bool = False
    total_attempts: int = 0
    incorrect_attempts: int = 0
    hints_used: int = 0
    first_attempt_success: bool = False
    steps_completed: int = 0
    total_steps: int = 0
    family: str | None = None
    difficulty: int | None = None
    invalid_attempts: int = 0


@dataclass(frozen=True)
class AdaptivePerformanceFeatures:
    mastery: float
    questions_completed: int
    first_attempt_streak: int
    recent_session_count: int
    recent_completion_rate: float
    recent_first_attempt_success_rate: float
    recent_hint_rate: float
    recent_incorrect_rate: float
    recent_average_attempts_per_step: float
    last_total_attempts: int
    last_incorrect_attempts: int
    last_hints_used: int
    last_first_attempt_success: bool
    last_completed: bool
    has_recent_history: bool
    has_enough_recent_history: bool
    recent_trend: str


def normalize_history_family(
    value: object,
) -> str | None:
    if not isinstance(value, str):
        return None

    family = value.strip()
    if family in LOGICAL_REASONING_HISTORY_FAMILIES:
        return family

    return None


def normalize_history_difficulty(
    value: object,
) -> int | None:
    if value is None or isinstance(value, bool):
        return None

    try:
        difficulty = int(value)
    except (TypeError, ValueError):
        return None

    if difficulty < 1:
        return None

    return difficulty


def recent_session_to_dict(
    session: RecentSession,
) -> dict:
    payload = {
        "completed": bool(session.completed),
        "total_attempts": int(
            session.total_attempts
        ),
        "incorrect_attempts": int(
            session.incorrect_attempts
        ),
        "hints_used": int(session.hints_used),
        "first_attempt_success": bool(
            session.first_attempt_success
        ),
        "steps_completed": int(
            session.steps_completed
        ),
        "total_steps": int(session.total_steps),
        "invalid_attempts": int(
            session.invalid_attempts
        ),
    }
    if session.family is not None:
        payload["family"] = session.family
    if session.difficulty is not None:
        payload["difficulty"] = session.difficulty
    return payload


def parse_recent_session(
    raw: object,
) -> RecentSession | None:
    if isinstance(raw, RecentSession):
        return raw

    if not isinstance(raw, dict):
        return None

    return RecentSession(
        completed=bool(
            raw.get("completed", False)
        ),
        total_attempts=int(
            raw.get("total_attempts", 0) or 0
        ),
        incorrect_attempts=int(
            raw.get("incorrect_attempts", 0) or 0
        ),
        hints_used=int(
            raw.get("hints_used", 0) or 0
        ),
        first_attempt_success=bool(
            raw.get("first_attempt_success", False)
        ),
        steps_completed=int(
            raw.get("steps_completed", 0) or 0
        ),
        total_steps=int(
            raw.get("total_steps", 0) or 0
        ),
        family=normalize_history_family(
            raw.get("family")
        ),
        difficulty=normalize_history_difficulty(
            raw.get("difficulty")
        ),
        invalid_attempts=int(
            raw.get("invalid_attempts", 0) or 0
        ),
    )


def parse_recent_sessions(
    raw: object,
) -> tuple[RecentSession, ...]:
    if not isinstance(raw, list):
        return ()

    sessions: list[RecentSession] = []
    for item in raw[-RECENT_HISTORY_LIMIT:]:
        session = parse_recent_session(item)
        if session is not None:
            sessions.append(session)

    return tuple(sessions)


def bound_recent_sessions(
    sessions: Sequence[object],
) -> list[dict]:
    bounded: list[dict] = []
    for item in list(sessions)[-RECENT_HISTORY_LIMIT:]:
        session = (
            item
            if isinstance(item, RecentSession)
            else parse_recent_session(item)
        )
        if session is None:
            continue
        bounded.append(
            recent_session_to_dict(session)
        )
    return bounded


def has_legacy_last_session(
    last_total_attempts: int,
    last_incorrect_attempts: int,
    last_hints_used: int,
    last_first_attempt_success: bool,
    last_completed: bool,
) -> bool:
    return (
        last_total_attempts > 0
        or last_incorrect_attempts > 0
        or last_hints_used > 0
        or last_first_attempt_success
        or last_completed
    )


def _safe_rate(
    numerator: float,
    denominator: int,
) -> float:
    if denominator <= 0:
        return 0.0

    return round(
        numerator / denominator,
        4,
    )


def attempts_per_completed_step(
    session: RecentSession,
) -> float | None:
    if session.steps_completed <= 0:
        return None

    return session.total_attempts / max(
        session.steps_completed,
        1,
    )


def _resolve_recent_sessions(
    recent_sessions: Sequence[
        RecentSession | dict
    ] | None,
    last_total_attempts: int,
    last_incorrect_attempts: int,
    last_hints_used: int,
    last_first_attempt_success: bool,
    last_completed: bool,
) -> tuple[RecentSession, ...]:
    parsed = parse_recent_sessions(
        list(recent_sessions or ())
    )
    if parsed:
        return parsed

    if has_legacy_last_session(
        last_total_attempts=last_total_attempts,
        last_incorrect_attempts=(
            last_incorrect_attempts
        ),
        last_hints_used=last_hints_used,
        last_first_attempt_success=(
            last_first_attempt_success
        ),
        last_completed=last_completed,
    ):
        return (
            RecentSession(
                completed=last_completed,
                total_attempts=last_total_attempts,
                incorrect_attempts=(
                    last_incorrect_attempts
                ),
                hints_used=last_hints_used,
                first_attempt_success=(
                    last_first_attempt_success
                ),
                steps_completed=0,
                total_steps=0,
            ),
        )

    return ()


def is_strong_recent_trend(
    features: AdaptivePerformanceFeatures,
) -> bool:
    return (
        features.has_enough_recent_history
        and features.recent_first_attempt_success_rate
        >= STRONG_FIRST_ATTEMPT_RATE
        and features.recent_hint_rate
        <= STRONG_MAX_HINT_RATE
        and features.recent_incorrect_rate
        <= STRONG_MAX_INCORRECT_RATE
    )


def is_weak_recent_trend(
    features: AdaptivePerformanceFeatures,
) -> bool:
    return features.has_enough_recent_history and (
        features.recent_hint_rate >= WEAK_HINT_RATE
        or features.recent_incorrect_rate
        >= WEAK_INCORRECT_RATE
        or features.recent_average_attempts_per_step
        >= WEAK_AVERAGE_ATTEMPTS_PER_STEP
    )


def classify_recent_trend(
    features: AdaptivePerformanceFeatures,
) -> str:
    if not features.has_enough_recent_history:
        return TREND_INSUFFICIENT

    strong = is_strong_recent_trend(features)
    weak = is_weak_recent_trend(features)

    if strong and not weak:
        return TREND_STRONG

    if weak and not strong:
        return TREND_NEEDS_SUPPORT

    return TREND_STABLE


def build_adaptive_features(
    mastery: float,
    questions_completed: int,
    first_attempt_streak: int,
    last_total_attempts: int = 0,
    last_incorrect_attempts: int = 0,
    last_hints_used: int = 0,
    last_first_attempt_success: bool = False,
    last_completed: bool = False,
    recent_sessions: Sequence[
        RecentSession | dict
    ] | None = None,
) -> AdaptivePerformanceFeatures:
    sessions = _resolve_recent_sessions(
        recent_sessions=recent_sessions,
        last_total_attempts=last_total_attempts,
        last_incorrect_attempts=(
            last_incorrect_attempts
        ),
        last_hints_used=last_hints_used,
        last_first_attempt_success=(
            last_first_attempt_success
        ),
        last_completed=last_completed,
    )
    count = len(sessions)
    completed_count = sum(
        1 for session in sessions if session.completed
    )
    first_attempt_count = sum(
        1
        for session in sessions
        if session.first_attempt_success
    )
    hint_count = sum(
        1
        for session in sessions
        if session.hints_used > 0
    )
    incorrect_count = sum(
        1
        for session in sessions
        if session.incorrect_attempts > 0
    )
    per_step_values = [
        value
        for value in (
            attempts_per_completed_step(session)
            for session in sessions
        )
        if value is not None
    ]
    features = AdaptivePerformanceFeatures(
        mastery=round(float(mastery), 4),
        questions_completed=int(questions_completed),
        first_attempt_streak=int(
            first_attempt_streak
        ),
        recent_session_count=count,
        recent_completion_rate=_safe_rate(
            completed_count,
            count,
        ),
        recent_first_attempt_success_rate=_safe_rate(
            first_attempt_count,
            count,
        ),
        recent_hint_rate=_safe_rate(
            hint_count,
            count,
        ),
        recent_incorrect_rate=_safe_rate(
            incorrect_count,
            count,
        ),
        recent_average_attempts_per_step=_safe_rate(
            sum(per_step_values),
            len(per_step_values),
        ),
        last_total_attempts=int(last_total_attempts),
        last_incorrect_attempts=int(
            last_incorrect_attempts
        ),
        last_hints_used=int(last_hints_used),
        last_first_attempt_success=bool(
            last_first_attempt_success
        ),
        last_completed=bool(last_completed),
        has_recent_history=count > 0,
        has_enough_recent_history=(
            count >= MIN_RECENT_SESSIONS_FOR_TREND
        ),
        recent_trend=TREND_INSUFFICIENT,
    )

    return AdaptivePerformanceFeatures(
        **{
            **features.__dict__,
            "recent_trend": classify_recent_trend(
                features
            ),
        }
    )


def features_as_metadata(
    features: AdaptivePerformanceFeatures,
) -> dict:
    return {
        "mastery": features.mastery,
        "questions_completed": (
            features.questions_completed
        ),
        "first_attempt_streak": (
            features.first_attempt_streak
        ),
        "recent_session_count": (
            features.recent_session_count
        ),
        "recent_completion_rate": (
            features.recent_completion_rate
        ),
        "recent_first_attempt_success_rate": (
            features.recent_first_attempt_success_rate
        ),
        "recent_hint_rate": features.recent_hint_rate,
        "recent_incorrect_rate": (
            features.recent_incorrect_rate
        ),
        "recent_average_attempts_per_step": (
            features.recent_average_attempts_per_step
        ),
        "has_recent_history": (
            features.has_recent_history
        ),
        "has_enough_recent_history": (
            features.has_enough_recent_history
        ),
        "recent_trend": features.recent_trend,
    }
