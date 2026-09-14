from src.core.i18n.kinematics import kt
from src.core.i18n.locale import normalize_locale
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


def _lang(language: str | None) -> str:
    return normalize_locale(language)


def load_fixed_kinematics_problem(
    language: str | None = None,
) -> KinematicsProblem:
    locale = _lang(language)
    quantities = KinematicsQuantities(
        v0=0.0,
        v=12.0,
        a=3.0,
        t=4.0,
        dx=24.0,
    )
    return KinematicsProblem(
        problem_id=KINEMATICS_FIXED_PROBLEM_ID,
        title=kt(locale, "title.fixed"),
        statement=kt(locale, "statement.fixed"),
        difficulty=2,
        quantities=quantities,
        unknown="v_and_dx",
        steps=build_v_and_dx_steps(quantities, locale),
        metadata={
            "generated": False,
            "subject": "physics",
            "domain": "classical_mechanics",
            "topic": "kinematics",
            "language": locale,
            "variant": "fixed",
        },
    )


def build_v_and_dx_steps(
    quantities: KinematicsQuantities,
    language: str | None = None,
) -> tuple[KinematicsStep, ...]:
    locale = _lang(language)
    return (
        quantity_step(
            "v0",
            kt(locale, "step.identify_v0"),
            kt(locale, "hint.identify_v0_rest"),
        ),
        quantity_step(
            "a",
            kt(locale, "step.identify_a"),
            kt(locale, "hint.identify_a"),
        ),
        quantity_step(
            "t",
            kt(locale, "step.identify_t"),
            kt(locale, "hint.identify_t"),
        ),
        formula_step(
            "velocity",
            kt(locale, "step.formula_velocity_long"),
            kt(locale, "hint.formula_velocity_long"),
        ),
        quantity_step(
            "v",
            kt(locale, "step.calculate_v"),
            kt(locale, "hint.calculate_v"),
        ),
        formula_step(
            "displacement",
            kt(locale, "step.formula_displacement_long"),
            kt(locale, "hint.formula_displacement_long"),
        ),
        quantity_step(
            "dx",
            kt(locale, "step.calculate_dx"),
            kt(locale, "hint.calculate_dx"),
        ),
        summary_step(
            kt(locale, "step.summary_v_dx"),
            kt(locale, "hint.summary_v_dx"),
        ),
    )


def build_find_v_steps(
    quantities: KinematicsQuantities,
    language: str | None = None,
) -> tuple[KinematicsStep, ...]:
    locale = _lang(language)
    return (
        quantity_step(
            "v0",
            kt(locale, "step.identify_v0"),
            kt(locale, "hint.identify_v0"),
        ),
        quantity_step(
            "a",
            kt(locale, "step.identify_a"),
            kt(locale, "hint.identify_a_short"),
        ),
        quantity_step(
            "t",
            kt(locale, "step.identify_t"),
            kt(locale, "hint.identify_t_short"),
        ),
        formula_step(
            "velocity",
            kt(locale, "step.formula_velocity"),
            kt(locale, "hint.formula_velocity"),
        ),
        quantity_step(
            "v",
            kt(locale, "step.calculate_v"),
            kt(locale, "hint.calculate_v_short"),
        ),
        summary_step(
            kt(locale, "step.summary_v"),
            kt(locale, "hint.summary_v"),
        ),
    )


def build_constant_velocity_steps(
    quantities: KinematicsQuantities,
    language: str | None = None,
) -> tuple[KinematicsStep, ...]:
    locale = _lang(language)
    return (
        quantity_step(
            "v",
            kt(locale, "step.identify_v_const"),
            kt(locale, "hint.identify_v_const"),
        ),
        quantity_step(
            "t",
            kt(locale, "step.identify_t"),
            kt(locale, "hint.identify_t_short"),
        ),
        formula_step(
            "constant_velocity",
            kt(locale, "step.formula_const_v"),
            kt(locale, "hint.formula_const_v"),
        ),
        quantity_step(
            "dx",
            kt(locale, "step.calculate_dx"),
            kt(locale, "hint.calculate_dx_vt"),
        ),
        summary_step(
            kt(locale, "step.summary_dx"),
            kt(locale, "hint.summary_dx"),
        ),
    )


