from dataclasses import dataclass, field

from src.core.adaptive.features import (
    AdaptivePerformanceFeatures,
    RecentSession,
    build_adaptive_features,
    features_as_metadata,
    is_strong_recent_trend,
    is_weak_recent_trend,
    mathematical_incorrect_attempts,
)


LOW_MASTERY_THRESHOLD = 0.40
HIGH_MASTERY_THRESHOLD = 0.75
SIMILAR_MASTERY_DELTA = 0.05

ADJUSTMENT_RECENT_STRONG = "recent_strong"
ADJUSTMENT_RECENT_WEAK = "recent_weak"
ADJUSTMENT_RECENT_MIXED = "recent_mixed"
ADJUSTMENT_LAST_SESSION_STRONG = "last_session_strong"
ADJUSTMENT_LAST_SESSION_WEAK = "last_session_weak"
ADJUSTMENT_INSUFFICIENT = "insufficient_history"
ADJUSTMENT_STATIC = "static_topic"


@dataclass(frozen=True)
class SessionPerformanceSummary:
    problem_id: str
    subject: str
    domain: str
    topic: str
    difficulty: int | None
    mastery_key: str
    completed: bool
    total_attempts: int
    incorrect_attempts: int
    hints_used: int
    first_attempt_success: bool
    steps_completed: int
    total_steps: int
    metadata: dict = field(default_factory=dict)
    family: str | None = None
    invalid_attempts: int = 0


@dataclass(frozen=True)
class AdaptiveTopicState:
    subject: str
    domain: str
    topic: str
    topic_name: str
    mastery_key: str
    mastery: float
    questions_completed: int
    first_attempt_streak: int
    supported_difficulties: tuple[int, ...]
    generation_available: bool
    problem_id: str | None = None
    last_total_attempts: int = 0
    last_incorrect_attempts: int = 0
    last_hints_used: int = 0
    last_first_attempt_success: bool = False
    last_completed: bool = False
    recent_sessions: tuple[RecentSession, ...] = ()
    features: AdaptivePerformanceFeatures | None = None


@dataclass(frozen=True)
class AdaptiveRecommendation:
    recommendation_available: bool
    reason: str
    subject: str | None = None
    domain: str | None = None
    topic: str | None = None
    topic_name: str | None = None
    difficulty: int | None = None
    mastery: float | None = None
    mastery_key: str | None = None
    generation_available: bool = False
    problem_id: str | None = None
    metadata: dict = field(default_factory=dict)


