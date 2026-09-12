from src.api.mat_pal import catalog
from src.api.mat_pal.tutor_registry import (
    SEPARABLE_ODE_FIXED_PROBLEM_ID,
    build_default_tutor_registry,
)
from src.core.tutor_engine.adapters import (
    SeparableODETutorAdapter,
)


def assert_registry_constructs_separable_adapter():
    registry = build_default_tutor_registry()
    registration = registry.get(
        SEPARABLE_ODE_FIXED_PROBLEM_ID
    )
    engine = registry.create_engine(
        SEPARABLE_ODE_FIXED_PROBLEM_ID
    )

    assert isinstance(
        engine,
        SeparableODETutorAdapter,
    )
    assert registration.catalog_visible is True
    assert registration.subject == "mathematics"
    assert registration.domain == "ode"
    assert registration.topic == "separable_equations"
    assert registration.topic_name == "Separable Equations"
    assert registration.expected_input_type == "math"


def assert_catalog_contains_separable_problem():
    problems = catalog.list_problems()
    problem_ids = {
        problem.problem_id
        for problem in problems
    }

    assert SEPARABLE_ODE_FIXED_PROBLEM_ID in problem_ids

    detail = catalog.get_problem(
        SEPARABLE_ODE_FIXED_PROBLEM_ID
    )

    assert detail.problem_id == (
        SEPARABLE_ODE_FIXED_PROBLEM_ID
    )
    assert detail.subject == "mathematics"
    assert detail.domain == "ode"
    assert detail.topic == "separable_equations"
    assert detail.expected_input_type == "math"

    catalog_response = catalog.get_catalog()
    mathematics = next(
        subject
        for subject in catalog_response.subjects
        if subject.id == "mathematics"
    )
    ode = next(
        domain
        for domain in mathematics.domains
        if domain.id == "ode"
    )
    separable = next(
        topic
        for topic in ode.topics
        if topic.id == "separable_equations"
    )

    assert separable.name == "Separable Equations"
    assert (
        SEPARABLE_ODE_FIXED_PROBLEM_ID
        in separable.problem_ids
    )


def main():
    assert_registry_constructs_separable_adapter()
    assert_catalog_contains_separable_problem()

    print("separable_ode_catalog tests passed")


if __name__ == "__main__":
    main()
