from fastapi.testclient import TestClient

from src.api.mat_pal.app import app
from src.api.mat_pal.generated_problem_store import (
    clear_generated_problems,
)


client = TestClient(app)


def generate_problem(
    topic: str,
    difficulty: int,
    seed: int | None = None,
) -> dict:
    payload = {
        "subject": "mathematics",
        "domain": "ode",
        "topic": topic,
        "difficulty": difficulty,
    }

    if seed is not None:
        payload["seed"] = seed

    response = client.post(
        "/problems/generate",
        json=payload,
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


def assert_catalog_exposes_generation_capability():
    response = client.get("/catalog")

    assert response.status_code == 200

    mathematics = next(
        subject
        for subject in response.json()["subjects"]
        if subject["id"] == "mathematics"
    )
    ode = next(
        domain
        for domain in mathematics["domains"]
        if domain["id"] == "ode"
    )
    topics = {
        topic["id"]: topic
        for topic in ode["topics"]
    }

    assert topics["first_order_linear"][
        "generation_available"
    ] is True
    assert topics["first_order_linear"][
        "supported_difficulties"
    ] == [1, 2, 3]
    assert topics["separable_equations"][
        "generation_available"
    ] is True
    assert topics["separable_equations"][
        "supported_difficulties"
    ] == [1, 2, 3]


def assert_generate_linear_problem_and_complete_session():
    generated = generate_problem(
        topic="first_order_linear",
        difficulty=1,
        seed=2,
    )

    assert generated["generated"] is True
    assert generated["metadata"]["P"] == "1"
    assert generated["metadata"]["Q"] == "1"
    assert generated["metadata"]["difficulty"] == 1
    assert generated["problem_id"].startswith(
        "linear_first_order_generated_"
    )

    detail = client.get(
        f"/problems/{generated['problem_id']}"
    )
    assert detail.status_code == 200
    assert detail.json()["problem_id"] == (
        generated["problem_id"]
    )

    start = client.post(
        "/sessions/start",
        json={
            "problem_id": generated["problem_id"],
        },
    )
    assert start.status_code == 200
    session = start.json()
    session_id = session["session_id"]

    assert session["problem_statement"] == (
        "Solve dy/dx + (1)*y = 1"
    )
    assert session["expected_input_type"] == "text"

    answers = [
        ("yes", "text"),
        ("P=1,Q=1", "text"),
        ("e^x", "math"),
        ("e^x*y' + e^x*y = e^x", "math"),
        ("d/dx(e^x*y)=e^x", "math"),
        ("e^x*y=e^x+C", "math"),
        ("y=1+C*e^(-x)", "math"),
        ("dy/dx=-C*e^(-x)", "math"),
        ("1", "math"),
        ("yes", "text"),
    ]

    result = session
    for answer, input_type in answers:
        result = post_answer(
            session_id,
            answer,
            input_type=input_type,
        )

    assert result["status"] == "complete"
    assert result["completed"] is True


def assert_generate_separable_problem_and_complete_session():
    generated = generate_problem(
        topic="separable_equations",
        difficulty=2,
        seed=9,
    )

    assert generated["generated"] is True
    assert generated["metadata"]["rhs_expression"] == (
        "2*x*y"
    )
    assert generated["problem_id"].startswith(
        "separable_ode_generated_"
    )

    start = client.post(
        "/sessions/start",
        json={
            "problem_id": generated["problem_id"],
        },
    )
    assert start.status_code == 200
    session = start.json()
    session_id = session["session_id"]

    assert session["problem_statement"] == (
        "Solve dy/dx = 2*x*y"
    )
    assert session["expected_input_type"] == "math"

    result = post_answer(
        session_id,
        "1/y = 2*x",
    )
    assert result["status"] == "correct"

    result = post_answer(
        session_id,
        r"\ln\left|y\right|=2\cdot x^{^2}/2+C",
    )
    assert result["status"] == "correct"

    result = post_answer(
        session_id,
        r"\operatorname{exp}\left("
        r"\operatorname{ln}\left("
        r"\left|y\right|\right)\right)"
        r"=\operatorname{exp}\left(x^2+C\right)",
    )
    assert result["status"] == "correct"

    result = post_answer(
        session_id,
        r"|y|=\exp \left(x^{2}+C\right)",
    )
    assert result["status"] == "correct"

    result = post_answer(
        session_id,
        (
            r"|y|=\exp \left(x^{2}\right)"
            r"\cdot \exp \left(C\right)"
        ),
    )
    assert result["status"] == "correct"

    result = post_answer(
        session_id,
        r"|y|=Ke^{x^{2}}",
    )
    assert result["status"] == "correct"
    assert result["metadata"]["log_stage"] == (
        "remove_absolute_value"
    )

    for answer in [
        "y = +/- K*exp(x^2)",
        "y = C*exp(x^2)",
        "dy/dx = 2*x*C*exp(x^2)",
        "2*x*C*exp(x^2)",
    ]:
        result = post_answer(
            session_id,
            answer,
        )
        assert result["status"] == "correct"

    result = post_answer(
        session_id,
        "yes",
        input_type="text",
    )
    assert result["status"] == "complete"
    assert result["completed"] is True


def assert_seed_reproducibility_and_unique_ids():
    first = generate_problem(
        topic="separable_equations",
        difficulty=2,
        seed=12345,
    )
    second = generate_problem(
        topic="separable_equations",
        difficulty=2,
        seed=12345,
    )

    assert first["problem_id"] != second["problem_id"]
    assert first["problem_text"] == second["problem_text"]
    assert first["metadata"]["rhs_expression"] == (
        second["metadata"]["rhs_expression"]
    )


def assert_invalid_generation_requests_return_http_errors():
    for payload in [
        {
            "subject": "unknown",
            "domain": "ode",
            "topic": "first_order_linear",
            "difficulty": 1,
        },
        {
            "subject": "mathematics",
            "domain": "unknown",
            "topic": "first_order_linear",
            "difficulty": 1,
        },
        {
            "subject": "mathematics",
            "domain": "ode",
            "topic": "word_problems",
            "difficulty": 1,
        },
        {
            "subject": "mathematics",
            "domain": "ode",
            "topic": "first_order_linear",
            "difficulty": 4,
        },
    ]:
        response = client.post(
            "/problems/generate",
            json=payload,
        )
        assert response.status_code == 400

    response = client.post(
        "/problems/generate",
        json={
            "subject": "mathematics",
            "domain": "ode",
            "topic": "first_order_linear",
            "difficulty": 1,
            "seed": "not-a-number",
        },
    )
    assert response.status_code == 422


def main():
    clear_generated_problems()
    assert_catalog_exposes_generation_capability()
    assert_generate_linear_problem_and_complete_session()
    assert_generate_separable_problem_and_complete_session()
    assert_seed_reproducibility_and_unique_ids()
    assert_invalid_generation_requests_return_http_errors()

    print("generated_ode_api tests passed")


if __name__ == "__main__":
    main()
