from src.api.mat_pal import catalog
from src.api.mat_pal import session_store
from src.api.mat_pal.problem_generation import (
    GeneratorRegistration,
    ProblemGeneratorRegistry,
)
from src.api.mat_pal.tutor_registry import (
    LINEAR_ODE_FIXED_PROBLEM_ID,
    MATH_INPUT_PROBE_PROBLEM_ID,
    SEPARABLE_ODE_FIXED_PROBLEM_ID,
    TutorRegistration,
    TutorRegistry,
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
    physics = catalog_response.subjects[1]

    assert mathematics.id == "mathematics"
    assert physics.id == "physics"
    assert (
        mathematics.available_problem_count
        + physics.available_problem_count
        == len(problems)
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


def _contract_registration(problem_id, create_engine):
    return TutorRegistration(
        problem_id=problem_id,
        title="Factory contract probe",
        problem_statement="Factory contract probe",
        subject="mathematics",
        domain="developer_tools",
        topic="factory_contract",
        topic_name="Factory Contract",
        problem_type="factory_contract",
        total_steps=1,
        expected_input_type="text",
        create_engine=create_engine,
        catalog_visible=False,
    )


def assert_create_engine_passes_normalized_language():
    received = []

    def tracking_factory(language="en"):
        received.append(language)
        return MathInputProbeEngine()

    registry = TutorRegistry()
    registry.register(
        _contract_registration(
            "factory_language_probe",
            tracking_factory,
        )
    )

    registry.create_engine("factory_language_probe")
    registry.create_engine(
        "factory_language_probe",
        language="bg",
    )
    registry.create_engine(
        "factory_language_probe",
        language="de",
    )

    assert received == ["en", "bg", "en"]


def assert_internal_typeerror_propagates_once():
    received = []

    def broken_factory(language="en"):
        received.append(language)
        raise TypeError("internal factory bug")

    registry = TutorRegistry()
    registry.register(
        _contract_registration(
            "broken_factory_probe",
            broken_factory,
        )
    )

    try:
        registry.create_engine("broken_factory_probe")
    except TypeError as error:
        assert str(error) == "internal factory bug"
    else:
        raise AssertionError(
            "internal TypeError must propagate"
        )

    assert received == ["en"]


def assert_generator_language_contract():
    received = []

    def tracking_create(difficulty, seed, language="en"):
        received.append((difficulty, seed, language))
        return _contract_registration(
            "generated_language_probe",
            lambda language="en": MathInputProbeEngine(),
        )

    generators = ProblemGeneratorRegistry()
    generators.register(
        GeneratorRegistration(
            subject="mathematics",
            domain="developer_tools",
            topic="factory_contract",
            topic_name="Factory Contract",
            generator_name="factory_contract",
            supported_difficulties=(1,),
            create_problem=tracking_create,
        )
    )

    generators.generate(
        subject="mathematics",
        domain="developer_tools",
        topic="factory_contract",
        difficulty=1,
    )
    generators.generate(
        subject="mathematics",
        domain="developer_tools",
        topic="factory_contract",
        difficulty=1,
        seed=7,
        language="bg",
    )
    generators.generate(
        subject="mathematics",
        domain="developer_tools",
        topic="factory_contract",
        difficulty=1,
        language="zz",
    )

    assert received == [
        (1, None, "en"),
        (1, 7, "bg"),
        (1, None, "en"),
    ]


def assert_generator_internal_typeerror_propagates_once():
    received = []

    def broken_create(difficulty, seed, language="en"):
        received.append((difficulty, seed, language))
        raise TypeError("internal generator bug")

    generators = ProblemGeneratorRegistry()
    generators.register(
        GeneratorRegistration(
            subject="mathematics",
            domain="developer_tools",
            topic="broken_generator",
            topic_name="Broken Generator",
            generator_name="broken_generator",
            supported_difficulties=(1,),
            create_problem=broken_create,
        )
    )

    try:
        generators.generate(
            subject="mathematics",
            domain="developer_tools",
            topic="broken_generator",
            difficulty=1,
            language="bg",
        )
    except TypeError as error:
        assert str(error) == "internal generator bug"
    else:
        raise AssertionError(
            "internal TypeError must propagate"
        )

    assert received == [(1, None, "bg")]


def main():
    assert_primary_school_registration()
    assert_math_probe_registration_preserves_api_path()
    assert_linear_ode_registration()
    assert_separable_ode_registration()
    assert_unknown_problem_fails_cleanly()
    assert_catalog_uses_visible_registrations_only()
    assert_session_store_starts_primary_school_from_registry()
    assert_create_engine_passes_normalized_language()
    assert_internal_typeerror_propagates_once()
    assert_generator_language_contract()
    assert_generator_internal_typeerror_propagates_once()

    print("tutor_registry tests passed")


if __name__ == "__main__":
    main()
