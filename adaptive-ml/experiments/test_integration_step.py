import sympy as sp
from sympy.parsing.sympy_parser import parse_expr

from src.core.math_input import (
    normalize_math_text,
)
from src.core.tutor_engine.concept_guidance.separable_stage_checker import (
    TRANSFORMATIONS,
    derive_separable_rhs_parts,
    evaluate_integration_step,
    x,
    y,
)


def trace_browser_style_integration(
    raw_answer: str,
) -> None:
    rhs = "2*x*y"
    input_type = "math"
    normalized = normalize_math_text(
        raw_answer,
        input_type=input_type,
    )
    value_passed_to_checker = normalized
    result = evaluate_integration_step(
        student_answer=value_passed_to_checker,
        rhs_expression=rhs,
    )

    left_text, right_text = value_passed_to_checker.split(
        "=",
        maxsplit=1,
    )
    C = sp.symbols("C")
    local_dict = {
        "x": x,
        "y": y,
        "C": C,
        "log": sp.log,
        "abs": sp.Abs,
        "Abs": sp.Abs,
    }
    parsed_left = parse_expr(
        left_text,
        transformations=TRANSFORMATIONS,
        local_dict=local_dict,
        evaluate=True,
    )
    parsed_right = parse_expr(
        right_text,
        transformations=TRANSFORMATIONS,
        local_dict=local_dict,
        evaluate=True,
    )
    _fx, integrated_fx = derive_separable_rhs_parts(
        rhs
    )

    assert sp.sstr(parsed_left) == "log(Abs(y))"
    assert C in parsed_right.free_symbols
    assert sp.sstr(integrated_fx) == "x**2"
    assert result["correct"]


def assert_current_registered_problem_integration():
    rhs = "2*x*y"

    trace_browser_style_integration(
        r"\ln\left|y\right|=x^{^2}+C"
    )
    trace_browser_style_integration(
        r"\ln\left|y\right|=2\cdot x^{^2}/2+C"
    )

    correct_answers = [
        "ln|y| = x^2 + C",
        "ln(|y|) = x^2 + C",
        "ln|y| = 2*x^2/2 + C",
        "log|y| = 2*x^2/2 + C",
        "log(|y|) = x^2 + C",
        "ln(y) = x^2 + C",
        normalize_math_text(
            r"\ln \left(|y|\right)=x^{2}+C",
            input_type="math",
        ),
        normalize_math_text(
            r"\ln \left(|y|\right)=2\cdot x^{2}/2+C",
            input_type="math",
        ),
    ]

    for answer in correct_answers:
        result = evaluate_integration_step(
            student_answer=answer,
            rhs_expression=rhs,
        )

        assert result["correct"], answer

    unsimplified = evaluate_integration_step(
        student_answer="ln|y| = 2*x^2/2 + C",
        rhs_expression=rhs,
    )
    assert unsimplified["correct"]
    assert unsimplified["suggestion"] is not None
    assert "2*x**2/2" in unsimplified["suggestion"]
    assert "x**2" in unsimplified["suggestion"]

    missing_equals = evaluate_integration_step(
        student_answer="ln(|y|) x^2 + C",
        rhs_expression=rhs,
    )
    assert not missing_equals["correct"]
    assert "x**2" in missing_equals["feedback"]
    assert "5*x^2/2" not in missing_equals["feedback"]
    assert "2*x^3" not in missing_equals["feedback"]
    assert "2*x**3" not in missing_equals["feedback"]

    parse_error = evaluate_integration_step(
        student_answer="ln(|y|) = x^2 + C +",
        rhs_expression=rhs,
    )
    assert not parse_error["correct"]
    assert parse_error["error_type"] == "parse_error"
    assert "x**2" in parse_error["feedback"]
    assert "5*x^2/2" not in parse_error["feedback"]
    assert "2*x^3" not in parse_error["feedback"]
    assert "2*x**3" not in parse_error["feedback"]

    for answer in [
        "ln|y| = x^2",
        "ln|y| = 2*x^2/2",
    ]:
        result = evaluate_integration_step(
            student_answer=answer,
            rhs_expression=rhs,
        )
        assert not result["correct"]
        assert result["error_type"] == "missing_constant"

    wrong_x = evaluate_integration_step(
        student_answer="ln|y| = 2*x + C",
        rhs_expression=rhs,
    )
    assert not wrong_x["correct"]
    assert wrong_x["error_type"] == "incorrect_x_integral"

    for answer in [
        "y = x^2 + C",
        "y^2/2 = x^2 + C",
        "1/y = x^2 + C",
        "exp(y) = x^2 + C",
    ]:
        result = evaluate_integration_step(
            student_answer=answer,
            rhs_expression=rhs,
        )
        assert not result["correct"]
        assert result["error_type"] == "incorrect_y_integral"


def assert_future_rhs_examples():
    result = evaluate_integration_step(
        student_answer="ln|y| = 6*x^2/2 + C",
        rhs_expression="6*x*y",
    )
    assert result["correct"]

    result = evaluate_integration_step(
        student_answer="ln|y| = 3*x^2 + C",
        rhs_expression="6*x*y",
    )
    assert result["correct"]

    result = evaluate_integration_step(
        student_answer="ln|y| = (2/3)*x^3 + C",
        rhs_expression="2*x^2*y",
    )
    assert result["correct"]

    result = evaluate_integration_step(
        student_answer="ln|y| = 2*x^3/3 + C",
        rhs_expression="2*x^2*y",
    )
    assert result["correct"]


def assert_existing_example_still_works():
    rhs = "5*x*y"

    result = evaluate_integration_step(
        student_answer="ln(y) = 5*x^2/2 + C",
        rhs_expression=rhs,
    )
    assert result["correct"]

    result = evaluate_integration_step(
        student_answer="log(y) = 5*x**2/2 + C",
        rhs_expression=rhs,
    )
    assert result["correct"]

    result = evaluate_integration_step(
        student_answer="ln(y) = 5*x^2/2",
        rhs_expression=rhs,
    )
    assert not result["correct"]
    assert result["error_type"] == "missing_constant"


assert_current_registered_problem_integration()
assert_future_rhs_examples()
assert_existing_example_still_works()

print("integration_step tests passed")