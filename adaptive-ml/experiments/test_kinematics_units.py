from src.core.physics.kinematics.checker import (
    evaluate_quantity,
    evaluate_summary,
)
from src.core.physics.kinematics.models import (
    KinematicsQuantities,
    KinematicsStep,
)
from src.core.physics.kinematics.problems import (
    load_fixed_kinematics_problem,
    quantity_step,
)
from src.core.physics.kinematics.units import (
    normalize_unit,
)


def check(step: KinematicsStep, answer: str) -> dict:
    return evaluate_quantity(
        load_fixed_kinematics_problem(),
        step,
        answer,
    )


def assert_velocity_equivalents():
    step = quantity_step(
        "v",
        "velocity",
        "hint",
    )
    for answer in (
        "12 m/s",
        "12 m s^-1",
        "12 m*s^-1",
    ):
        result = check(step, answer)
        assert result["correct"] is True, answer

    rejected = check(step, "12 m")
    assert rejected["correct"] is False
    assert rejected["error_type"] == "wrong_unit"


def assert_acceleration_equivalents():
    step = quantity_step(
        "a",
        "acceleration",
        "hint",
    )
    for answer in (
        "3 m/s^2",
        "3 m/s²",
        "3 m s^-2",
    ):
        result = check(step, answer)
        assert result["correct"] is True, answer

    rejected = check(step, "3 m/s")
    assert rejected["correct"] is False
    assert rejected["error_type"] == "wrong_unit"


def assert_normalization_is_deterministic():
    assert normalize_unit("m/s²") == "m/s^2"
    assert normalize_unit("m s^-1") == "m/s"
    assert normalize_unit("m*s^-2") == "m/s^2"
    assert normalize_unit("kg") is None
    unused = KinematicsQuantities()
    assert unused.v0 is None


def assert_summary_accepts_quantity_unit_aliases():
    problem = load_fixed_kinematics_problem()

    for answer in (
        "12 m/s, 24 m",
        "v = 12 m s^-1, dx = 24 m",
        "12 m*s^-1 and 24 m",
    ):
        result = evaluate_summary(problem, answer)
        assert result["correct"] is True, answer

    wrong_dimension = evaluate_summary(
        problem,
        "12 m, 24 m",
    )
    assert wrong_dimension["correct"] is False

    missing_displacement = evaluate_summary(
        problem,
        "12 m/s",
    )
    assert missing_displacement["correct"] is False


def main():
    assert_velocity_equivalents()
    assert_acceleration_equivalents()
    assert_normalization_is_deterministic()
    assert_summary_accepts_quantity_unit_aliases()
    print("kinematics_units tests passed")


if __name__ == "__main__":
    main()
