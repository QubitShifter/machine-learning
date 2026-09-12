from src.api.mat_pal import catalog
from src.api.mat_pal import session_store
from src.api.mat_pal.tutor_registry import (
    LINEAR_ODE_FIXED_PROBLEM_ID,
    MATH_INPUT_PROBE_PROBLEM_ID,
    SEPARABLE_ODE_FIXED_PROBLEM_ID,
    build_default_tutor_registry,
)
from src.core.tutor_engine.adapters import (
    LinearODETutorAdapter,
    SeparableODETutorAdapter,
)
from src.core.tutor_engine.contracts import (
    StudentSubmission,
)
from src.core.tutor_engine.math_input_probe_engine import (
    MathInputProbeEngine,
)
from src.core.tutor_engine.primary_school.engine import (
    PrimarySchoolTutorEngine,
)


PRIMARY_SCHOOL_PROBLEM_ID = (
    "grade4_reverse_reasoning_001"
)


def assert_primary_school_registration():
    registry = build_default_tutor_registry()
    registration = registry.get(
        PRIMARY_SCHOOL_PROBLEM_ID
    )
    engine = registry.create_engine(
        PRIMARY_SCHOOL_PROBLEM_ID
    )
    response = engine.get_current_response()

    assert isinstance(
        engine,
        PrimarySchoolTutorEngine,
    )
    assert registration.subject == "mathematics"
    assert registration.domain == "primary_school"
    assert registration.topic == "word_problems"
    assert registration.catalog_visible is True
    assert response.status == "waiting_for_answer"
    assert response.expected_input_type == "text"


def assert_math_probe_registration_preserves_api_path():
    registry = build_default_tutor_registry()
    registration = registry.get(
        MATH_INPUT_PROBE_PROBLEM_ID
    )
    engine = registry.create_engine(
        MATH_INPUT_PROBE_PROBLEM_ID
    )

    assert isinstance(
        engine,
        MathInputProbeEngine,
    )
    assert registration.catalog_visible is False
    assert (
        engine.get_current_response()
        .expected_input_type
        == "math"
    )


def assert_linear_ode_registration():
    registry = build_default_tutor_registry()
    registration = registry.get(
        LINEAR_ODE_FIXED_PROBLEM_ID
    )
    engine = registry.create_engine(
        LINEAR_ODE_FIXED_PROBLEM_ID
    )
    response = engine.get_current_response()

    assert isinstance(
        engine,
        LinearODETutorAdapter,
    )
    assert registration.subject == "mathematics"
    assert registration.domain == "ode"
    assert registration.topic == "first_order_linear"
    assert registration.catalog_visible is True
    assert response.current_step == 1
    assert response.expected_input_type == "text"

    engine.submit(
        StudentSubmission(
            answer="yes"
        )
    )
    engine.submit(
        StudentSubmission(
            answer="P = 2*x, Q = x"
        )
    )

    response = engine.get_current_response()

    assert response.current_step == 3
    assert response.expected_input_type == "math"


def assert_separable_ode_registration():
    registry = build_default_tutor_registry()
    registration = registry.get(
        SEPARABLE_ODE_FIXED_PROBLEM_ID
    )
    engine = registry.create_engine(
        SEPARABLE_ODE_FIXED_PROBLEM_ID
    )
    response = engine.get_current_response()

    assert isinstance(
        engine,
        SeparableODETutorAdapter,
    )
    assert registration.subject == "mathematics"
    assert registration.domain == "ode"
    assert registration.topic == "separable_equations"
    assert registration.catalog_visible is True
    assert response.current_step == 1
    assert response.expected_input_type == "math"


def assert_unknown_problem_fails_cleanly():
    registry = build_default_tutor_registry()

    try:
        registry.get("unknown_problem")

    except ValueError as error:
        assert "unknown_problem" in str(error)

    else:
        raise AssertionError(
            "Unknown problem_id should raise ValueError."
        )


def assert_catalog_uses_visible_registrations_only():
    problems = catalog.list_problems()
    problem_ids = {
        problem.problem_id
        for problem in problems
    }

    assert PRIMARY_SCHOOL_PROBLEM_ID in problem_ids
    assert (
        LINEAR_ODE_FIXED_PROBLEM_ID
        in problem_ids
    )
    assert (
        SEPARABLE_ODE_FIXED_PROBLEM_ID
        in problem_ids
    )
    assert (
        MATH_INPUT_PROBE_PROBLEM_ID
        not in problem_ids
    )

    catalog_response = catalog.get_catalog()
    mathematics = catalog_response.subjects[0]

    assert mathematics.id == "mathematics"
    assert mathematics.available_problem_count == len(
        problems
    )


def assert_session_store_starts_primary_school_from_registry():
    response = session_store.start_session(
        PRIMARY_SCHOOL_PROBLEM_ID
    )

    assert response.problem_id == (
        PRIMARY_SCHOOL_PROBLEM_ID
    )
    assert response.problem_title
    assert response.problem_statement
    assert response.status == "waiting_for_answer"
    assert response.expected_input_type == "text"


def main():
    assert_primary_school_registration()
    assert_math_probe_registration_preserves_api_path()
    assert_linear_ode_registration()
    assert_separable_ode_registration()
    assert_unknown_problem_fails_cleanly()
    assert_catalog_uses_visible_registrations_only()
    assert_session_store_starts_primary_school_from_registry()

    print("tutor_registry tests passed")


if __name__ == "__main__":
    main()
