from src.api.mat_pal.problem_generation import (
    DEFAULT_PROBLEM_GENERATOR_REGISTRY,
)
from src.core.tutor_engine.adapters import (
    LinearODETutorAdapter,
    SeparableODETutorAdapter,
)
from src.core.tutor_engine.contracts import (
    StudentSubmission,
)


def assert_registry_finds_supported_ode_generators():
    registry = DEFAULT_PROBLEM_GENERATOR_REGISTRY

    linear = registry.get(
        "mathematics",
        "ode",
        "first_order_linear",
    )
    separable = registry.get(
        "mathematics",
        "ode",
        "separable_equations",
    )

    assert linear.generator_name == "linear_first_order"
    assert separable.generator_name == (
        "separable_equations"
    )
    assert linear.supported_difficulties == (1, 2, 3)
    assert separable.supported_difficulties == (1, 2, 3)


def assert_generated_ids_are_unique_and_seed_is_reproducible():
    registry = DEFAULT_PROBLEM_GENERATOR_REGISTRY

    first = registry.generate(
        "mathematics",
        "ode",
        "first_order_linear",
        difficulty=1,
        seed=2,
    )
    second = registry.generate(
        "mathematics",
        "ode",
        "first_order_linear",
        difficulty=1,
        seed=2,
    )

    assert first.problem_id != second.problem_id
    assert first.metadata["difficulty"] == 1
    assert first.metadata["seed"] == 2
    assert first.metadata["P"] == second.metadata["P"]
    assert first.metadata["Q"] == second.metadata["Q"]
    assert first.problem_statement == second.problem_statement


def assert_generated_linear_constructs_valid_adapter():
    registration = (
        DEFAULT_PROBLEM_GENERATOR_REGISTRY
        .generate(
            "mathematics",
            "ode",
            "first_order_linear",
            difficulty=1,
            seed=2,
        )
    )
    engine = registration.create_engine()
    response = engine.get_current_response()

    assert isinstance(engine, LinearODETutorAdapter)
    assert registration.metadata["generated"] is True
    assert registration.metadata["P"] in (
        registration.problem_statement
    )
    assert registration.metadata["Q"] in (
        registration.problem_statement
    )
    assert response.status == "waiting_for_answer"
    assert response.expected_input_type == "text"

    bad = engine.submit(
        StudentSubmission(
            answer=r"e^{x^2",
            input_type="math",
        )
    )

    assert bad.status == "incorrect"
    assert bad.completed is False


def assert_generated_separable_constructs_valid_adapter():
    registration = (
        DEFAULT_PROBLEM_GENERATOR_REGISTRY
        .generate(
            "mathematics",
            "ode",
            "separable_equations",
            difficulty=2,
            seed=9,
        )
    )
    engine = registration.create_engine()
    response = engine.get_current_response()

    assert isinstance(engine, SeparableODETutorAdapter)
    assert registration.metadata["generated"] is True
    assert registration.metadata["difficulty"] == 2
    assert registration.metadata["rhs_expression"] == "2*x*y"
    assert response.status == "waiting_for_answer"
    assert response.expected_input_type == "math"


def assert_invalid_generation_requests_fail_cleanly():
    registry = DEFAULT_PROBLEM_GENERATOR_REGISTRY

    for subject, domain, topic in [
        ("unknown", "ode", "first_order_linear"),
        ("mathematics", "unknown", "first_order_linear"),
        ("mathematics", "ode", "unknown"),
    ]:
        try:
            registry.generate(
                subject,
                domain,
                topic,
                difficulty=1,
                seed=1,
            )
        except ValueError as error:
            assert "No generator" in str(error)
        else:
            raise AssertionError(
                "Unknown generator should fail."
            )

    try:
        registry.generate(
            "mathematics",
            "ode",
            "first_order_linear",
            difficulty=4,
        )
    except ValueError as error:
        assert "Unsupported difficulty" in str(error)
    else:
        raise AssertionError(
            "Unsupported difficulty should fail."
        )


def main():
    assert_registry_finds_supported_ode_generators()
    assert_generated_ids_are_unique_and_seed_is_reproducible()
    assert_generated_linear_constructs_valid_adapter()
    assert_generated_separable_constructs_valid_adapter()
    assert_invalid_generation_requests_fail_cleanly()

    print("problem_generator_registry tests passed")


if __name__ == "__main__":
    main()
