import sympy as sp

from src.core.math_input import (
    normalize_math_text,
    normalize_student_submission,
)
from src.core.tutor_engine.contracts import (
    StudentSubmission,
)
from src.core.tutor_engine.primary_school.checker import (
    evaluate_step_answer,
)


x, yp, C = sp.symbols("x yp C")


def assert_equivalent(
    answer: str,
    expected,
    input_type: str = "math",
) -> None:
    result = normalize_student_submission(
        StudentSubmission(
            answer=answer,
            input_type=input_type,
        )
    )

    assert result.ok, result.error
    assert result.expression is not None
    assert sp.simplify(
        result.expression - expected
    ) == 0


assert_equivalent(
    "x^2",
    x**2,
)

assert_equivalent(
    "2x",
    2 * x,
)

assert_equivalent(
    r"e^{-x^2}",
    sp.exp(-x**2),
    input_type="latex",
)

assert_equivalent(
    r"\exp(-x^2)",
    sp.exp(-x**2),
    input_type="latex",
)

derivative_result = normalize_student_submission(
    StudentSubmission(
        answer=r"\frac{dy}{dx}",
        input_type="latex",
    )
)

assert derivative_result.ok
assert derivative_result.expression == yp

assert_equivalent(
    r"C e^{x^2}",
    C * sp.exp(x**2),
    input_type="latex",
)

assert_equivalent(
    r"\frac{1}{2}x^2",
    sp.Rational(1, 2) * x**2,
    input_type="latex",
)

malformed_fraction = normalize_student_submission(
    StudentSubmission(
        answer=r"\frac{1}{2",
        input_type="latex",
    )
)

assert not malformed_fraction.ok
assert malformed_fraction.expression is None

malformed_exponential = normalize_student_submission(
    StudentSubmission(
        answer=r"e^{",
        input_type="latex",
    )
)

assert not malformed_exponential.ok
assert malformed_exponential.expression is None

text_result = normalize_student_submission(
    StudentSubmission(
        answer=" 7 ",
        input_type="text",
    )
)

assert text_result.ok
assert text_result.normalized == "7"
assert text_result.expression is None

primary_school_result = evaluate_step_answer(
    student_answer=text_result.normalized,
    expected_answer=7,
)

assert primary_school_result["correct"]

assert normalize_math_text(
    "2 × 3",
    input_type="text",
) == "2 * 3"

print(
    "Math input normalization tests passed."
)
