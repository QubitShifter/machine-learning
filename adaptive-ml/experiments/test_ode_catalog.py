import json

from fastapi.testclient import TestClient

from src.api.mat_pal.app import app
from src.api.mat_pal.tutor_registry import (
    LINEAR_ODE_FIXED_PROBLEM_ID,
    MATH_INPUT_PROBE_PROBLEM_ID,
)


PRIMARY_SCHOOL_PROBLEM_ID = (
    "grade4_reverse_reasoning_001"
)

client = TestClient(app)


def print_json(
    label: str,
    payload,
) -> None:
    print(f"\n--- {label} ---")
    print(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
    )


def get_mathematics_subject(
    catalog_payload: dict,
) -> dict:
    return next(
        subject
        for subject in catalog_payload["subjects"]
        if subject["id"] == "mathematics"
    )


def get_domain(
    subject_payload: dict,
    domain_id: str,
) -> dict:
    return next(
        domain
        for domain in subject_payload["domains"]
        if domain["id"] == domain_id
    )


def assert_ode_catalog_hierarchy() -> None:
    response = client.get("/catalog")

    assert response.status_code == 200
    catalog_payload = response.json()

    print_json(
        "Catalog JSON with ODE entry",
        catalog_payload,
    )

    mathematics = get_mathematics_subject(
        catalog_payload
    )
    ode_domain = get_domain(
        mathematics,
        "ode",
    )

    assert ode_domain["name"] == "ODE"
    assert ode_domain["available_problem_count"] == 1
    assert len(ode_domain["topics"]) == 1

    first_order_topic = ode_domain["topics"][0]

    assert first_order_topic["id"] == (
        "first_order_linear"
    )
    assert first_order_topic["name"] == (
        "First-Order Linear ODEs"
    )
    assert first_order_topic[
        "available_problem_count"
    ] == 1
    assert LINEAR_ODE_FIXED_PROBLEM_ID in (
        first_order_topic["problem_ids"]
    )


def assert_problem_list_contains_primary_and_ode_only() -> None:
    response = client.get("/problems")

    assert response.status_code == 200
    problems = response.json()

    print_json(
        "Problem list with ODE entry",
        problems,
    )

    problem_ids = {
        problem["problem_id"]
        for problem in problems
    }

    assert PRIMARY_SCHOOL_PROBLEM_ID in problem_ids
    assert LINEAR_ODE_FIXED_PROBLEM_ID in problem_ids
    assert (
        MATH_INPUT_PROBE_PROBLEM_ID
        not in problem_ids
    )


def assert_ode_problem_detail_is_selectable() -> None:
    response = client.get(
        f"/problems/{LINEAR_ODE_FIXED_PROBLEM_ID}"
    )

    assert response.status_code == 200
    detail = response.json()

    print_json(
        "ODE problem detail",
        detail,
    )

    assert detail["problem_id"] == (
        LINEAR_ODE_FIXED_PROBLEM_ID
    )
    assert detail["subject"] == "mathematics"
    assert detail["domain"] == "ode"
    assert detail["topic"] == "first_order_linear"
    assert detail["expected_input_type"] == "text"
    assert detail["total_steps"] == 8


def assert_math_probe_remains_hidden() -> None:
    response = client.get(
        f"/problems/{MATH_INPUT_PROBE_PROBLEM_ID}"
    )

    assert response.status_code == 404


def main():
    assert_ode_catalog_hierarchy()
    assert_problem_list_contains_primary_and_ode_only()
    assert_ode_problem_detail_is_selectable()
    assert_math_probe_remains_hidden()

    print("\node_catalog tests passed")


if __name__ == "__main__":
    main()
