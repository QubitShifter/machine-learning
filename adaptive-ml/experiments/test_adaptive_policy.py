from src.core.adaptive import (
    AdaptiveTopicState,
    RecentSession,
    RuleBasedAdaptivePolicy,
)


def make_session(
    completed: bool = True,
    total_attempts: int = 1,
    incorrect_attempts: int = 0,
    hints_used: int = 0,
    first_attempt_success: bool = True,
    steps_completed: int = 1,
    total_steps: int = 1,
    invalid_attempts: int = 0,
) -> RecentSession:
    return RecentSession(
        completed=completed,
        total_attempts=total_attempts,
        incorrect_attempts=incorrect_attempts,
        hints_used=hints_used,
        first_attempt_success=first_attempt_success,
        steps_completed=steps_completed,
        total_steps=total_steps,
        invalid_attempts=invalid_attempts,
    )


def make_topic(
    topic: str,
    mastery: float,
    questions_completed: int = 0,
    first_attempt_streak: int = 0,
    last_incorrect_attempts: int = 0,
    last_hints_used: int = 0,
    last_first_attempt_success: bool = False,
    last_total_attempts: int = 0,
    last_completed: bool = False,
    supported_difficulties: tuple[int, ...] = (1, 2, 3),
    generation_available: bool = True,
    problem_id: str | None = None,
    recent_sessions: tuple[RecentSession, ...] = (),
) -> AdaptiveTopicState:
    return AdaptiveTopicState(
        subject="mathematics",
        domain="ode",
        topic=topic,
        topic_name=topic.replace("_", " ").title(),
        mastery_key=topic,
        mastery=mastery,
        questions_completed=questions_completed,
        first_attempt_streak=first_attempt_streak,
        supported_difficulties=supported_difficulties,
        generation_available=generation_available,
        problem_id=problem_id,
        last_total_attempts=last_total_attempts,
        last_incorrect_attempts=last_incorrect_attempts,
        last_hints_used=last_hints_used,
        last_first_attempt_success=(
            last_first_attempt_success
        ),
        last_completed=last_completed,
        recent_sessions=recent_sessions,
    )


def assert_mastery_thresholds():
    policy = RuleBasedAdaptivePolicy()

    assert policy.choose_base_difficulty(0.20) == 1
    assert policy.choose_base_difficulty(0.50) == 2
    assert policy.choose_base_difficulty(0.90) == 3
    assert policy.choose_base_difficulty(0.39) == 1
    assert policy.choose_base_difficulty(0.40) == 2
    assert policy.choose_base_difficulty(0.74) == 2
    assert policy.choose_base_difficulty(0.75) == 3


def assert_recent_performance_adjustments():
    policy = RuleBasedAdaptivePolicy()

    strong = make_topic(
        "first_order_linear",
        mastery=0.50,
        questions_completed=2,
        first_attempt_streak=2,
        last_first_attempt_success=True,
    )
    weak = make_topic(
        "first_order_linear",
        mastery=0.50,
        last_incorrect_attempts=2,
    )
    low_bound = make_topic(
        "first_order_linear",
        mastery=0.20,
        last_incorrect_attempts=3,
    )
    high_bound = make_topic(
        "first_order_linear",
        mastery=0.90,
        questions_completed=3,
        first_attempt_streak=3,
        last_first_attempt_success=True,
    )

    assert policy.choose_difficulty(strong) == 3
    assert policy.choose_difficulty(weak) == 1
    assert policy.choose_difficulty(low_bound) == 1
    assert policy.choose_difficulty(high_bound) == 3


def assert_topic_selection_prefers_lower_mastery():
    policy = RuleBasedAdaptivePolicy()

    recommendation = policy.recommend_next(
        [
            make_topic("first_order_linear", 0.80),
            make_topic("separable_equations", 0.45),
        ]
    )

    assert recommendation.recommendation_available is True
    assert recommendation.topic == "separable_equations"
    assert recommendation.difficulty == 2

    recommendation = policy.recommend_next(
        [
            make_topic("first_order_linear", 0.30),
            make_topic("separable_equations", 0.90),
        ]
    )

    assert recommendation.topic == "first_order_linear"
    assert recommendation.difficulty == 1


def assert_topic_selection_tie_breaks_deterministically():
    policy = RuleBasedAdaptivePolicy()

    recommendation = policy.recommend_next(
        [
            make_topic(
                "separable_equations",
                0.50,
                questions_completed=3,
            ),
            make_topic(
                "first_order_linear",
                0.50,
                questions_completed=1,
            ),
        ]
    )

    assert recommendation.topic == "first_order_linear"

    recommendation = policy.recommend_next(
        [
            make_topic("separable_equations", 0.50),
            make_topic("first_order_linear", 0.50),
        ]
    )

    assert recommendation.topic == "first_order_linear"


