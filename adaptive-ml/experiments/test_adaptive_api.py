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


def read_progress() -> dict:
    return json.loads(
        DEFAULT_PROGRESS_PATH.read_text(
            encoding="utf-8"
        )
    )


def recommendation(
    subject: str = "mathematics",
    domain: str = "ode",
) -> dict:
    response = client.post(
        "/adaptive/recommendation",
        json={
            "subject": subject,
            "domain": domain,
        },
    )

    assert response.status_code == 200
    return response.json()


def generate_from_recommendation(
    next_step: dict,
    seed: int,
) -> dict:
    response = client.post(
        "/problems/generate",
        json={
            "subject": next_step["subject"],
            "domain": next_step["domain"],
            "topic": next_step["topic"],
            "difficulty": next_step["difficulty"],
            "seed": seed,
        },
    )

    assert response.status_code == 200
    return response.json()


def post_answer(
    session_id: str,
    answer: str,
    input_type: str = "math",
) -> dict:
    response = client.post(
        f"/sessions/{session_id}/answer",
        json={
            "answer": answer,
            "input_type": input_type,
        },
    )

    assert response.status_code == 200
    return response.json()


def assert_recommends_lower_mastery_ode_topic():
    write_progress(
        {
            "skills": {
                "linear_first_order_ode": {
                    "mastery": 0.80,
                    "questions_completed": 3,
                    "first_attempt_streak": 1,
                },
                "separable_equations": {
                    "mastery": 0.45,
                    "questions_completed": 1,
                    "first_attempt_streak": 0,
                },
            }
        }
    )

    next_step = recommendation()

    assert next_step["recommendation_available"] is True
    assert next_step["topic"] == "separable_equations"
    assert next_step["difficulty"] == 2
    assert next_step["generation_available"] is True
    assert "0.45" in next_step["reason"]

    generated = generate_from_recommendation(
        next_step,
        seed=9,
    )
    assert generated["topic"] == "separable_equations"

    start = client.post(
        "/sessions/start",
        json={
            "problem_id": generated["problem_id"],
        },
    )
    assert start.status_code == 200
    assert start.json()["expected_input_type"] == "math"


def assert_recommendation_changes_when_mastery_swaps():
    write_progress(
        {
            "skills": {
                "linear_first_order_ode": {
                    "mastery": 0.25,
                    "questions_completed": 1,
                    "first_attempt_streak": 0,
                },
                "separable_equations": {
                    "mastery": 0.90,
                    "questions_completed": 4,
                    "first_attempt_streak": 2,
                },
            }
        }
    )

    next_step = recommendation()

    assert next_step["topic"] == "first_order_linear"
    assert next_step["difficulty"] == 1


def assert_primary_school_static_recommendation():
    write_progress(
        {
            "skills": {
                "grade4_arithmetic": {
                    "mastery": 0.95,
                    "questions_completed": 4,
                    "first_attempt_streak": 2,
                },
                "grade4_unknown_number": {
                    "mastery": 0.95,
                    "questions_completed": 4,
                    "first_attempt_streak": 2,
                },
                "grade4_number_patterns": {
                    "mastery": 0.95,
                    "questions_completed": 4,
                    "first_attempt_streak": 2,
                },
                "grade4_reverse_reasoning": {
                    "mastery": 0.50,
                    "questions_completed": 0,
                    "first_attempt_streak": 0,
                },
            }
        }
    )

    next_step = recommendation(
        domain="primary_school",
    )

    assert next_step["recommendation_available"] is True
    assert next_step["topic"] == "word_problems"
    assert next_step["generation_available"] is False
    assert next_step["difficulty"] is None
    assert next_step["problem_id"] == (
        "grade4_reverse_reasoning_001"
    )
    assert next_step["metadata"][
        "recommended_difficulty"
    ] is None
    assert next_step["metadata"][
        "adjustment_reason"
    ] == "static_topic"
    assert "difficulty" not in next_step["reason"].lower()