def build_find_t_steps(
    quantities: KinematicsQuantities,
    language: str | None = None,
) -> tuple[KinematicsStep, ...]:
    locale = _lang(language)
    return (
        quantity_step(
            "v0",
            kt(locale, "step.identify_v0"),
            kt(locale, "hint.identify_v0"),
        ),
        quantity_step(
            "v",
            kt(locale, "step.identify_v"),
            kt(locale, "hint.identify_v"),
        ),
        quantity_step(
            "a",
            kt(locale, "step.identify_a"),
            kt(locale, "hint.identify_a_sign"),
        ),
        formula_step(
            "time",
            kt(locale, "step.formula_time"),
            kt(locale, "hint.formula_time"),
        ),
        quantity_step(
            "t",
            kt(locale, "step.calculate_t"),
            kt(locale, "hint.calculate_t"),
        ),
        summary_step(
            kt(locale, "step.summary_t"),
            kt(locale, "hint.summary_t"),
        ),
    )


def build_find_dx_from_velocities_steps(
    quantities: KinematicsQuantities,
    language: str | None = None,
) -> tuple[KinematicsStep, ...]:
    locale = _lang(language)
    return (
        quantity_step(
            "v0",
            kt(locale, "step.identify_v0"),
            kt(locale, "hint.identify_v0"),
        ),
        quantity_step(
            "v",
            kt(locale, "step.identify_v"),
            kt(locale, "hint.identify_v"),
        ),
        quantity_step(
            "a",
            kt(locale, "step.identify_a"),
            kt(locale, "hint.identify_a_sign"),
        ),
        formula_step(
            "velocity_sq",
            kt(locale, "step.formula_velocity_sq"),
            kt(locale, "hint.formula_velocity_sq"),
        ),
        quantity_step(
            "dx",
            kt(locale, "step.calculate_dx"),
            kt(locale, "hint.calculate_dx_no_t"),
        ),
        summary_step(
            kt(locale, "step.summary_dx"),
            kt(locale, "hint.summary_dx"),
        ),
    )


def localize_kinematics_problem(
    problem: KinematicsProblem,
    language: str | None,
) -> KinematicsProblem:
    locale = _lang(language)
    variant = problem.metadata.get("variant", "fixed")
    quantities = problem.quantities
    builders = {
        "fixed": build_v_and_dx_steps,
        "from_rest": build_find_v_steps,
        "constant_velocity": build_constant_velocity_steps,
        "v_and_dx": build_v_and_dx_steps,
        "solve_t": build_find_t_steps,
        "solve_dx": build_find_dx_from_velocities_steps,
    }
    builder = builders.get(variant, build_v_and_dx_steps)
    title = (
        kt(locale, "title.fixed")
        if variant == "fixed"
        else kt(locale, "title.generated")
    )
    return KinematicsProblem(
        problem_id=problem.problem_id,
        title=title,
        statement=_localized_statement(problem, locale),
        difficulty=problem.difficulty,
        quantities=quantities,
        steps=builder(quantities, locale),
        unknown=problem.unknown,
        metadata={
            **problem.metadata,
            "language": locale,
        },
    )


def _localized_statement(
    problem: KinematicsProblem,
    locale: str,
) -> str:
    values = problem.quantities
    from src.core.physics.kinematics.checker import (
        format_number,
    )

    variant = problem.metadata.get("variant", "fixed")
    if variant == "fixed":
        return kt(locale, "statement.fixed")

    a = format_number(values.a or 0)
    t = format_number(values.t or 0)
    v = format_number(values.v or 0)
    v0 = format_number(values.v0 or 0)
    if variant == "from_rest":
        return kt(locale, "statement.from_rest", a=a, t=t)
    if variant == "constant_velocity":
        return kt(
            locale,
            "statement.constant_velocity",
            v=v,
            t=t,
        )
    if variant == "v_and_dx":
        motion = (
            kt(locale, "motion.slows")
            if (values.a or 0) < 0
            else kt(locale, "motion.accelerates")
        )
        return kt(
            locale,
            "statement.v_and_dx",
            v0=v0,
            motion=motion,
            a=a,
            t=t,
        )
    if variant == "solve_t":
        return kt(
            locale,
            "statement.solve_t",
            v0=v0,
            v=v,
            a=a,
        )
    if variant == "solve_dx":
        return kt(
            locale,
            "statement.solve_dx",
            v0=v0,
            v=v,
            a=a,
        )
    return problem.statement