def assert_no_runnable_content_is_safe():
    policy = RuleBasedAdaptivePolicy()

    recommendation = policy.recommend_next([])

    assert recommendation.recommendation_available is False


def assert_insufficient_history_keeps_base_difficulty():
    policy = RuleBasedAdaptivePolicy()
    topic = make_topic(
        "first_order_linear",
        mastery=0.50,
        recent_sessions=(make_session(),),
    )

    assert policy.choose_difficulty(topic) == 2


def assert_strong_recent_history_increases_one_level():
    policy = RuleBasedAdaptivePolicy()
    topic = make_topic(
        "first_order_linear",
        mastery=0.50,
        questions_completed=3,
        recent_sessions=(
            make_session(),
            make_session(),
            make_session(),
        ),
    )

    assert policy.choose_difficulty(topic) == 3


def assert_clean_multistep_sessions_do_not_look_weak():
    policy = RuleBasedAdaptivePolicy()
    topic = make_topic(
        "first_order_linear",
        mastery=0.50,
        questions_completed=2,
        recent_sessions=(
            make_session(
                total_attempts=7,
                steps_completed=7,
                total_steps=7,
            ),
            make_session(
                total_attempts=8,
                steps_completed=8,
                total_steps=8,
            ),
        ),
    )

    assert policy.choose_difficulty(topic) == 3
    recommendation = policy.recommend_next([topic])
    assert recommendation.metadata[
        "recent_average_attempts_per_step"
    ] == 1.0
    assert recommendation.metadata["adjustment"] == 1


def assert_weak_recent_history_decreases_one_level():
    policy = RuleBasedAdaptivePolicy()
    weak_session = make_session(
        total_attempts=4,
        incorrect_attempts=2,
        hints_used=2,
        first_attempt_success=False,
    )
    topic = make_topic(
        "first_order_linear",
        mastery=0.50,
        recent_sessions=(weak_session, weak_session),
    )

    assert policy.choose_difficulty(topic) == 1


def assert_mixed_recent_history_keeps_base_level():
    policy = RuleBasedAdaptivePolicy()
    topic = make_topic(
        "first_order_linear",
        mastery=0.50,
        recent_sessions=(
            make_session(),
            make_session(
                total_attempts=3,
                incorrect_attempts=1,
                hints_used=1,
                first_attempt_success=False,
            ),
            make_session(),
        ),
    )

    assert policy.choose_difficulty(topic) == 2


def assert_supported_bounds_are_respected():
    policy = RuleBasedAdaptivePolicy()
    strong = make_topic(
        "first_order_linear",
        mastery=0.90,
        recent_sessions=(
            make_session(),
            make_session(),
        ),
    )
    weak = make_topic(
        "first_order_linear",
        mastery=0.20,
        recent_sessions=(
            make_session(
                total_attempts=4,
                incorrect_attempts=2,
                hints_used=2,
                first_attempt_success=False,
            ),
            make_session(
                total_attempts=5,
                incorrect_attempts=3,
                hints_used=2,
                first_attempt_success=False,
            ),
        ),
    )

    assert policy.choose_difficulty(strong) == 3
    assert policy.choose_difficulty(weak) == 1


def assert_noncontiguous_supported_levels():
    policy = RuleBasedAdaptivePolicy()
    strong = make_topic(
        "first_order_linear",
        mastery=0.20,
        supported_difficulties=(1, 3),
        recent_sessions=(
            make_session(),
            make_session(),
        ),
    )
    weak = make_topic(
        "first_order_linear",
        mastery=0.90,
        supported_difficulties=(1, 3),
        recent_sessions=(
            make_session(
                total_attempts=4,
                incorrect_attempts=2,
                hints_used=2,
                first_attempt_success=False,
            ),
            make_session(
                total_attempts=3,
                incorrect_attempts=2,
                hints_used=1,
                first_attempt_success=False,
            ),
        ),
    )
    stepped = make_topic(
        "first_order_linear",
        mastery=0.50,
        supported_difficulties=(2, 4, 7),
        recent_sessions=(
            make_session(),
            make_session(),
        ),
    )
    weak_stepped = make_topic(
        "first_order_linear",
        mastery=0.90,
        supported_difficulties=(2, 4, 7),
        recent_sessions=(
            make_session(
                total_attempts=4,
                incorrect_attempts=2,
                hints_used=2,
                first_attempt_success=False,
            ),
            make_session(
                total_attempts=3,
                incorrect_attempts=2,
                hints_used=1,
                first_attempt_success=False,
            ),
        ),
    )

    assert policy.choose_difficulty(strong) == 3
    assert policy.choose_difficulty(weak) == 1
    assert policy.choose_difficulty(stepped) == 4
    assert policy.choose_difficulty(weak_stepped) in (
        2,
        4,
        7,
    )
    assert policy.choose_difficulty(weak_stepped) == 2
    assert policy.choose_difficulty(stepped) not in (
        1,
        3,
        5,
        6,
    )


