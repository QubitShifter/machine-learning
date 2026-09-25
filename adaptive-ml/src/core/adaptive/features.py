from dataclasses import dataclass
from typing import Sequence


RECENT_HISTORY_LIMIT = 5
MIN_RECENT_SESSIONS_FOR_TREND = 2
FAMILY_MATH_ERROR_SESSION_THRESHOLD = 2
FAMILY_HISTORY_LIMIT = 3

LOGICAL_REASONING_FAMILY_ORDER = (
    "number_detective",
    "distribution_puzzles",
    "logic_detective",
)
LOGICAL_REASONING_HISTORY_FAMILIES = frozenset(
    LOGICAL_REASONING_FAMILY_ORDER
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
    recent_mathematical_incorrect_rate: float
    recent_average_mathematical_attempts_per_step: float
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


def bounded_invalid_attempts(
    session: RecentSession,
) -> int:
    incorrect = max(0, int(session.incorrect_attempts))
    invalid = max(0, int(session.invalid_attempts))
    return min(invalid, incorrect)


def mathematical_incorrect_attempts(
    session: RecentSession,
) -> int:
    return max(
        0,
        int(session.incorrect_attempts)
        - bounded_invalid_attempts(session),
    )


def session_has_mathematical_error(
    session: RecentSession,
) -> bool:
    return mathematical_incorrect_attempts(session) > 0


@dataclass(frozen=True)
class FamilyWindowStats:
    family: str
    completed: int
    mathematical_error_sessions: int


def annotated_logical_reasoning_sessions(
    sessions: Sequence[RecentSession],
) -> tuple[RecentSession, ...]:
    annotated: list[RecentSession] = []
    for session in sessions:
        if not session.completed:
            continue
        if normalize_history_family(session.family) is None:
            continue
        annotated.append(session)
    return tuple(annotated)


def last_completed_known_family(
    sessions: Sequence[RecentSession],
) -> str | None:
    annotated = annotated_logical_reasoning_sessions(
        sessions
    )
    if not annotated:
        return None
    return annotated[-1].family


def family_window_stats(
    sessions: Sequence[RecentSession],
) -> dict[str, FamilyWindowStats]:
    stats = {
        family: FamilyWindowStats(
            family=family,
            completed=0,
            mathematical_error_sessions=0,
        )
        for family in LOGICAL_REASONING_FAMILY_ORDER
    }
    for session in annotated_logical_reasoning_sessions(
        sessions
    ):
        family = session.family
        if family is None:
            continue
        current = stats[family]
        stats[family] = FamilyWindowStats(
            family=family,
            completed=current.completed + 1,
            mathematical_error_sessions=(
                current.mathematical_error_sessions
                + int(
                    session_has_mathematical_error(
                        session
                    )
                )
            ),
        )
    return stats


def parse_family_outcomes(
    raw: object,
) -> tuple[dict, ...]:
    if not isinstance(raw, (list, tuple)):
        return ()

    outcomes: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        if "math_error" not in item:
            continue
        outcomes.append(
            {
                "math_error": bool(item["math_error"]),
            }
        )
    return tuple(outcomes[-FAMILY_HISTORY_LIMIT:])


def parse_family_history(
    raw: object,
) -> dict[str, tuple[dict, ...]]:
    if not isinstance(raw, dict):
        return {}

    history: dict[str, tuple[dict, ...]] = {}
    for family in LOGICAL_REASONING_FAMILY_ORDER:
        outcomes = parse_family_outcomes(
            raw.get(family)
        )
        if outcomes:
            history[family] = outcomes
    return history


def family_history_to_dict(
    history: object,
) -> dict:
    parsed = parse_family_history(history)
    payload: dict[str, list[dict]] = {}
    for family in LOGICAL_REASONING_FAMILY_ORDER:
        outcomes = parsed.get(family)
        if not outcomes:
            continue
        payload[family] = [
            {
                "math_error": bool(
                    outcome["math_error"]
                ),
            }
            for outcome in outcomes
        ]
    return payload


def derive_family_history_from_sessions(
    sessions: Sequence[RecentSession],
) -> dict[str, tuple[dict, ...]]:
    collected: dict[str, list[dict]] = {
        family: []
        for family in LOGICAL_REASONING_FAMILY_ORDER
    }
    for session in annotated_logical_reasoning_sessions(
        sessions
    ):
        family = session.family
        if family is None:
            continue
        collected[family].append(
            {
                "math_error": (
                    session_has_mathematical_error(
                        session
                    )
                ),
            }
        )
    return parse_family_history(collected)


def resolve_family_history(
    persisted: object,
    recent_sessions: Sequence[RecentSession] = (),
) -> dict[str, tuple[dict, ...]]:
    parsed = parse_family_history(persisted)
    if parsed:
        return parsed
    return derive_family_history_from_sessions(
        recent_sessions
    )


def family_math_error_count(
    outcomes: Sequence[dict],
) -> int:
    return sum(
        1
        for outcome in outcomes
        if outcome.get("math_error")
    )


def family_is_targeted(
    outcomes: Sequence[dict],
) -> bool:
    return (
        family_math_error_count(outcomes)
        >= FAMILY_MATH_ERROR_SESSION_THRESHOLD
    )


def append_family_outcome(
    history: object,
    family: str | None,
    math_error: bool,
) -> dict[str, tuple[dict, ...]]:
    normalized = normalize_history_family(family)
    parsed = parse_family_history(history)
    if normalized is None:
        return parsed

    current = list(parsed.get(normalized, ()))
    current.append(
        {
            "math_error": bool(math_error),
        }
    )
    parsed[normalized] = tuple(
        current[-FAMILY_HISTORY_LIMIT:]
    )
    return parse_family_history(parsed)


def mathematical_answer_attempts(
    session: RecentSession,
) -> int:
    """
    Valid answer submissions remaining after
    removing known invalid-format attempts.

    Assumes each invalid-format submission is
    also counted in total_attempts and in
    incorrect_attempts. Missing invalid_attempts
    defaults to 0, so legacy sessions keep their
    original attempt totals.
    """

    total = max(0, int(session.total_attempts))
    return max(
        0,
        total - bounded_invalid_attempts(session),
    )


def mathematical_attempts_per_completed_step(
    session: RecentSession,
) -> float | None:
    if session.steps_completed <= 0:
        return None

    return mathematical_answer_attempts(
        session
    ) / max(session.steps_completed, 1)


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
        or features.recent_mathematical_incorrect_rate
        >= WEAK_INCORRECT_RATE
        or features.recent_average_mathematical_attempts_per_step
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
    mathematical_incorrect_count = sum(
        1
        for session in sessions
        if mathematical_incorrect_attempts(session) > 0
    )
    per_step_values = [
        value
        for value in (
            attempts_per_completed_step(session)
            for session in sessions
        )
        if value is not None
    ]
    mathematical_per_step_values = [
        value
        for value in (
            mathematical_attempts_per_completed_step(
                session
            )
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
        recent_mathematical_incorrect_rate=_safe_rate(
            mathematical_incorrect_count,
            count,
        ),
        recent_average_mathematical_attempts_per_step=_safe_rate(
            sum(mathematical_per_step_values),
            len(mathematical_per_step_values),
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
        "recent_mathematical_incorrect_rate": (
            features.recent_mathematical_incorrect_rate
        ),
        "recent_average_mathematical_attempts_per_step": (
            features.recent_average_mathematical_attempts_per_step
        ),
        "has_recent_history": (
            features.has_recent_history
        ),
        "has_enough_recent_history": (
            features.has_enough_recent_history
        ),
        "recent_trend": features.recent_trend,
    }
