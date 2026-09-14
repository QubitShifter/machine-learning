from __future__ import annotations

import random
from dataclasses import replace

from src.core.physics.kinematics.checker import (
    format_number,
)
from src.core.physics.kinematics.models import (
    KinematicsProblem,
    KinematicsQuantities,
)
from src.core.physics.kinematics.problems import (
    build_constant_velocity_steps,
    build_find_dx_from_velocities_steps,
    build_find_t_steps,
    build_find_v_steps,
    build_v_and_dx_steps,
    localize_kinematics_problem,
)


MAX_GENERATION_ATTEMPTS = 24
MAX_TIME = 30
MAX_SPEED = 50
MAX_ACCEL = 10
MAX_DISPLACEMENT = 500


class KinematicsGenerationError(ValueError):
    pass


def generate_kinematics_problem(
    difficulty: int = 1,
    seed: int | None = None,
    rng: random.Random | None = None,
    language: str | None = None,
) -> KinematicsProblem:
    if difficulty not in {1, 2, 3}:
        raise KinematicsGenerationError(
            f"Unsupported kinematics difficulty {difficulty}."
        )

    chooser = rng or random.Random(seed)
    last_error = "Could not generate a valid kinematics problem."

    for _ in range(MAX_GENERATION_ATTEMPTS):
        try:
            problem = _attempt_problem(difficulty, chooser)
            validate_kinematics_problem(problem)
            return localize_kinematics_problem(
                problem,
                language,
            )
        except ValueError as error:
            last_error = str(error)

    raise KinematicsGenerationError(last_error)


def validate_kinematics_problem(
    problem: KinematicsProblem,
) -> None:
    values = problem.quantities
    required = {
        "v0": values.v0,
        "v": values.v,
        "a": values.a,
        "t": values.t,
        "dx": values.dx,
    }
    if any(item is None for item in required.values()):
        raise ValueError("Generated problem is missing a field.")

    assert values.t is not None
    assert values.v0 is not None
    assert values.v is not None
    assert values.a is not None
    assert values.dx is not None

    if values.t <= 0:
        raise ValueError("Time must be positive.")
    if values.t > MAX_TIME:
        raise ValueError("Time is unreasonably large.")
    if abs(values.a) > MAX_ACCEL:
        raise ValueError("Acceleration is unreasonably large.")
    if abs(values.v0) > MAX_SPEED or abs(values.v) > MAX_SPEED:
        raise ValueError("Velocity is unreasonably large.")
    if abs(values.dx) > MAX_DISPLACEMENT:
        raise ValueError("Displacement is unreasonably large.")

    if not _finite(values.v0, values.v, values.a, values.t, values.dx):
        raise ValueError("Expected answer is not finite.")

    if not _close(values.v, values.v0 + values.a * values.t):
        raise ValueError("Velocity equation is not satisfied.")
    if not _close(
        values.dx,
        values.v0 * values.t + 0.5 * values.a * values.t**2,
    ):
        raise ValueError("Displacement equation is not satisfied.")

    if problem.difficulty == 1:
        if values.t <= 0 or values.a < 0:
            raise ValueError("Difficulty 1 must stay simple and non-negative.")
        if values.v0 < 0 or values.v < 0 or values.dx < 0:
            raise ValueError("Difficulty 1 quantities must be positive.")

    if problem.difficulty == 3 and values.v < 0:
        raise ValueError(
            "Difficulty 3 must not reverse direction."
        )

    if not problem.steps:
        raise ValueError("Generated problem has no tutor steps.")


def _attempt_problem(
    difficulty: int,
    chooser: random.Random,
) -> KinematicsProblem:
    if difficulty == 1:
        if chooser.random() < 0.5:
            return _from_rest_velocity(chooser)
        return _constant_velocity(chooser)

    if difficulty == 2:
        return _two_unknowns(chooser)

    if chooser.random() < 0.5:
        return _solve_for_time(chooser)
    return _solve_for_displacement(chooser)


def _from_rest_velocity(
    chooser: random.Random,
) -> KinematicsProblem:
    v0 = 0
    a = chooser.choice([1, 2, 3, 4, 5])
    t = chooser.choice([2, 3, 4, 5, 6])
    v = v0 + a * t
    dx = v0 * t + 0.5 * a * t**2
    quantities = KinematicsQuantities(
        v0=float(v0),
        v=float(v),
        a=float(a),
        t=float(t),
        dx=float(dx),
    )
    return KinematicsProblem(
        problem_id="kinematics_generated",
        title="Generated 1D kinematics",
        statement=(
            "An object starts from rest and accelerates "
            f"uniformly at ${format_number(a)}\\ "
            f"\\mathrm{{m/s^2}}$ for ${format_number(t)}\\ "
            "\\mathrm{s}$. Find the final velocity."
        ),
        difficulty=1,
        quantities=quantities,
        steps=build_find_v_steps(quantities),
        unknown="v",
        metadata=_metadata(1, "from_rest"),
    )


