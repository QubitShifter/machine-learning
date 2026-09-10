import json

from fastapi.testclient import TestClient

from src.api.mat_pal.app import app
from src.api.mat_pal.tutor_registry import (
    LINEAR_ODE_FIXED_PROBLEM_ID,
)


PRIMARY_SCHOOL_PROBLEM_ID = (
    "grade4_reverse_reasoning_001"
)


client = TestClient(app)


def print_response(
    label: str,
    payload: dict,
) -> None:
    print(f"\n--- {label} ---")
    print(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
    )


def start_ode_session() -> dict:
    request = {
        "problem_id": LINEAR_ODE_FIXED_PROBLEM_ID,
    }
    response = client.post(
        "/sessions/start",
        json=request,
    )

    assert response.status_code == 200
    data = response.json()

    print_response(
        "ODE start request",
        request,
    )
    print_response(
        "ODE start response",
        data,
    )

    assert data["problem_id"] == (
        LINEAR_ODE_FIXED_PROBLEM_ID
    )
    assert data["problem_title"] == (
        "First-Order Linear ODE"
    )
    assert data["status"] == "waiting_for_answer"
    assert data["current_step"] == 1
    assert data["total_steps"] == 8
    assert data["completed"] is False
    assert data["expected_input_type"] == "text"

    return data


def assert_get_session_uses_generic_endpoint(
    session_id: str,
) -> None:
    response = client.get(
        f"/sessions/{session_id}"
    )

    assert response.status_code == 200
    data = response.json()

    assert data["session_id"] == session_id
    assert data["problem_id"] == (
        LINEAR_ODE_FIXED_PROBLEM_ID
    )


def assert_text_stage_answer(
    session_id: str,
) -> dict:
    response = client.post(
        f"/sessions/{session_id}/answer",
        json={
            "answer": "yes",
            "input_type": "text",
        },
    )

    assert response.status_code == 200
    data = response.json()

    print_response(
        "ODE text-stage answer response",
        data,
    )

    assert data["status"] == "correct"
    assert data["current_step"] == 2
    assert data["expected_input_type"] == "text"

    return data


def assert_hint_response(
    session_id: str,
) -> dict:
    response = client.post(
        f"/sessions/{session_id}/hint"
    )

    assert response.status_code == 200
    data = response.json()

    print_response(
        "ODE hint response",
        data,
    )

    assert data["status"] == "hint"
    assert data["current_step"] == 2
    assert data["completed"] is False

    return data


def assert_concept_question_response(
    session_id: str,
) -> dict:
    response = client.post(
        f"/sessions/{session_id}/answer",
        json={
            "answer": "what is P?",
            "input_type": "text",
        },
    )

    assert response.status_code == 200
    data = response.json()

    print_response(
        "ODE concept-question response",
        data,
    )

    assert data["status"] == "concept"
    assert data["current_step"] == 2
    assert data["expected_input_type"] == "text"
    assert data["metadata"]["concept_question"] is True

    return data


