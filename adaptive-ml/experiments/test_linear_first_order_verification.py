import sympy as sp

from src.core.math_input import normalize_math_text
from src.core.tutor_engine.linear_first_order_engine import (
    LinearFirstOrderEngine,
)
from src.core.tutor_engine.linear_first_order_session import (
    LinearODEStage,
)
from src.core.tutor_engine.linear_first_order_verification import (
    LinearFirstOrderVerificationEngine,
)


x = sp.symbols("x")
C = sp.symbols("C")


EXPECTED_DERIVATIVE = -2 * x * C * sp.exp(
    -(x**2)
)


def make_verification_engine():
    return LinearFirstOrderVerificationEngine(
        p_expression=2 * x,
        q_expression=x,
        solution_expression=(
            C * sp.exp(-(x**2))
            + sp.Rational(1, 2)
        ),
    )


def assert_derivative_form_is_correct(
    raw_answer: str,
    input_type: str,
) -> None:
    answer = normalize_math_text(
        answer=raw_answer,
        input_type=input_type,
    )
    verification_engine = make_verification_engine()

    result = verification_engine.evaluate(
        answer
    )

    assert result["correct"], (
        raw_answer,
        answer,
        result,
    )
    assert (
        verification_engine.student_derivative
        is not None
    )
    assert (
        sp.simplify(
            verification_engine.student_derivative
            - EXPECTED_DERIVATIVE
        )
        == 0
    )


def assert_stage_8_derivative_inputs_parse():
    examples = [
        (
            "-2*x*C*exp(-x**2)",
            "text",
        ),
        (
            "dy/dx = -2*x*C*exp(-x**2)",
            "text",
        ),
        (
            r"-2xCe^{-x^2}",
            "math",
        ),
        (
            r"\frac{dy}{dx}=-2xCe^{-x^2}",
            "math",
        ),
        (
            (
                r"\frac{dy}{dx}="
                r"-2\cdot x\cdot C\cdot e^{-x^2}"
            ),
            "math",
        ),
    ]

    for raw_answer, input_type in examples:
        assert_derivative_form_is_correct(
            raw_answer,
            input_type,
        )


def assert_existing_ode_stage_inputs_still_parse():
    engine = LinearFirstOrderEngine(
        p_expression=2 * x,
        q_expression=x,
    )

    examples = [
        (
            LinearODEStage.IDENTIFY_P_Q,
            {
                "student_p": "2*x",
                "student_q": "x",
            },
        ),
        (
            LinearODEStage.FIND_INTEGRATING_FACTOR,
            {
                "student_answer": "exp(x**2)",
            },
        ),
        (
            LinearODEStage.MULTIPLY_BY_INTEGRATING_FACTOR,
            {
                "student_answer": (
                    "exp(x**2)*y' "
                    "+ 2*x*exp(x**2)*y "
                    "= x*exp(x**2)"
                ),
            },
        ),
        (
            LinearODEStage.RECOGNIZE_PRODUCT_DERIVATIVE,
            {
                "student_answer": (
                    "d/dx(exp(x**2)*y) "
                    "= x*exp(x**2)"
                ),
            },
        ),
        (
            LinearODEStage.INTEGRATE_BOTH_SIDES,
            {
                "student_answer": (
                    "exp(x**2)*y "
                    "= exp(x**2)/2 + C"
                ),
            },
        ),
        (
            LinearODEStage.SOLVE_FOR_Y,
            {
                "student_answer": (
                    "y = 1/2 + C*exp(-x**2)"
                ),
            },
        ),
    ]

    for stage, kwargs in examples:
        result = engine.evaluate(
            stage=stage,
            **kwargs,
        )

        assert result["correct"], (
            stage,
            result,
        )


def assert_malformed_derivative_returns_feedback():
    verification_engine = make_verification_engine()

    result = verification_engine.evaluate(
        "exp(-x**2"
    )

    assert result["correct"] is False
    assert result["error_type"] == "parse_error"
    assert result["feedback"] == (
        "I could not understand the derivative."
    )


def reach_compare(language="en"):
    engine = LinearFirstOrderVerificationEngine(
        p_expression=2 * x,
        q_expression=x,
        solution_expression=(
            C * sp.exp(-(x**2))
            + sp.Rational(1, 2)
        ),
        language=language,
    )
    derivative = engine.evaluate("-2*x*C*exp(-x**2)")
    assert derivative["correct"]
    engine.advance()
    substitution = engine.evaluate("x")
    assert substitution["correct"]
    engine.advance()
    return engine


def assert_english_compare_yes_still_works():
    engine = reach_compare("en")
    result = engine.evaluate("they match")
    assert result["correct"] is True
    assert result["error_type"] is None


def assert_bulgarian_compare_yes_no_phrases():
    yes_answers = (
        "да",
        "да, съвпадат",
        "да съвпадат",
        "съвпадат",
        "равни са",
        "ДА, СЪВПАДАТ!",
        "те съвпадат",
        "еднакви са",
        "да, равни са",
    )
    for answer in yes_answers:
        engine = reach_compare("bg")
        result = engine.evaluate(answer)
        assert result["correct"] is True, answer

    no_answers = (
        "не",
        "не съвпадат",
        "не, не съвпадат",
        "различни са",
        "не са равни",
    )
    for answer in no_answers:
        engine = reach_compare("bg")
        result = engine.evaluate(answer)
        assert result["correct"] is False, answer
        assert result["error_type"] == "comparison_error"

    unrelated = reach_compare("bg")
    result = unrelated.evaluate("не знам")
    assert result["correct"] is False
    assert "The two expressions are mathematically equal." not in (
        result["feedback"]
    )


def main():
    assert_stage_8_derivative_inputs_parse()
    assert_existing_ode_stage_inputs_still_parse()
    assert_malformed_derivative_returns_feedback()
    assert_english_compare_yes_still_works()
    assert_bulgarian_compare_yes_no_phrases()

    print(
        "linear_first_order_verification tests passed"
    )


if __name__ == "__main__":
    main()