def assert_no_available_content_is_safe():
    write_progress({"skills": {}})

    next_step = recommendation(
        subject="physics",
        domain="waves",
    )

    assert next_step["recommendation_available"] is False


def assert_generated_completion_updates_mastery_and_difficulty():
    write_progress(
        {
            "skills": {
                "linear_first_order_ode": {
                    "mastery": 0.90,
                    "questions_completed": 2,
                    "first_attempt_streak": 0,
                },
                "separable_equations": {
                    "mastery": 0.39,
                    "questions_completed": 1,
                    "first_attempt_streak": 1,
                },
            }
        }
    )

    next_step = recommendation()
    assert next_step["topic"] == "separable_equations"
    assert next_step["difficulty"] == 1

    generated = generate_from_recommendation(
        next_step,
        seed=2,
    )
    assert generated["metadata"]["rhs_expression"] == "x*y"
    start = client.post(
        "/sessions/start",
        json={
            "problem_id": generated["problem_id"],
        },
    )
    assert start.status_code == 200
    session_id = start.json()["session_id"]

    answers = [
        ("1/y = x", "math"),
        (
            r"\ln\left|y\right|=x^{^2}/2+C",
            "math",
        ),
        (
            r"\operatorname{exp}\left("
            r"\operatorname{ln}\left("
            r"\left|y\right|\right)\right)"
            r"=\operatorname{exp}\left(x^2/2+C\right)",
            "math",
        ),
        (r"|y|=\exp \left(x^{2}/2+C\right)", "math"),
        (
            r"|y|=\exp \left(x^{2}/2\right)"
            r"\cdot \exp \left(C\right)",
            "math",
        ),
        ("|y|=K*exp(x^2/2)", "math"),
        ("y = +/- K*exp(x^2/2)", "math"),
        ("y = C*exp(x^2/2)", "math"),
        ("dy/dx = x*C*exp(x^2/2)", "math"),
        ("x*C*exp(x^2/2)", "math"),
        ("yes", "text"),
    ]

    result = start.json()
    for answer, input_type in answers:
        result = post_answer(
            session_id,
            answer,
            input_type=input_type,
        )

    assert result["status"] == "complete"
    assert result["metadata"]["mastery_key"] == (
        "separable_equations"
    )
    assert result["metadata"]["mastery"] == 0.49

    progress = read_progress()
    separable = progress["skills"][
        "separable_equations"
    ]

    assert separable["mastery"] == 0.49
    assert separable["questions_completed"] == 2
    assert separable["first_attempt_streak"] == 2
    assert separable["last_first_attempt_success"] is True
    assert len(separable["recent_sessions"]) == 1
    assert separable["recent_sessions"][0][
        "completed"
    ] is True
    assert "steps_completed" in separable[
        "recent_sessions"
    ][0]
    assert "total_steps" in separable[
        "recent_sessions"
    ][0]

    next_step = recommendation()

    assert next_step["topic"] == "separable_equations"
    assert next_step["difficulty"] == 3
    assert next_step["metadata"][
        "recent_session_count"
    ] == 1
    assert next_step["metadata"][
        "adjustment_reason"
    ] == "last_session_strong"