def advance_to_math_stage(
    session_id: str,
) -> dict:
    response = client.post(
        f"/sessions/{session_id}/answer",
        json={
            "answer": "P = 2*x, Q = x",
            "input_type": "text",
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "correct"
    assert data["current_step"] == 3
    assert data["expected_input_type"] == "math"

    return data


def assert_math_stage_answer(
    session_id: str,
) -> dict:
    response = client.post(
        f"/sessions/{session_id}/answer",
        json={
            "answer": r"e^{x^2}",
            "input_type": "math",
        },
    )

    assert response.status_code == 200
    data = response.json()

    print_response(
        "ODE math-stage answer response",
        data,
    )

    assert data["status"] == "correct"
    assert data["current_step"] == 4
    assert data["expected_input_type"] == "math"

    return data


def assert_stage_4_concept_question_response(
    session_id: str,
) -> dict:
    response = client.post(
        f"/sessions/{session_id}/answer",
        json={
            "answer": (
                "why do we need an integrating factor?"
            ),
            "input_type": "text",
        },
    )

    assert response.status_code == 200
    data = response.json()

    print_response(
        "ODE Stage 4 concept-question response",
        data,
    )

    assert data["status"] == "concept"
    assert data["current_step"] == 4
    assert data["expected_input_type"] == "math"
    assert data["metadata"]["concept_question"] is True
    assert data["metadata"]["attempts"] == 0

    return data


def assert_full_ode_completion(
    session_id: str,
) -> dict:
    answers = [
        {
            "answer": (
                r"e^{x^2}*y' + "
                r"2*x*e^{x^2}*y = x*e^{x^2}"
            ),
            "input_type": "math",
            "expected_step": 5,
            "expected_input_type": "math",
        },
        {
            "answer": (
                r"d/dx(e^{x^2}*y) = x*e^{x^2}"
            ),
            "input_type": "math",
            "expected_step": 6,
            "expected_input_type": "math",
        },
        {
            "answer": (
                r"e^{x^2}*y = e^{x^2}/2 + C"
            ),
            "input_type": "math",
            "expected_step": 7,
            "expected_input_type": "math",
        },
        {
            "answer": (
                r"y = 1/2 + C*e^{-x^2}"
            ),
            "input_type": "math",
            "expected_step": 8,
            "expected_input_type": "math",
        },
        {
            "answer": (
                r"\frac{dy}{dx}=-2xCe^{-x^2}"
            ),
            "input_type": "math",
            "expected_step": 8,
            "expected_input_type": "math",
        },
        {
            "answer": "x",
            "input_type": "math",
            "expected_step": 8,
            "expected_input_type": "text",
        },
    ]

    data = None

    for answer in answers:
        response = client.post(
            f"/sessions/{session_id}/answer",
            json={
                "answer": answer["answer"],
                "input_type": answer["input_type"],
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "correct"
        assert data["current_step"] == (
            answer["expected_step"]
        )
        assert data["expected_input_type"] == (
            answer["expected_input_type"]
        )
        assert data["completed"] is False

    assert data is not None
    comparison = data["metadata"]["comparison"]
    print_response(
        "ODE compare metadata",
        comparison,
    )
    assert comparison["kind"] == (
        "expression_comparison"
    )
    assert comparison["title"] == (
        "Verification comparison"
    )
    assert comparison["left_label"] == (
        "Simplified left-hand side"
    )
    assert comparison["left"] == "x"
    assert comparison["right_label"] == (
        "Right-hand side Q(x)"
    )
    assert comparison["right"] == "x"
    assert comparison["question"] == (
        "Do they match?"
    )

    complete_response = client.post(
        f"/sessions/{session_id}/answer",
        json={
            "answer": "yes",
            "input_type": "text",
        },
    )

    assert complete_response.status_code == 200
    complete_data = complete_response.json()

    print_response(
        "ODE completion response",
        complete_data,
    )

    assert complete_data["status"] == "complete"
    assert complete_data["current_step"] == 8
    assert complete_data["total_steps"] == 8
    assert complete_data["completed"] is True

    return complete_data


def assert_malformed_math_response() -> dict:
    start = start_ode_session()
    session_id = start["session_id"]

    assert_text_stage_answer(
        session_id
    )
    advance_to_math_stage(
        session_id
    )

    response = client.post(
        f"/sessions/{session_id}/answer",
        json={
            "answer": r"e^{x^2",
            "input_type": "math",
        },
    )

    assert response.status_code == 200
    data = response.json()

    print_response(
        "ODE malformed-input response",
        data,
    )

    assert data["status"] == "incorrect"
    assert data["current_step"] == 3
    assert data["expected_input_type"] == "math"
    assert data["metadata"]["error_type"] == (
        "parse_error"
    )
    assert data["completed"] is False

    return data


def assert_ode_is_visible_in_catalog() -> None:
    response = client.get("/problems")

    assert response.status_code == 200
    problem_ids = {
        problem["problem_id"]
        for problem in response.json()
    }

    assert (
        LINEAR_ODE_FIXED_PROBLEM_ID
        in problem_ids
    )

    detail_response = client.get(
        f"/problems/{LINEAR_ODE_FIXED_PROBLEM_ID}"
    )

    assert detail_response.status_code == 200
    assert (
        detail_response.json()["problem_id"]
        == LINEAR_ODE_FIXED_PROBLEM_ID
    )


def assert_primary_school_api_regression() -> None:
    start_response = client.post(
        "/sessions/start",
        json={
            "problem_id": PRIMARY_SCHOOL_PROBLEM_ID,
        },
    )

    assert start_response.status_code == 200
    start_data = start_response.json()
    session_id = start_data["session_id"]

    assert start_data["problem_id"] == (
        PRIMARY_SCHOOL_PROBLEM_ID
    )
    assert start_data["expected_input_type"] == "text"

    answer_response = client.post(
        f"/sessions/{session_id}/answer",
        json={
            "answer": "7",
            "input_type": "text",
        },
    )

    assert answer_response.status_code == 200
    answer_data = answer_response.json()

    assert answer_data["status"] == "correct"
    assert answer_data["current_step"] == 2
    assert answer_data["expected_input_type"] == "text"


def main():
    start = start_ode_session()
    session_id = start["session_id"]

    assert_get_session_uses_generic_endpoint(
        session_id
    )
    assert_text_stage_answer(
        session_id
    )
    assert_hint_response(
        session_id
    )
    assert_concept_question_response(
        session_id
    )
    advance_to_math_stage(
        session_id
    )
    assert_math_stage_answer(
        session_id
    )
    assert_stage_4_concept_question_response(
        session_id
    )
    assert_full_ode_completion(
        session_id
    )
    assert_malformed_math_response()
    assert_ode_is_visible_in_catalog()
    assert_primary_school_api_regression()

    print(
        "\nlinear_ode_api_session tests passed"
    )


if __name__ == "__main__":
    main()
