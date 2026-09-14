import random

from src.core.physics.kinematics.engine import (
    KinematicsTutorEngine,
)
from src.core.physics.kinematics.generator import (
    _solve_for_time,
    generate_kinematics_problem,
    validate_kinematics_problem,
)
from src.core.tutor_engine.adapters.kinematics_adapter import (
    KinematicsTutorAdapter,
)


def assert_difficulties_generate_valid_problems():
    for difficulty in (1, 2, 3):
        for seed in range(50):
            problem = generate_kinematics_problem(
                difficulty=difficulty,
                seed=seed,
            )
            validate_kinematics_problem(problem)
            values = problem.quantities
            assert problem.difficulty == difficulty
            assert values.t is not None and values.t > 0
            assert values.a is not None
            assert values.v is not None
            assert values.dx is not None
            assert values.v == values.v
            assert "m/s" in problem.statement
            if difficulty == 1:
                assert values.a >= 0
                assert values.v0 >= 0
                assert values.dx >= 0
            if difficulty == 3:
                assert values.v >= 0


def assert_seed_is_deterministic():
    first = generate_kinematics_problem(2, seed=11)
    second = generate_kinematics_problem(2, seed=11)
    third = generate_kinematics_problem(2, seed=12)

    assert first.statement == second.statement
    assert first.quantities == second.quantities
    assert first.unknown == second.unknown
    assert first.statement != third.statement or (
        first.quantities != third.quantities
    )


def assert_generated_problem_builds_engine():
    problem = generate_kinematics_problem(
        difficulty=1,
        seed=3,
    )
    engine = KinematicsTutorAdapter(problem)
    response = engine.get_current_response()

    assert isinstance(
        engine.engine,
        KinematicsTutorEngine,
    )
    assert response.completed is False
    assert response.total_steps == problem.total_steps()
    assert response.metadata["topic"] == "kinematics"
    assert response.expected_input_type in {
        "units",
        "math",
        "text",
    }


def assert_difficulty_3_does_not_reverse_direction():
    chooser = random.Random(0)
    for _ in range(40):
        try:
            problem = _solve_for_time(chooser)
        except ValueError as error:
            assert "reversed direction" in str(error) or (
                "divide by zero" in str(error)
                or "not positive" in str(error)
            )
            continue

        assert problem.quantities.v is not None
        assert problem.quantities.v >= 0
        if problem.quantities.a is not None:
            assert problem.quantities.a != 0


def main():
    assert_difficulties_generate_valid_problems()
    assert_difficulty_3_does_not_reverse_direction()
    assert_seed_is_deterministic()
    assert_generated_problem_builds_engine()
    print("kinematics_generator tests passed")


if __name__ == "__main__":
    main()