def _constant_velocity(
    chooser: random.Random,
) -> KinematicsProblem:
    v = chooser.choice([2, 4, 5, 6, 8, 10])
    t = chooser.choice([2, 3, 4, 5])
    dx = v * t
    quantities = KinematicsQuantities(
        v0=float(v),
        v=float(v),
        a=0.0,
        t=float(t),
        dx=float(dx),
    )
    return KinematicsProblem(
        problem_id="kinematics_generated",
        title="Generated 1D kinematics",
        statement=(
            "An object moves at constant velocity "
            f"${format_number(v)}\\ \\mathrm{{m/s}}$ "
            f"for ${format_number(t)}\\ \\mathrm{{s}}$. "
            "Find the displacement."
        ),
        difficulty=1,
        quantities=quantities,
        steps=build_constant_velocity_steps(quantities),
        unknown="dx",
        metadata=_metadata(1, "constant_velocity"),
    )


def _two_unknowns(
    chooser: random.Random,
) -> KinematicsProblem:
    v0 = chooser.choice([2, 3, 4, 5, 6, 8])
    a = chooser.choice([-2, -1, 1, 2, 3])
    t = chooser.choice([2, 3, 4, 5, 6])
    v = v0 + a * t
    if v < 0:
        raise ValueError("Generated velocity became negative.")
    dx = v0 * t + 0.5 * a * t**2
    quantities = KinematicsQuantities(
        v0=float(v0),
        v=float(v),
        a=float(a),
        t=float(t),
        dx=float(dx),
    )
    motion = (
        "slows uniformly"
        if a < 0
        else "accelerates uniformly"
    )
    return KinematicsProblem(
        problem_id="kinematics_generated",
        title="Generated 1D kinematics",
        statement=(
            "An object has initial velocity "
            f"${format_number(v0)}\\ \\mathrm{{m/s}}$ and "
            f"{motion} at ${format_number(a)}\\ "
            f"\\mathrm{{m/s^2}}$ for ${format_number(t)}\\ "
            "\\mathrm{s}$. Find the final velocity and "
            "the displacement."
        ),
        difficulty=2,
        quantities=quantities,
        steps=build_v_and_dx_steps(quantities),
        unknown="v_and_dx",
        metadata=_metadata(2, "v_and_dx"),
    )


def _solve_for_time(
    chooser: random.Random,
) -> KinematicsProblem:
    v0 = chooser.choice([8, 10, 12, 15, 18, 20])
    a = chooser.choice([-4, -3, -2, 2, 3])
    t = chooser.choice([2, 3, 4, 5])
    v = v0 + a * t
    if v == v0 or a == 0:
        raise ValueError("Time solution would divide by zero.")
    if (v - v0) / a <= 0:
        raise ValueError("Time is not positive.")
    if v < 0:
        raise ValueError(
            "Final velocity reversed direction during "
            "the interval."
        )
    dx = v0 * t + 0.5 * a * t**2
    quantities = KinematicsQuantities(
        v0=float(v0),
        v=float(v),
        a=float(a),
        t=float(t),
        dx=float(dx),
    )
    return KinematicsProblem(
        problem_id="kinematics_generated",
        title="Generated 1D kinematics",
        statement=(
            "An object changes from "
            f"${format_number(v0)}\\ \\mathrm{{m/s}}$ to "
            f"${format_number(v)}\\ \\mathrm{{m/s}}$ with "
            f"constant acceleration ${format_number(a)}\\ "
            "\\mathrm{m/s^2}$. Find the elapsed time."
        ),
        difficulty=3,
        quantities=quantities,
        steps=build_find_t_steps(quantities),
        unknown="t",
        metadata=_metadata(3, "solve_t"),
    )


def _solve_for_displacement(
    chooser: random.Random,
) -> KinematicsProblem:
    v0 = chooser.choice([3, 4, 5, 6, 8])
    a = chooser.choice([-2, 2, 3, 4])
    t = chooser.choice([2, 3, 4, 5])
    v = v0 + a * t
    if v < 0 or a == 0:
        raise ValueError("Displacement case is invalid.")
    dx = (v**2 - v0**2) / (2 * a)
    quantities = KinematicsQuantities(
        v0=float(v0),
        v=float(v),
        a=float(a),
        t=float(t),
        dx=float(dx),
    )
    return KinematicsProblem(
        problem_id="kinematics_generated",
        title="Generated 1D kinematics",
        statement=(
            "An object changes from "
            f"${format_number(v0)}\\ \\mathrm{{m/s}}$ to "
            f"${format_number(v)}\\ \\mathrm{{m/s}}$ with "
            f"constant acceleration ${format_number(a)}\\ "
            "\\mathrm{m/s^2}$. Time is not given. "
            "Find the displacement."
        ),
        difficulty=3,
        quantities=quantities,
        steps=build_find_dx_from_velocities_steps(quantities),
        unknown="dx",
        metadata=_metadata(3, "solve_dx"),
    )


def assign_problem_id(
    problem: KinematicsProblem,
    problem_id: str,
) -> KinematicsProblem:
    return replace(problem, problem_id=problem_id)


def _metadata(difficulty: int, variant: str) -> dict:
    return {
        "generated": True,
        "difficulty": difficulty,
        "variant": variant,
        "subject": "physics",
        "domain": "classical_mechanics",
        "topic": "kinematics",
        "given_units": {
            "v0": "m/s",
            "v": "m/s",
            "a": "m/s^2",
            "t": "s",
            "dx": "m",
        },
    }


def _close(left: float, right: float) -> bool:
    return abs(left - right) <= 1e-6


def _finite(*values: float) -> bool:
    return all(
        value == value and abs(value) != float("inf")
        for value in values
    )