def assert_topic_ranking_uses_weaker_recent_performance():
    policy = RuleBasedAdaptivePolicy()
    recommendation = policy.recommend_next(
        [
            make_topic(
                "separable_equations",
                mastery=0.50,
                recent_sessions=(
                    make_session(),
                    make_session(),
                ),
            ),
            make_topic(
                "first_order_linear",
                mastery=0.50,
                recent_sessions=(
                    make_session(
                        first_attempt_success=False,
                        incorrect_attempts=1,
                    ),
                    make_session(
                        first_attempt_success=False,
                        incorrect_attempts=1,
                    ),
                ),
            ),
        ]
    )

    assert recommendation.topic == "first_order_linear"


def assert_static_topic_has_null_difficulty():
    policy = RuleBasedAdaptivePolicy()
    topic = AdaptiveTopicState(
        subject="mathematics",
        domain="primary_school",
        topic="word_problems",
        topic_name="Word Problems",
        mastery_key="grade4_reverse_reasoning",
        mastery=0.50,
        questions_completed=0,
        first_attempt_streak=0,
        supported_difficulties=(),
        generation_available=False,
        problem_id="grade4_reverse_reasoning_001",
        recent_sessions=(
            make_session(),
            make_session(),
        ),
    )

    assert policy.choose_difficulty(topic) is None

    recommendation = policy.recommend_next([topic])

    assert recommendation.topic == "word_problems"
    assert recommendation.difficulty is None
    assert recommendation.generation_available is False
    assert recommendation.problem_id == (
        "grade4_reverse_reasoning_001"
    )
    assert "difficulty" not in recommendation.reason.lower()
    assert "increased" not in recommendation.reason
    assert "reduced" not in recommendation.reason


def assert_recommendation_reason_and_metadata():
    policy = RuleBasedAdaptivePolicy()
    strong = policy.recommend_next(
        [
            make_topic(
                "first_order_linear",
                mastery=0.62,
                recent_sessions=(
                    make_session(),
                    make_session(),
                    make_session(),
                ),
            )
        ]
    )

    assert "0.62" in strong.reason
    assert "strong" in strong.reason.lower()
    assert strong.metadata["recent_session_count"] == 3
    assert strong.metadata["adjustment"] == 1
    assert strong.metadata["adjustment_reason"] == (
        "recent_strong"
    )
    assert strong.metadata["base_difficulty"] == 2
    assert strong.metadata["recommended_difficulty"] == 3
    assert strong.metadata["supported_difficulties"] == [
        1,
        2,
        3,
    ]

    weak = policy.recommend_next(
        [
            make_topic(
                "separable_equations",
                mastery=0.48,
                recent_sessions=(
                    make_session(
                        total_attempts=4,
                        incorrect_attempts=2,
                        hints_used=2,
                        first_attempt_success=False,
                    ),
                    make_session(
                        total_attempts=3,
                        incorrect_attempts=1,
                        hints_used=2,
                        first_attempt_success=False,
                    ),
                ),
            )
        ]
    )

    assert "0.48" in weak.reason
    assert "hints" in weak.reason
    assert weak.metadata["adjustment"] == -1
    assert weak.metadata["adjustment_reason"] == (
        "recent_weak"
    )

    limited = policy.recommend_next(
        [
            make_topic(
                "separable_equations",
                mastery=0.48,
            )
        ]
    )

    assert "not yet enough recent history" in limited.reason
    assert limited.metadata["adjustment_reason"] == (
        "insufficient_history"
    )


def format_only_session(
    *,
    invalid_attempts: int = 2,
    steps_completed: int = 1,
    extra_valid_attempts: int = 1,
    hints_used: int = 0,
) -> RecentSession:
    return make_session(
        total_attempts=(
            extra_valid_attempts + invalid_attempts
        ),
        incorrect_attempts=invalid_attempts,
        invalid_attempts=invalid_attempts,
        hints_used=hints_used,
        first_attempt_success=False,
        steps_completed=steps_completed,
        total_steps=steps_completed,
    )


