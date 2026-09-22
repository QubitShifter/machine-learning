import json

from fastapi.testclient import TestClient

from src.api.mat_pal.app import app
from src.core.student_model.progress_store import (
    DEFAULT_PROGRESS_PATH,
)


client = TestClient(app)


def write_progress(progress: dict) -> None:
    DEFAULT_PROGRESS_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    DEFAULT_PROGRESS_PATH.write_text(
        json.dumps(progress, indent=4),
        encoding="utf-8",
    )


def get_progress(
    query: str = "",
) -> dict:
    response = client.get(
        f"/progress{query}"
    )

    assert response.status_code == 200
    return response.json()


def assert_progress_api_returns_dashboard_schema():
    write_progress(
        {
            "skills": {
                "linear_first_order_ode": {
                    "mastery": 0.8,
                    "questions_completed": 4,
                    "first_attempt_streak": 1,
                    "last_total_attempts": 9,
                    "last_incorrect_attempts": 1,
                    "last_hints_used": 0,
                    "last_first_attempt_success": False,
                    "last_completed": True,
                },
                "separable_equations": {
                    "mastery": 0.45,
                    "questions_completed": 2,
                    "first_attempt_streak": 0,
                },
            }
        }
    )

    payload = get_progress()

    assert payload["student_id"] == "local_student"
    assert "topics" in payload
    assert "recommendation" in payload
    assert payload["recommendation"][
        "recommendation_available"
    ] is True

    keys = [
        (
            topic["subject"],
            topic["domain"],
            topic["topic"],
        )
        for topic in payload["topics"]
    ]

    assert len(keys) == len(set(keys))
    assert {
        key[2]
        for key in keys
    } == {
        "arithmetic",
        "first_order_linear",
        "kinematics",
        "logical_reasoning",
        "number_patterns",
        "separable_equations",
        "story_problems",
        "unknown_numbers",
        "word_problems",
    }

    separable = next(
        topic
        for topic in payload["topics"]
        if topic["topic"] == "separable_equations"
    )

    assert separable["mastery"] == 0.45
    assert separable["questions_completed"] == 2
    assert separable["first_attempt_streak"] == 0
    assert separable["last_total_attempts"] == 0
    assert separable["generation_available"] is True
    assert separable["supported_difficulties"] == [
        1,
        2,
        3,
    ]
    assert separable["recommended_difficulty"] == 2


def assert_progress_filters_are_generic():
    write_progress({"skills": {}})

    ode = get_progress(
        "?subject=mathematics&domain=ode"
    )
    physics = get_progress(
        "?subject=physics&domain=waves"
    )

    assert {
        topic["topic"]
        for topic in ode["topics"]
    } == {
        "first_order_linear",
        "separable_equations",
    }
    assert physics["topics"] == []
    assert physics["recommendation"][
        "recommendation_available"
    ] is False


def assert_recommended_practice_flow_uses_generation():
    write_progress(
        {
            "skills": {
                "linear_first_order_ode": {
                    "mastery": 0.8,
                    "questions_completed": 4,
                    "first_attempt_streak": 1,
                },
                "separable_equations": {
                    "mastery": 0.45,
                    "questions_completed": 2,
                    "first_attempt_streak": 0,
                },
            }
        }
    )

    payload = get_progress(
        "?subject=mathematics&domain=ode"
    )
    recommendation = payload["recommendation"]

    assert recommendation["topic"] == (
        "separable_equations"
    )
    assert recommendation["difficulty"] == 2
    assert recommendation["generation_available"] is True

    generated = client.post(
        "/problems/generate",
        json={
            "subject": recommendation["subject"],
            "domain": recommendation["domain"],
            "topic": recommendation["topic"],
            "difficulty": recommendation["difficulty"],
            "seed": 9,
        },
    )

    assert generated.status_code == 200
    generated_payload = generated.json()
    assert generated_payload["topic"] == (
        "separable_equations"
    )

    start = client.post(
        "/sessions/start",
        json={
            "problem_id": (
                generated_payload["problem_id"]
            ),
        },
    )

    assert start.status_code == 200
    assert start.json()["problem_statement"] == (
        "Solve dy/dx = 2*x*y"
    )


def main():
    had_progress = DEFAULT_PROGRESS_PATH.exists()
    original_progress = (
        DEFAULT_PROGRESS_PATH.read_text(
            encoding="utf-8"
        )
        if had_progress
        else None
    )

    try:
        assert_progress_api_returns_dashboard_schema()
        assert_progress_filters_are_generic()
        assert_recommended_practice_flow_uses_generation()

    finally:
        if had_progress and original_progress is not None:
            DEFAULT_PROGRESS_PATH.write_text(
                original_progress,
                encoding="utf-8",
            )
        elif DEFAULT_PROGRESS_PATH.exists():
            DEFAULT_PROGRESS_PATH.unlink()

    print("progress_api tests passed")


if __name__ == "__main__":
    main()
