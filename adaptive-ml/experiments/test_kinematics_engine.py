from src.core.physics.kinematics.checker import (
    evaluate_formula,
)
from src.core.physics.kinematics.engine import (
    KinematicsTutorEngine,
)
from src.core.physics.kinematics.problems import (
    KINEMATICS_FIXED_PROBLEM_ID,
    formula_step,
    load_fixed_kinematics_problem,
)
from src.core.tutor_engine.contracts import (
    StudentSubmission,
)


def start_fixed_engine() -> KinematicsTutorEngine:
    return KinematicsTutorEngine(
        load_fixed_kinematics_problem()
    )


def submit(engine, answer, input_type="units"):
    return engine.submit(
        StudentSubmission(
            answer=answer,
            input_type=input_type,
        )
    )


def advance_to_formula_velocity():
    engine = start_fixed_engine()
    submit(engine, "0 m/s")
    submit(engine, "3 m/s^2")
    submit(engine, "4 s")
    return engine


def advance_to_displacement():
    engine = advance_to_formula_velocity()
    submit(engine, "v = v0 + a*t", "math")
    submit(engine, "12 m/s")
    return engine


def assert_fixed_problem_starts():
    engine = start_fixed_engine()
    response = engine.get_current_response()
    problem = engine.problem

    assert problem.problem_id == KINEMATICS_FIXED_PROBLEM_ID
    assert response.status == "waiting_for_answer"
    assert response.current_step == 1
    assert response.total_steps == 8
    assert response.completed is False
    assert response.expected_input_type == "units"
    assert response.metadata["subject"] == "physics"
    assert response.metadata["domain"] == "classical_mechanics"
    assert response.metadata["topic"] == "kinematics"


def assert_quantity_and_formula_steps():
    engine = start_fixed_engine()

    first = submit(engine, "0 m/s")
    assert first.status == "correct"
    assert first.current_step == 2

    second = submit(engine, "3 m/s^2")
    assert second.status == "correct"

    third = submit(engine, "4 s")
    assert third.status == "correct"
    assert third.expected_input_type == "math"

    wrong_formula = submit(
        engine,
        "v**2 = v0**2 + 2*a*dx",
        "math",
    )
    assert wrong_formula.status == "incorrect"

    for formula in (
        "v = v0 + a*t",
        "v-v0 = a*t",
        "a*t + v0 = v",
    ):
        retry = start_fixed_engine()
        submit(retry, "0 m/s")
        submit(retry, "3 m/s^2")
        submit(retry, "4 s")
        accepted = submit(retry, formula, "math")
        assert accepted.status == "correct", formula

    engine = advance_to_formula_velocity()
    submit(engine, "v = v0 + a t", "math")
    velocity = submit(engine, "12 m/s")
    assert velocity.status == "correct"

    for formula in (
        "dx = v0*t + (1/2)*a*t**2",
        "dx = v0*t + 1/2*a*t^2",
        "x - x0 = v0*t + (1/2)*a*t**2",
    ):
        retry = advance_to_displacement()
        accepted = submit(retry, formula, "math")
        assert accepted.status == "correct", formula

    engine = advance_to_displacement()
    submit(engine, "dx = v0*t + (1/2)*a*t**2", "math")
    displacement = submit(engine, "24 m")
    assert displacement.status == "correct"


def assert_units_and_hints_and_completion():
    engine = start_fixed_engine()
    missing = submit(engine, "0")
    assert missing.status == "incorrect"
    assert missing.metadata["error_type"] == "missing_unit"
    assert "unit" in missing.feedback.lower()

    wrong_unit = submit(engine, "0 m")
    assert wrong_unit.status == "incorrect"
    assert wrong_unit.metadata["error_type"] == "wrong_unit"

    hint = engine.request_hint()
    assert hint.status == "hint"
    assert hint.hint_available is True
    assert "rest" in hint.feedback.lower() or "v_0" in hint.feedback

    submit(engine, "0 m/s")
    submit(engine, "3 m/s^2")
    submit(engine, "4 s")
    submit(engine, "v = v0 + a*t", "math")
    submit(engine, "12 m/s")
    submit(engine, "dx = v0*t + (1/2)*a*t**2", "math")
    submit(engine, "24 m")
    complete = submit(
        engine,
        "final velocity = 12 m/s, distance traveled = 24 m",
        "text",
    )
    assert complete.status == "complete"
    assert complete.completed is True
    assert complete.metadata["subject"] == "physics"
    assert complete.metadata["topic"] == "kinematics"


def assert_constant_scalar_formula_equivalence():
    step = formula_step(
        "velocity",
        "formula",
        "hint",
    )

    for formula in (
        "v = v0 + a*t",
        "v-v0 = a*t",
        "a*t + v0 = v",
        "2*v = 2*v0 + 2*a*t",
        "-3*v = -3*v0 - 3*a*t",
        "0.5*v = 0.5*v0 + 0.5*a*t",
        "v_f = v_0 + a*t",
        "v_{f} = v_{0} + a*t",
        r"v_f = v_0 + a\cdot t",
        "v_f = v_0 + at",
        "v_f=v_0+at",
        r"v_\mathrm{f} = v_0 + a*t",
        r"v_{\mathrm{f}} = v_{0} + a*t",
        "v_f-v_0 = a t",
        "2*v_f = 2*v_0 + 2*a*t",
    ):
        result = evaluate_formula(step, formula)
        assert result["correct"] is True, formula

    symbol_multiple = evaluate_formula(
        step,
        "v*(v-v0-a*t) = 0",
    )
    assert symbol_multiple["correct"] is False

    unrelated = evaluate_formula(
        step,
        "dx = v*t",
    )
    assert unrelated["correct"] is False


def assert_displacement_formula_aliases():
    step = formula_step(
        "displacement",
        "formula",
        "hint",
    )

    for formula in (
        "dx = v0*t + (1/2)*a*t^2",
        "dx = v_0*t + (1/2)*a*t^2",
        "Δx = v_0*t + (1/2)*a*t^2",
        r"\Delta x = v_0*t + (1/2)*a*t^2",
        r"\Delta_{x} = v_0*t + (1/2)*a*t^2",
        r"\delta_{x} = v_0*t + (1/2)*a*t^2",
        r"\delta_x = v_0*t + (1/2)*a*t^2",
        "x - x0 = v0*t + (1/2)*a*t^2",
        "x - x_0 = v_0*t + (1/2)*a*t^2",
        r"x - x_{0} = v_0*t + (1/2)*a*t^2",
        r"\delta_{x} = v_0\cdot t + (1/2)*a*t^2",
        "2*dx = 2*v0*t + a*t^2",
        "-3*dx = -3*v0*t - (3/2)*a*t^2",
    ):
        result = evaluate_formula(step, formula)
        assert result["correct"] is True, formula

    constant_velocity = evaluate_formula(
        step,
        "dx = v*t",
    )
    assert constant_velocity["correct"] is False


def main():
    assert_fixed_problem_starts()
    assert_quantity_and_formula_steps()
    assert_constant_scalar_formula_equivalence()
    assert_displacement_formula_aliases()
    assert_units_and_hints_and_completion()
    print("kinematics_engine tests passed")


if __name__ == "__main__":
    main()
