from src.core.adaptive import (
    AdaptiveTopicState,
    RuleBasedAdaptivePolicy,
)


def make_topic(
    topic: str,
    mastery: float,
    questions_completed: int = 0,
    first_attempt_streak: int = 0,
    last_incorrect_attempts: int = 0,
    last_hints_used: int = 0,
    last_first_attempt_success: bool = False,
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
        supported_difficulties=(1, 2, 3),
        generation_available=True,
        last_incorrect_attempts=last_incorrect_attempts,
        last_hints_used=last_hints_used,
        last_first_attempt_success=(
            last_first_attempt_success
        ),
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
    )

    assert policy.choose_difficulty(topic) is None

    recommendation = policy.recommend_next([topic])

    assert recommendation.topic == "word_problems"
    assert recommendation.difficulty is None
    assert recommendation.generation_available is False


def main():
    assert_mastery_thresholds()
    assert_recent_performance_adjustments()
    assert_topic_selection_prefers_lower_mastery()
    assert_topic_selection_tie_breaks_deterministically()
    assert_no_runnable_content_is_safe()
    assert_static_topic_has_null_difficulty()

    print("adaptive_policy tests passed")


if __name__ == "__main__":
    main()
