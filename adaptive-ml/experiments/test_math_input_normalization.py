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

assert (
    normalize_math_text(
        r"|y|=e^{x^2+C}",
        input_type="latex",
    )
    == "|y|=exp(x**2+C)"
)

assert (
    normalize_math_text(
        r"\left|y\right|=e^{x^2+C}",
        input_type="latex",
    )
    == "|y|=exp(x**2+C)"
)

assert (
    normalize_math_text(
        r"\lvert y \rvert=e^{x^2+C}",
        input_type="latex",
    )
    == "|y|=exp(x**2+C)"
)

assert (
    normalize_math_text(
        r"\left\lvert y\right\rvert=e^{x^2+C}",
        input_type="latex",
    )
    == "|y|=exp(x**2+C)"
)

assert (
    normalize_math_text(
        (
            r"\exp \left(\ln \left(|y|\right)\right)"
            r"=\exp \left(x^{2}+C\right)"
        ),
        input_type="latex",
    )
    == "exp(log(Abs(y)))=exp(x**(2)+C)"
)

assert (
    normalize_math_text(
        (
            r"\operatorname{exp}\left("
            r"\operatorname{ln}\left("
            r"\left|y\right|\right)\right)"
            r"=\operatorname{exp}\left(x^2+C\right)"
        ),
        input_type="latex",
    )
    == "exp(log(Abs(y)))=exp(x**2+C)"
)

assert (
    normalize_math_text(
        r"\ln |y|=x^{2}+C",
        input_type="latex",
    )
    == "log(Abs(y))=x**(2)+C"
)

assert (
    normalize_math_text(
        r"\ln |y|=2\cdot x^{2}/2+C",
        input_type="latex",
    )
    == "log(Abs(y))=2* x**(2)/2+C"
)

assert (
    normalize_math_text(
        r"\ln\left|y\right|=x^{^2}+C",
        input_type="latex",
    )
    == "log(Abs(y))=x**(2)+C"
)

assert (
    normalize_math_text(
        r"\ln\left|y\right|=2\cdot x^{^2}/2+C",
        input_type="latex",
    )
    == "log(Abs(y))=2* x**(2)/2+C"
)

assert (
    normalize_math_text(
        r"|y|=Ke^{x^{2}}",
        input_type="latex",
    )
    == "|y|=K*exp(x**(2))"
)

assert (
    normalize_math_text(
        r"\left|y\right|=Ke^{x^{^2}}",
        input_type="latex",
    )
    == "|y|=K*exp(x**(2))"
)

assert (
    normalize_math_text(
        r"\ln\left(\left|y\right|\right)=\frac{2x^2}{2}+C",
        input_type="latex",
    )
    == "log(Abs(y))=(2*x**2)/(2)+C"
)

assert (
    normalize_math_text(
        r"\ln\left|y\right|=x^2+C",
        input_type="latex",
    )
    == "log(Abs(y))=x**2+C"
)

assert (
    normalize_math_text(
        r"\ln{|y|}=x^2+C",
        input_type="latex",
    )
    == "log(Abs(y))=x**2+C"
)

assert (
    normalize_math_text(
        r"\ln\left(\left\vert y\right\vert\right)=x^2+C",
        input_type="latex",
    )
    == "log(Abs(y))=x**2+C"
)

assert (
    normalize_math_text(
        r"\ln \middle|y\middle|=x^2+C",
        input_type="latex",
    )
    == "log(Abs(y))=x**2+C"
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
