from fastapi.testclient import TestClient

from src.api.mat_pal.app import app
from src.api.mat_pal.tutor_registry import (
    SEPARABLE_ODE_FIXED_PROBLEM_ID,
)


client = TestClient(app)


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


def start_separable_session() -> dict:
    response = client.post(
        "/sessions/start",
        json={
            "problem_id": (
                SEPARABLE_ODE_FIXED_PROBLEM_ID
            ),
        },
    )

    assert response.status_code == 200
    return response.json()


def assert_browser_step2_payload_advances(
    raw_payload: str,
) -> None:
    data = start_separable_session()
    session_id = data["session_id"]

    data = post_answer(session_id, "1/y = 2*x")
    assert data["status"] == "correct"
    assert data["current_step"] == 2

    malformed = post_answer(
        session_id,
        r"\ln\left|y=x^{^2}+C",
    )
    assert malformed["status"] == "incorrect"
    assert malformed["current_step"] == 2
    assert malformed["metadata"]["error_type"] == (
        "parse_error"
    )

    data = post_answer(session_id, raw_payload)
    assert data["status"] == "correct"
    assert data["current_step"] == 3
    assert data["metadata"]["log_stage"] == "apply_exp"

    if "2\\cdot" in raw_payload:
        assert data["suggestion"] is not None
        assert "simplify" in data["suggestion"]


def assert_full_separable_api_session():
    data = start_separable_session()
    session_id = data["session_id"]

    assert data["problem_id"] == (
        SEPARABLE_ODE_FIXED_PROBLEM_ID
    )
    assert data["expected_input_type"] == "math"
    assert data["current_step"] == 1

    hint_response = client.post(
        f"/sessions/{session_id}/hint"
    )
    assert hint_response.status_code == 200
    hint_data = hint_response.json()
    assert hint_data["status"] == "hint"
    assert hint_data["current_step"] == 1

    data = post_answer(session_id, "1/y = 3*x")
    assert data["status"] == "incorrect"
    assert data["current_step"] == 1

    data = post_answer(session_id, r"\frac{1}{y")
    assert data["status"] == "incorrect"
    assert data["metadata"]["error_type"] == "parse_error"

    data = post_answer(session_id, "1/y = 2*x")
    assert data["status"] == "correct"
    assert data["current_step"] == 2

    data = post_answer(
        session_id,
        "ln(|y|) = x^2 + C +",
    )
    assert data["status"] == "incorrect"
    assert data["metadata"]["error_type"] == "parse_error"
    assert "x**2" in data["feedback"]
    assert "5*x^2/2" not in data["feedback"]
    assert "2*x^3" not in data["feedback"]
    assert "2*x**3" not in data["feedback"]

    data = post_answer(
        session_id,
        (
            r"\ln\left|y\right|"
            r"=2\cdot x^{^2}/2+C"
        ),
    )
    assert data["status"] == "correct"
    assert data["current_step"] == 3
    assert data["problem_id"] == (
        SEPARABLE_ODE_FIXED_PROBLEM_ID
    )
    assert data["metadata"]["integrated_fx"] == "x**2"
    assert "x**2" in data["metadata"]["next_prompt"]
    assert "5*x^2/2" not in data["metadata"]["next_prompt"]
    assert "2*x^3" not in data["metadata"]["next_prompt"]
    assert "2*x**3" not in data["metadata"]["next_prompt"]
    assert data["suggestion"] is not None
    assert "simplify" in data["suggestion"]

    data = post_answer(
        session_id,
        "what is the inverse of ln?",
        input_type="text",
    )
    assert data["status"] == "concept"
    assert data["current_step"] == 3
    assert data["metadata"]["concept_question"] is True

    data = post_answer(
        session_id,
        "exp(ln(|y|)) = exp(x^2 + C + )",
    )
    assert data["status"] == "incorrect"
    assert data["metadata"]["error_type"] == "parse_error"
    assert "x**2" in data["suggestion"]
    assert "5*x^2/2" not in data["suggestion"]
    assert "2*x^3" not in data["suggestion"]
    assert "2*x**3" not in data["suggestion"]
    assert "ln|y|" in data["suggestion"]

    for answer in [
        (
            r"\operatorname{exp}\left("
            r"\operatorname{ln}\left("
            r"\left|y\right|\right)\right)"
            r"=\operatorname{exp}\left(x^2+C\right)"
        ),
        r"\lvert y=e^{x^2+C}",
        r"|y|=\exp \left(x^{2}+C\right)",
        (
            r"|y|=\exp \left(x^{2}\right)"
            r"\cdot \exp \left(C\right)"
        ),
        r"|y|=Ke^{x^{2}}",
        r"y=+/-K\cdot \exp \left(x^{2}\right)",
        r"y=C\cdot \exp \left(x^{2}\right)",
        r"\frac{dy}{dx}=2xCe^{x^2}",
        "2*x*C*exp(x^2)",
    ]:
        data = post_answer(session_id, answer)
        if answer == r"\lvert y=e^{x^2+C}":
            assert data["status"] == "incorrect"
            assert data["metadata"]["error_type"] == (
                "parse_error"
            )
        else:
            assert data["status"] == "correct"
            if answer == r"|y|=Ke^{x^{2}}":
                assert data["metadata"]["log_stage"] == (
                    "remove_absolute_value"
                )

    assert data["metadata"]["comparison"]["left"] == (
        "2*C*x*exp(x**2)"
    )
    assert data["metadata"]["comparison"]["right"] == (
        "2*C*x*exp(x**2)"
    )
    assert data["expected_input_type"] == "text"

    data = post_answer(
        session_id,
        "yes",
        input_type="text",
    )
    assert data["status"] == "complete"
    assert data["completed"] is True
    assert data["current_step"] == 4
    assert data["total_steps"] == 4


def main():
    assert_browser_step2_payload_advances(
        r"\ln\left|y\right|=x^{^2}+C"
    )
    assert_browser_step2_payload_advances(
        r"\ln\left|y\right|=2\cdot x^{^2}/2+C"
    )
    assert_full_separable_api_session()

    print("separable_ode_api_session tests passed")


if __name__ == "__main__":
    main()
