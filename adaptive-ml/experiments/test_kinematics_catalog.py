from src.api.mat_pal import catalog
from src.api.mat_pal.problem_generation import (
    DEFAULT_PROBLEM_GENERATOR_REGISTRY,
)
from src.api.mat_pal.tutor_registry import (
    KINEMATICS_FIXED_PROBLEM_ID,
    build_default_tutor_registry,
)
from src.core.tutor_engine.adapters import (
    KinematicsTutorAdapter,
)


def get_subject(catalog_response, subject_id):
    return next(
        subject
        for subject in catalog_response.subjects
        if subject.id == subject_id
    )


def get_domain(subject, domain_id):
    return next(
        domain
        for domain in subject.domains
        if domain.id == domain_id
    )


def assert_physics_catalog_exposes_kinematics():
    response = catalog.get_catalog()
    physics = get_subject(response, "physics")
    mechanics = get_domain(
        physics,
        "classical_mechanics",
    )
    kinematics = next(
        topic
        for topic in mechanics.topics
        if topic.id == "kinematics"
    )

    assert physics.name == "Physics"
    assert physics.available_problem_count > 0
    assert mechanics.name == "Classical Mechanics"
    assert mechanics.available_problem_count > 0
    assert kinematics.name == "Kinematics"
    assert kinematics.available_problem_count > 0
    assert KINEMATICS_FIXED_PROBLEM_ID in kinematics.problem_ids
    assert kinematics.generation_available is True
    assert kinematics.supported_difficulties == [1, 2, 3]


def assert_registry_instantiates_kinematics_tutor():
    registry = build_default_tutor_registry()
    registration = registry.get(
        KINEMATICS_FIXED_PROBLEM_ID
    )
    engine = registry.create_engine(
        KINEMATICS_FIXED_PROBLEM_ID
    )
    response = engine.get_current_response()

    assert isinstance(engine, KinematicsTutorAdapter)
    assert registration.subject == "physics"
    assert registration.domain == "classical_mechanics"
    assert registration.topic == "kinematics"
    assert registration.catalog_visible is True
    assert registration.expected_input_type == "units"
    assert response.metadata["topic"] == "kinematics"


def assert_generation_is_registered():
    generated = (
        DEFAULT_PROBLEM_GENERATOR_REGISTRY.generate(
            "physics",
            "classical_mechanics",
            "kinematics",
            difficulty=1,
            seed=4,
        )
    )
    assert generated.subject == "physics"
    assert generated.topic == "kinematics"
    assert generated.metadata["generated"] is True
    assert generated.create_engine().get_current_response()


def main():
    assert_physics_catalog_exposes_kinematics()
    assert_registry_instantiates_kinematics_tutor()
    assert_generation_is_registered()
    print("kinematics_catalog tests passed")


if __name__ == "__main__":
    main()