def assert_format_only_last_session_does_not_decrease():
    policy = RuleBasedAdaptivePolicy()
    topic = make_topic(
        "first_order_linear",
        mastery=0.50,
        last_incorrect_attempts=2,
        last_hints_used=0,
        last_first_attempt_success=False,
        last_completed=True,
        last_total_attempts=3,
        recent_sessions=(format_only_session(),),
    )

    assert policy.choose_difficulty(topic) == 2
    decision = policy._difficulty_decision(topic)
    assert decision["adjustment"] == 0
    assert decision["adjustment_reason"] == (
        "insufficient_history"
    )


def assert_mathematical_last_session_still_decreases():
    policy = RuleBasedAdaptivePolicy()
    topic = make_topic(
        "first_order_linear",
        mastery=0.50,
        last_incorrect_attempts=2,
        last_hints_used=0,
        last_first_attempt_success=False,
        last_completed=True,
        recent_sessions=(
            make_session(
                total_attempts=3,
                incorrect_attempts=2,
                invalid_attempts=0,
                first_attempt_success=False,
            ),
        ),
    )

    assert policy.choose_difficulty(topic) == 1
    decision = policy._difficulty_decision(topic)
    assert decision["adjustment"] == -1
    assert decision["adjustment_reason"] == (
        "last_session_weak"
    )


def assert_mixed_errors_last_session_still_decreases():
    policy = RuleBasedAdaptivePolicy()
    topic = make_topic(
        "first_order_linear",
        mastery=0.50,
        last_incorrect_attempts=4,
        last_hints_used=0,
        last_first_attempt_success=False,
        recent_sessions=(
            make_session(
                total_attempts=5,
                incorrect_attempts=4,
                invalid_attempts=2,
                first_attempt_success=False,
            ),
        ),
    )

    assert policy.choose_difficulty(topic) == 1


def assert_format_only_trend_does_not_decrease():
    policy = RuleBasedAdaptivePolicy()
    topic = make_topic(
        "first_order_linear",
        mastery=0.50,
        recent_sessions=(
            format_only_session(),
            format_only_session(),
        ),
    )

    assert policy.choose_difficulty(topic) == 2
    decision = policy._difficulty_decision(topic)
    assert decision["adjustment"] == 0
    assert decision["adjustment_reason"] == (
        "recent_mixed"
    )


def assert_format_only_high_attempts_per_step_do_not_decrease():
    policy = RuleBasedAdaptivePolicy()
    heavy_format = format_only_session(
        invalid_attempts=4,
        steps_completed=2,
        extra_valid_attempts=2,
    )
    topic = make_topic(
        "first_order_linear",
        mastery=0.50,
        recent_sessions=(heavy_format, heavy_format),
    )
    features = policy.features_for(topic)

    assert features.recent_average_attempts_per_step >= 2.0
    assert (
        features.recent_average_mathematical_attempts_per_step
        < 2.0
    )
    assert features.recent_incorrect_rate == 1.0
    assert features.recent_mathematical_incorrect_rate == 0.0
    assert policy.choose_difficulty(topic) == 2


def assert_hints_with_format_errors_still_decrease():
    policy = RuleBasedAdaptivePolicy()
    last_session = make_topic(
        "first_order_linear",
        mastery=0.50,
        last_hints_used=2,
        last_incorrect_attempts=2,
        last_first_attempt_success=False,
        recent_sessions=(
            format_only_session(hints_used=2),
        ),
    )
    trend = make_topic(
        "first_order_linear",
        mastery=0.50,
        recent_sessions=(
            format_only_session(hints_used=2),
            format_only_session(hints_used=2),
        ),
    )

    assert policy.choose_difficulty(last_session) == 1
    assert policy._difficulty_decision(last_session)[
        "adjustment_reason"
    ] == "last_session_weak"
    assert policy.choose_difficulty(trend) == 1
    assert policy._difficulty_decision(trend)[
        "adjustment_reason"
    ] == "recent_weak"


def assert_two_clean_sessions_still_increase():
    policy = RuleBasedAdaptivePolicy()
    topic = make_topic(
        "first_order_linear",
        mastery=0.50,
        recent_sessions=(
            make_session(invalid_attempts=0),
            make_session(invalid_attempts=0),
        ),
    )

    assert policy.choose_difficulty(topic) == 3
    assert policy._difficulty_decision(topic)[
        "adjustment_reason"
    ] == "recent_strong"