def assert_recommendation_metadata_for_history_profiles():
    write_progress({"skills": {}})
    fresh = recommendation()

    assert fresh["recommendation_available"] is True
    assert fresh["metadata"]["recent_session_count"] == 0
    assert fresh["metadata"]["recent_trend"] == (
        "insufficient_history"
    )
    assert "recent_first_attempt_success_rate" in (
        fresh["metadata"]
    )
    assert "base_difficulty" in fresh["metadata"]

    write_progress(
        {
            "skills": {
                "linear_first_order_ode": {
                    "mastery": 0.80,
                    "questions_completed": 3,
                    "first_attempt_streak": 1,
                    "last_total_attempts": 2,
                    "last_incorrect_attempts": 0,
                    "last_hints_used": 0,
                    "last_first_attempt_success": True,
                    "last_completed": True,
                },
                "separable_equations": {
                    "mastery": 0.45,
                    "questions_completed": 1,
                    "first_attempt_streak": 0,
                },
            }
        }
    )
    legacy = recommendation()

    assert legacy["topic"] == "separable_equations"
    assert legacy["difficulty"] == 2
    assert legacy["metadata"]["recent_session_count"] == 0
    assert legacy["metadata"]["adjustment_reason"] == (
        "insufficient_history"
    )

    write_progress(
        {
            "skills": {
                "linear_first_order_ode": {
                    "mastery": 0.80,
                    "questions_completed": 4,
                    "first_attempt_streak": 3,
                    "recent_sessions": [
                        {
                            "completed": True,
                            "total_attempts": 1,
                            "incorrect_attempts": 0,
                            "hints_used": 0,
                            "first_attempt_success": True,
                        },
                        {
                            "completed": True,
                            "total_attempts": 1,
                            "incorrect_attempts": 0,
                            "hints_used": 0,
                            "first_attempt_success": True,
                        },
                        {
                            "completed": True,
                            "total_attempts": 1,
                            "incorrect_attempts": 0,
                            "hints_used": 0,
                            "first_attempt_success": True,
                        },
                    ],
                },
                "separable_equations": {
                    "mastery": 0.62,
                    "questions_completed": 3,
                    "first_attempt_streak": 3,
                    "recent_sessions": [
                        {
                            "completed": True,
                            "total_attempts": 1,
                            "incorrect_attempts": 0,
                            "hints_used": 0,
                            "first_attempt_success": True,
                        },
                        {
                            "completed": True,
                            "total_attempts": 1,
                            "incorrect_attempts": 0,
                            "hints_used": 0,
                            "first_attempt_success": True,
                        },
                        {
                            "completed": True,
                            "total_attempts": 1,
                            "incorrect_attempts": 0,
                            "hints_used": 0,
                            "first_attempt_success": True,
                        },
                    ],
                },
            }
        }
    )
    strong = recommendation()

    assert strong["topic"] == "separable_equations"
    assert strong["difficulty"] == 3
    assert strong["metadata"]["recent_trend"] == "strong"
    assert strong["metadata"]["adjustment"] == 1
    assert strong["metadata"]["recent_session_count"] == 3
    assert "strong" in strong["reason"].lower()

    write_progress(
        {
            "skills": {
                "linear_first_order_ode": {
                    "mastery": 0.80,
                    "questions_completed": 4,
                    "first_attempt_streak": 0,
                },
                "separable_equations": {
                    "mastery": 0.48,
                    "questions_completed": 3,
                    "first_attempt_streak": 0,
                    "recent_sessions": [
                        {
                            "completed": True,
                            "total_attempts": 4,
                            "incorrect_attempts": 2,
                            "hints_used": 2,
                            "first_attempt_success": False,
                        },
                        {
                            "completed": True,
                            "total_attempts": 3,
                            "incorrect_attempts": 2,
                            "hints_used": 1,
                            "first_attempt_success": False,
                        },
                    ],
                },
            }
        }
    )
    weak = recommendation()

    assert weak["topic"] == "separable_equations"
    assert weak["difficulty"] == 1
    assert weak["metadata"]["recent_trend"] == (
        "needs_support"
    )
    assert weak["metadata"]["adjustment"] == -1
    assert "hints" in weak["reason"]


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
        assert_recommends_lower_mastery_ode_topic()
        assert_recommendation_changes_when_mastery_swaps()
        assert_primary_school_static_recommendation()
        assert_no_available_content_is_safe()
        assert_generated_completion_updates_mastery_and_difficulty()
        assert_recommendation_metadata_for_history_profiles()

    finally:
        if had_progress and original_progress is not None:
            DEFAULT_PROGRESS_PATH.write_text(
                original_progress,
                encoding="utf-8",
            )
        elif DEFAULT_PROGRESS_PATH.exists():
            DEFAULT_PROGRESS_PATH.unlink()

    print("adaptive_api tests passed")


if __name__ == "__main__":
    main()
