from dataclasses import dataclass, field


LOW_MASTERY_THRESHOLD = 0.40
HIGH_MASTERY_THRESHOLD = 0.75
SIMILAR_MASTERY_DELTA = 0.05


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
        if not topic_state.generation_available:
            return None

        supported = sorted(
            topic_state.supported_difficulties
        )

        if not supported:
            return None

        difficulty = self.choose_base_difficulty(
            topic_state.mastery
        )

        if self._has_strong_recent_performance(
            topic_state
        ):
            difficulty += 1

        elif self._has_weak_recent_performance(
            topic_state
        ):
            difficulty -= 1

        return min(
            max(difficulty, supported[0]),
            supported[-1],
        )

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
            key=lambda candidate: (
                round(candidate.mastery, 4),
                candidate.questions_completed,
                candidate.topic,
            ),
        )[0]

        difficulty = self.choose_difficulty(
            selected
        )

        reason = (
            f"Practice {selected.topic_name} next because "
            f"its current mastery is {selected.mastery:.2f}."
        )

        if (
            difficulty is not None
            and self._has_strong_recent_performance(
                selected
            )
        ):
            reason += (
                " Strong recent performance allows a "
                "one-level difficulty increase."
            )

        elif (
            difficulty is not None
            and self._has_weak_recent_performance(
                selected
            )
        ):
            reason += (
                " Recent hints or incorrect attempts keep "
                "the difficulty conservative."
            )

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
            reason=reason,
            metadata={
                "questions_completed": (
                    selected.questions_completed
                ),
                "first_attempt_streak": (
                    selected.first_attempt_streak
                ),
                "supported_difficulties": (
                    list(selected.supported_difficulties)
                    if selected.generation_available
                    else []
                ),
                "tie_breaker": (
                    "lowest mastery, then fewer completed "
                    "questions, then topic id"
                ),
            },
        )

    def _has_strong_recent_performance(
        self,
        topic_state: AdaptiveTopicState,
    ) -> bool:
        return (
            topic_state.first_attempt_streak >= 2
            and topic_state.last_first_attempt_success
            and topic_state.last_hints_used == 0
        )

    def _has_weak_recent_performance(
        self,
        topic_state: AdaptiveTopicState,
    ) -> bool:
        return (
            topic_state.last_incorrect_attempts >= 2
            or topic_state.last_hints_used >= 2
        )
