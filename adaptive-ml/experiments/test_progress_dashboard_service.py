import json
from pathlib import Path
from tempfile import TemporaryDirectory

from src.api.mat_pal.progress_service import (
    get_student_progress,
)


def write_progress(
    path: Path,
    progress: dict,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        json.dumps(progress, indent=4),
        encoding="utf-8",
    )


def assert_fresh_progress_returns_runnable_topics():
    with TemporaryDirectory() as directory:
        path = Path(directory) / "progress.json"
        progress = get_student_progress(
            path=path
        )

    topics = {
        topic.topic
        for topic in progress.topics
    }

    assert topics == {
        "first_order_linear",
        "separable_equations",
        "word_problems",
    }
    assert all(
        topic.mastery == 0.5
        for topic in progress.topics
    )
    assert progress.recommendation.recommendation_available


def assert_existing_and_legacy_progress_fields_are_returned():
    with TemporaryDirectory() as directory:
        path = Path(directory) / "progress.json"
        write_progress(
            path,
            {
                "skills": {
                    "linear_first_order_ode": {
                        "mastery": 0.9,
                        "questions_completed": 8,
                        "first_attempt_streak": 3,
                        "last_total_attempts": 8,
                        "last_incorrect_attempts": 0,
                        "last_hints_used": 0,
                        "last_first_attempt_success": True,
                        "last_completed": True,
                    },
                    "separable_equations": {
                        "mastery": 0.45,
                        "questions_completed": 2,
                        "first_attempt_streak": 1,
                    },
                }
            },
        )

        progress = get_student_progress(
            subject="mathematics",
            domain="ode",
            path=path,
        )

    topics = {
        topic.topic: topic
        for topic in progress.topics
    }

    linear = topics["first_order_linear"]
    separable = topics["separable_equations"]

    assert linear.mastery == 0.9
    assert linear.mastery_label == "Strong"
    assert linear.questions_completed == 8
    assert linear.first_attempt_streak == 3
    assert linear.last_total_attempts == 8
    assert linear.last_incorrect_attempts == 0
    assert linear.last_hints_used == 0
    assert linear.last_first_attempt_success is True
    assert linear.last_completed is True
    assert linear.generation_available is True
    assert linear.supported_difficulties == [1, 2, 3]
    assert linear.recommended_difficulty == 3

    assert separable.mastery == 0.45
    assert separable.mastery_label == "Developing"
    assert separable.questions_completed == 2
    assert separable.first_attempt_streak == 1
    assert separable.last_total_attempts == 0
    assert separable.last_hints_used == 0
    assert separable.recommended_difficulty == 2


def assert_static_primary_school_topic_has_problem_id():
    with TemporaryDirectory() as directory:
        path = Path(directory) / "progress.json"
        progress = get_student_progress(
            subject="mathematics",
            domain="primary_school",
            path=path,
        )

    assert len(progress.topics) == 1
    topic = progress.topics[0]

    assert topic.topic == "word_problems"
    assert topic.generation_available is False
    assert topic.supported_difficulties == []
    assert topic.recommended_difficulty is None
    assert topic.problem_id == (
        "grade4_reverse_reasoning_001"
    )


def assert_no_duplicate_topics_and_deterministic_ordering():
    with TemporaryDirectory() as directory:
        path = Path(directory) / "progress.json"
        progress = get_student_progress(
            path=path
        )

    keys = [
        (
            topic.subject,
            topic.domain,
            topic.topic,
        )
        for topic in progress.topics
    ]

    assert len(keys) == len(set(keys))
    assert keys == sorted(
        keys,
        key=lambda key: (
            key[0],
            key[1],
            next(
                topic.topic_name
                for topic in progress.topics
                if (
                    topic.subject,
                    topic.domain,
                    topic.topic,
                )
                == key
            ),
        ),
    )


def assert_empty_filter_returns_safe_response():
    with TemporaryDirectory() as directory:
        path = Path(directory) / "progress.json"
        progress = get_student_progress(
            subject="physics",
            domain="waves",
            path=path,
        )

    assert progress.topics == []
    assert (
        progress.recommendation
        .recommendation_available
        is False
    )


def main():
    assert_fresh_progress_returns_runnable_topics()
    assert_existing_and_legacy_progress_fields_are_returned()
    assert_static_primary_school_topic_has_problem_id()
    assert_no_duplicate_topics_and_deterministic_ordering()
    assert_empty_filter_returns_safe_response()

    print("progress_dashboard_service tests passed")


if __name__ == "__main__":
    main()
