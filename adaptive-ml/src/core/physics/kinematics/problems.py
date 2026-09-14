from src.core.physics.kinematics.models import (
    KinematicsProblem,
    KinematicsQuantities,
    KinematicsStep,
)
from src.core.physics.kinematics.units import (
    QUANTITY_UNITS,
)


KINEMATICS_FIXED_PROBLEM_ID = "kinematics_fixed_001"


def quantity_step(
    quantity: str,
    prompt: str,
    hint: str,
) -> KinematicsStep:
    return KinematicsStep(
        prompt=prompt,
        hint=hint,
        kind="quantity",
        input_type="units",
        quantity=quantity,
        unit=QUANTITY_UNITS[quantity],
    )


def formula_step(
    formula_id: str,
    prompt: str,
    hint: str,
) -> KinematicsStep:
    return KinematicsStep(
        prompt=prompt,
        hint=hint,
        kind="formula",
        input_type="math",
        formula_id=formula_id,
    )


def summary_step(prompt: str, hint: str) -> KinematicsStep:
    return KinematicsStep(
        prompt=prompt,
        hint=hint,
        kind="summary",
        input_type="text",
    )


def load_fixed_kinematics_problem() -> KinematicsProblem:
    quantities = KinematicsQuantities(
        v0=0.0,
        v=12.0,
        a=3.0,
        t=4.0,
        dx=24.0,
    )
    return KinematicsProblem(
        problem_id=KINEMATICS_FIXED_PROBLEM_ID,
        title="Car accelerating from rest",
        statement=(
            "A car starts from rest and accelerates "
            "uniformly at $3\\ \\mathrm{m/s^2}$ for "
            "$4\\ \\mathrm{s}$.\n\n"
            "Find:\n"
            "1. the final velocity\n"
            "2. the distance traveled"
        ),
        difficulty=2,
        quantities=quantities,
        unknown="v_and_dx",
        steps=build_v_and_dx_steps(quantities),
        metadata={
            "generated": False,
            "subject": "physics",
            "domain": "classical_mechanics",
            "topic": "kinematics",
        },
    )


def build_v_and_dx_steps(
    quantities: KinematicsQuantities,
) -> tuple[KinematicsStep, ...]:
    return (
        quantity_step(
            "v0",
            "Identify the initial velocity $v_0$.",
            "Read the starting velocity. Rest means $v_0 = 0$.",
        ),
        quantity_step(
            "a",
            "Identify the acceleration $a$.",
            "Acceleration is the given constant rate "
            "of change of velocity.",
        ),
        quantity_step(
            "t",
            "Identify the elapsed time $t$.",
            "Use the time interval stated in the problem.",
        ),
        formula_step(
            "velocity",
            "Choose the equation for final velocity "
            "when acceleration is constant.",
            "Which equation connects initial velocity, "
            "acceleration, and time directly?",
        ),
        quantity_step(
            "v",
            "Calculate the final velocity $v$.",
            "Substitute the known $v_0$, $a$, and $t$ "
            "into $v = v_0 + at$.",
        ),
        formula_step(
            "displacement",
            "Choose the equation for displacement "
            "when $v_0$, $a$, and $t$ are known.",
            "Since acceleration is constant and time "
            "is known, use the equation containing "
            "$v_0$, $a$, and $t$.",
        ),
        quantity_step(
            "dx",
            "Calculate the displacement $\\Delta x$.",
            "Substitute into "
            "$\\Delta x = v_0 t + \\frac{1}{2} a t^2$.",
        ),
        summary_step(
            "State the final velocity and the "
            "distance traveled, including SI units.",
            "Report both $v$ and $\\Delta x$ with units.",
        ),
    )


def build_find_v_steps(
    quantities: KinematicsQuantities,
) -> tuple[KinematicsStep, ...]:
    return (
        quantity_step(
            "v0",
            "Identify the initial velocity $v_0$.",
            "Read $v_0$ from the problem statement.",
        ),
        quantity_step(
            "a",
            "Identify the acceleration $a$.",
            "Acceleration is given and constant.",
        ),
        quantity_step(
            "t",
            "Identify the elapsed time $t$.",
            "Use the given time interval.",
        ),
        formula_step(
            "velocity",
            "Choose the equation for final velocity.",
            "Which equation connects $v_0$, $a$, and $t$?",
        ),
        quantity_step(
            "v",
            "Calculate the final velocity $v$.",
            "Substitute the known values into "
            "$v = v_0 + at$.",
        ),
        summary_step(
            "State the final velocity with its SI unit.",
            "Include both the number and m/s.",
        ),
    )


def build_constant_velocity_steps(
    quantities: KinematicsQuantities,
) -> tuple[KinematicsStep, ...]:
    return (
        quantity_step(
            "v",
            "Identify the constant velocity $v$.",
            "Speed does not change in this problem.",
        ),
        quantity_step(
            "t",
            "Identify the elapsed time $t$.",
            "Use the given time interval.",
        ),
        formula_step(
            "constant_velocity",
            "Choose the displacement equation for "
            "constant velocity.",
            "With $a = 0$, displacement is velocity "
            "times time.",
        ),
        quantity_step(
            "dx",
            "Calculate the displacement $\\Delta x$.",
            "Use $\\Delta x = v t$.",
        ),
        summary_step(
            "State the displacement with its SI unit.",
            "Include both the number and m.",
        ),
    )


def build_find_t_steps(
    quantities: KinematicsQuantities,
) -> tuple[KinematicsStep, ...]:
    return (
        quantity_step(
            "v0",
            "Identify the initial velocity $v_0$.",
            "Read $v_0$ from the problem statement.",
        ),
        quantity_step(
            "v",
            "Identify the final velocity $v$.",
            "Read the later velocity from the statement.",
        ),
        quantity_step(
            "a",
            "Identify the acceleration $a$.",
            "Pay attention to the sign of acceleration.",
        ),
        formula_step(
            "time",
            "Choose the equation that finds $t$ "
            "from $v$, $v_0$, and $a$.",
            "Rearrange $v = v_0 + at$ to solve for time.",
        ),
        quantity_step(
            "t",
            "Calculate the elapsed time $t$.",
            "Use $t = (v - v_0)/a$. Time must be positive.",
        ),
        summary_step(
            "State the elapsed time with its SI unit.",
            "Include both the number and s.",
        ),
    )


def build_find_dx_from_velocities_steps(
    quantities: KinematicsQuantities,
) -> tuple[KinematicsStep, ...]:
    return (
        quantity_step(
            "v0",
            "Identify the initial velocity $v_0$.",
            "Read $v_0$ from the problem statement.",
        ),
        quantity_step(
            "v",
            "Identify the final velocity $v$.",
            "Read the later velocity from the statement.",
        ),
        quantity_step(
            "a",
            "Identify the acceleration $a$.",
            "Pay attention to the sign of acceleration.",
        ),
        formula_step(
            "velocity_sq",
            "Choose an equation for $\\Delta x$ that "
            "does not require time.",
            "Use $v^2 = v_0^2 + 2 a \\Delta x$ when "
            "$t$ is unknown.",
        ),
        quantity_step(
            "dx",
            "Calculate the displacement $\\Delta x$.",
            "Rearrange to "
            "$\\Delta x = (v^2 - v_0^2)/(2a)$.",
        ),
        summary_step(
            "State the displacement with its SI unit.",
            "Include both the number and m.",
        ),
    )