def assert_legacy_history_keeps_previous_difficulty():
    policy = RuleBasedAdaptivePolicy()
    no_history = make_topic(
        "separable_equations",
        mastery=0.45,
    )
    one_legacy = make_topic(
        "first_order_linear",
        mastery=0.50,
        last_incorrect_attempts=2,
        last_completed=True,
        last_total_attempts=3,
    )
    five_legacy = make_topic(
        "first_order_linear",
        mastery=0.50,
        recent_sessions=tuple(
            make_session(
                total_attempts=4,
                incorrect_attempts=2,
                first_attempt_success=False,
            )
            for _ in range(5)
        ),
    )
    mixed = make_topic(
        "first_order_linear",
        mastery=0.50,
        recent_sessions=(
            make_session(
                total_attempts=4,
                incorrect_attempts=2,
                first_attempt_success=False,
            ),
            format_only_session(),
        ),
    )

    assert policy.choose_difficulty(no_history) == 2
    assert policy.choose_difficulty(one_legacy) == 1
    assert policy.choose_difficulty(five_legacy) == 1
    assert policy.choose_difficulty(mixed) == 1


def assert_invalid_annotations_do_not_change_topic_rank():
    policy = RuleBasedAdaptivePolicy()
    unmarked = [
        make_topic(
            "separable_equations",
            mastery=0.50,
            recent_sessions=(
                make_session(),
                make_session(),
            ),
        ),
        make_topic(
            "first_order_linear",
            mastery=0.50,
            recent_sessions=(
                make_session(
                    first_attempt_success=False,
                    incorrect_attempts=2,
                    total_attempts=3,
                ),
                make_session(
                    first_attempt_success=False,
                    incorrect_attempts=2,
                    total_attempts=3,
                ),
            ),
        ),
    ]
    annotated = [
        make_topic(
            "separable_equations",
            mastery=0.50,
            recent_sessions=(
                make_session(invalid_attempts=0),
                make_session(invalid_attempts=0),
            ),
        ),
        make_topic(
            "first_order_linear",
            mastery=0.50,
            recent_sessions=(
                make_session(
                    first_attempt_success=False,
                    incorrect_attempts=2,
                    invalid_attempts=2,
                    total_attempts=3,
                ),
                make_session(
                    first_attempt_success=False,
                    incorrect_attempts=2,
                    invalid_attempts=2,
                    total_attempts=3,
                ),
            ),
        ),
    ]

    assert policy.recommend_next(unmarked).topic == (
        policy.recommend_next(annotated).topic
    )
    assert policy.recommend_next(unmarked).topic == (
        "first_order_linear"
    )
    assert policy.recommend_next(annotated).difficulty == 2
    assert policy.recommend_next(unmarked).difficulty == 1


def assert_difficulty_stays_within_supported_levels():
    policy = RuleBasedAdaptivePolicy()
    for mastery in (0.20, 0.50, 0.90):
        for sessions in (
            (format_only_session(),),
            (format_only_session(), format_only_session()),
            (
                make_session(
                    incorrect_attempts=2,
                    first_attempt_success=False,
                ),
                make_session(
                    incorrect_attempts=2,
                    first_attempt_success=False,
                ),
            ),
        ):
            topic = make_topic(
                "first_order_linear",
                mastery=mastery,
                recent_sessions=sessions,
            )
            difficulty = policy.choose_difficulty(topic)
            assert difficulty in (1, 2, 3)


def main():
    assert_mastery_thresholds()
    assert_recent_performance_adjustments()
    assert_topic_selection_prefers_lower_mastery()
    assert_topic_selection_tie_breaks_deterministically()
    assert_no_runnable_content_is_safe()
    assert_insufficient_history_keeps_base_difficulty()
    assert_strong_recent_history_increases_one_level()
    assert_clean_multistep_sessions_do_not_look_weak()
    assert_weak_recent_history_decreases_one_level()
    assert_mixed_recent_history_keeps_base_level()
    assert_supported_bounds_are_respected()
    assert_noncontiguous_supported_levels()
    assert_topic_ranking_uses_weaker_recent_performance()
    assert_static_topic_has_null_difficulty()
    assert_recommendation_reason_and_metadata()
    assert_format_only_last_session_does_not_decrease()
    assert_mathematical_last_session_still_decreases()
    assert_mixed_errors_last_session_still_decreases()
    assert_format_only_trend_does_not_decrease()
    assert_format_only_high_attempts_per_step_do_not_decrease()
    assert_hints_with_format_errors_still_decrease()
    assert_two_clean_sessions_still_increase()
    assert_legacy_history_keeps_previous_difficulty()
    assert_invalid_annotations_do_not_change_topic_rank()
    assert_difficulty_stays_within_supported_levels()

    print("adaptive_policy tests passed")


if __name__ == "__main__":
    main()