class RuleBasedAdaptivePolicy:
    """
    Transparent deterministic baseline policy.
    """

    def choose_base_difficulty(
        self,
        mastery: float,
    ) -> int:
        if mastery < LOW_MASTERY_THRESHOLD:
            return 1

        if mastery < HIGH_MASTERY_THRESHOLD:
            return 2

        return 3

    def choose_difficulty(
        self,
        topic_state: AdaptiveTopicState,
    ) -> int | None:
        decision = self._difficulty_decision(
            topic_state
        )
        return decision["recommended_difficulty"]

    def recommend_next(
        self,
        candidates: list[AdaptiveTopicState],
    ) -> AdaptiveRecommendation:
        runnable = [
            candidate
            for candidate in candidates
            if (
                candidate.generation_available
                or candidate.problem_id is not None
            )
        ]

        if not runnable:
            return AdaptiveRecommendation(
                recommendation_available=False,
                reason=(
                    "No runnable adaptive practice is "
                    "available for this selection yet."
                ),
            )

        selected = sorted(
            runnable,
            key=self._topic_sort_key,
        )[0]
        decision = self._difficulty_decision(
            selected
        )
        features = self.features_for(selected)
        difficulty = decision[
            "recommended_difficulty"
        ]

        return AdaptiveRecommendation(
            recommendation_available=True,
            subject=selected.subject,
            domain=selected.domain,
            topic=selected.topic,
            topic_name=selected.topic_name,
            difficulty=difficulty,
            mastery=round(selected.mastery, 4),
            mastery_key=selected.mastery_key,
            generation_available=(
                selected.generation_available
            ),
            problem_id=selected.problem_id,
            reason=self._recommendation_reason(
                selected,
                features,
                decision,
            ),
            metadata={
                **features_as_metadata(features),
                "base_difficulty": decision[
                    "base_difficulty"
                ],
                "recommended_difficulty": difficulty,
                "adjustment": decision["adjustment"],
                "adjustment_reason": decision[
                    "adjustment_reason"
                ],
                "supported_difficulties": (
                    list(
                        selected.supported_difficulties
                    )
                    if selected.generation_available
                    else []
                ),
                "tie_breaker": (
                    "lowest mastery, then fewer "
                    "completed questions, then weaker "
                    "recent performance, then topic id"
                ),
            },
        )

    def features_for(
        self,
        topic_state: AdaptiveTopicState,
    ) -> AdaptivePerformanceFeatures:
        if topic_state.features is not None:
            return topic_state.features

        return build_adaptive_features(
            mastery=topic_state.mastery,
            questions_completed=(
                topic_state.questions_completed
            ),
            first_attempt_streak=(
                topic_state.first_attempt_streak
            ),
            last_total_attempts=(
                topic_state.last_total_attempts
            ),
            last_incorrect_attempts=(
                topic_state.last_incorrect_attempts
            ),
            last_hints_used=topic_state.last_hints_used,
            last_first_attempt_success=(
                topic_state.last_first_attempt_success
            ),
            last_completed=topic_state.last_completed,
            recent_sessions=topic_state.recent_sessions,
        )

    def _topic_sort_key(
        self,
        topic_state: AdaptiveTopicState,
    ) -> tuple:
        features = self.features_for(topic_state)
        return (
            round(topic_state.mastery, 4),
            topic_state.questions_completed,
            features.recent_first_attempt_success_rate,
            -features.recent_hint_rate,
            -features.recent_incorrect_rate,
            topic_state.topic,
        )

    def _difficulty_decision(
        self,
        topic_state: AdaptiveTopicState,
    ) -> dict:
        if (
            not topic_state.generation_available
            or not topic_state.supported_difficulties
        ):
            return {
                "base_difficulty": None,
                "recommended_difficulty": None,
                "adjustment": 0,
                "adjustment_reason": ADJUSTMENT_STATIC,
            }

        features = self.features_for(topic_state)
        supported = tuple(
            sorted(
                topic_state.supported_difficulties
            )
        )
        base = self._snap_to_supported(
            self.choose_base_difficulty(
                topic_state.mastery
            ),
            supported,
        )
        adjustment, adjustment_reason = (
            self._difficulty_adjustment(
                topic_state,
                features,
            )
        )
        recommended = self._move_supported(
            base,
            supported,
            adjustment,
        )

        return {
            "base_difficulty": base,
            "recommended_difficulty": recommended,
            "adjustment": adjustment,
            "adjustment_reason": adjustment_reason,
        }

    def _difficulty_adjustment(
        self,
        topic_state: AdaptiveTopicState,
        features: AdaptivePerformanceFeatures,
    ) -> tuple[int, str]:
        if features.has_enough_recent_history:
            strong = is_strong_recent_trend(features)
            weak = is_weak_recent_trend(features)

            if strong and not weak:
                return 1, ADJUSTMENT_RECENT_STRONG

            if weak and not strong:
                return -1, ADJUSTMENT_RECENT_WEAK

            return 0, ADJUSTMENT_RECENT_MIXED

        if self._has_strong_last_session(
            topic_state
        ):
            return 1, ADJUSTMENT_LAST_SESSION_STRONG

        if self._has_weak_last_session(topic_state):
            return -1, ADJUSTMENT_LAST_SESSION_WEAK

        return 0, ADJUSTMENT_INSUFFICIENT

    def _has_strong_last_session(
        self,
        topic_state: AdaptiveTopicState,
    ) -> bool:
        return (
            topic_state.first_attempt_streak >= 2
            and topic_state.last_first_attempt_success
            and topic_state.last_hints_used == 0
        )

    def _has_weak_last_session(
        self,
        topic_state: AdaptiveTopicState,
    ) -> bool:
        return (
            self._last_mathematical_incorrect_attempts(
                topic_state
            ) >= 2
            or topic_state.last_hints_used >= 2
        )

    def _last_mathematical_incorrect_attempts(
        self,
        topic_state: AdaptiveTopicState,
    ) -> int:
        if topic_state.recent_sessions:
            return mathematical_incorrect_attempts(
                topic_state.recent_sessions[-1]
            )

        return max(
            0,
            int(topic_state.last_incorrect_attempts),
        )

    def _snap_to_supported(
        self,
        difficulty: int,
        supported: tuple[int, ...],
    ) -> int:
        nearest = supported[0]
        nearest_distance = abs(
            difficulty - supported[0]
        )

        for level in supported[1:]:
            distance = abs(difficulty - level)
            if distance < nearest_distance:
                nearest = level
                nearest_distance = distance

        return nearest

    def _move_supported(
        self,
        difficulty: int,
        supported: tuple[int, ...],
        adjustment: int,
    ) -> int:
        index = supported.index(difficulty)
        moved = min(
            max(index + adjustment, 0),
            len(supported) - 1,
        )
        return supported[moved]

    def _recommendation_reason(
        self,
        topic_state: AdaptiveTopicState,
        features: AdaptivePerformanceFeatures,
        decision: dict,
    ) -> str:
        reason = (
            f"Practice {topic_state.topic_name} next "
            f"because its current mastery is "
            f"{topic_state.mastery:.2f}."
        )
        adjustment_reason = decision[
            "adjustment_reason"
        ]

        if not topic_state.generation_available:
            return reason

        if adjustment_reason == ADJUSTMENT_RECENT_STRONG:
            return (
                reason
                + " Recent performance has been strong "
                + f"across {features.recent_session_count} "
                + "sessions, so difficulty is increased "
                + "by one supported level."
            )

        if adjustment_reason == ADJUSTMENT_RECENT_WEAK:
            return (
                reason
                + " Recent practice required frequent "
                + "hints or corrections, so difficulty "
                + "is reduced by one supported level."
            )

        if adjustment_reason == ADJUSTMENT_RECENT_MIXED:
            return (
                reason
                + " Recent performance is mixed, so the "
                + "mastery-based difficulty is kept."
            )

        if (
            adjustment_reason
            == ADJUSTMENT_LAST_SESSION_STRONG
        ):
            return (
                reason
                + " A strong last session allows a "
                + "one-level difficulty increase."
            )

        if (
            adjustment_reason
            == ADJUSTMENT_LAST_SESSION_WEAK
        ):
            return (
                reason
                + " The last session required extra "
                + "hints or corrections, so difficulty "
                + "is reduced by one supported level."
            )

        return (
            reason
            + " There is not yet enough recent "
            + "history for a trend-based difficulty "
            + "adjustment."
        )
