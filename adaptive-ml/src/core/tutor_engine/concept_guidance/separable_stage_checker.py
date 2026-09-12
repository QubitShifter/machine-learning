import sympy as sp
from tokenize import TokenError

from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)


x = sp.symbols("x")
y = sp.symbols("y")


TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)


def normalize_math_text(text: str) -> str:
    text = text.strip()

    text = text.replace("X", "x")
    text = text.replace("Y", "y")
    text = text.replace("×", "*")
    text = text.replace("÷", "/")

    return text


def parse_expression(expression: str) -> sp.Expr:
    return parse_expr(
        expression,
        transformations=TRANSFORMATIONS,
        local_dict={
            "x": x,
            "y": y,
        },
        evaluate=True,
    )


def derive_separable_rhs_parts(
    rhs_expression: str,
) -> tuple[sp.Expr, sp.Expr]:
    rhs = parse_expression(
        rhs_expression
    )
    fx = sp.simplify(
        rhs / y
    )
    integrated_fx = sp.integrate(
        fx,
        x,
    )

    return fx, integrated_fx


def expected_separation_example(
    rhs_expression: str,
) -> str:
    try:
        fx, _integrated_fx = derive_separable_rhs_parts(
            rhs_expression
        )
        return f"1/y = {sp.sstr(fx)}"

    except (
        SyntaxError,
        TypeError,
        ValueError,
        NameError,
        TokenError,
        sp.SympifyError,
    ):
        return "1/y = f(x)"


def expected_integration_example(
    rhs_expression: str,
) -> str:
    try:
        _fx, integrated_fx = derive_separable_rhs_parts(
            rhs_expression
        )
        return f"ln|y| = {sp.sstr(integrated_fx)} + C"

    except (
        SyntaxError,
        TypeError,
        ValueError,
        NameError,
        TokenError,
        sp.SympifyError,
    ):
        return "ln|y| = integral(f(x), x) + C"


def normalize_log_absolute_value_y(
    text: str,
) -> str:
    return text.replace(
        "log|y|",
        "log(Abs(y))",
    ).replace(
        "ln|y|",
        "log(Abs(y))",
    )


def evaluate_separation_step(
    student_answer: str,
    rhs_expression: str,
) -> dict:
    answer = normalize_math_text(
        student_answer
    )

    if "=" not in answer:
        return {
            "correct": False,
            "parse_error": True,
            "error_type": "missing_equals",
            "feedback": (
                "Write the separated equation using '='. "
                f"For example: "
                f"{expected_separation_example(rhs_expression)}"
            ),
        }

    left_text, right_text = answer.split(
        "=",
        maxsplit=1,
    )

    try:
        left = parse_expression(
            left_text
        )

        right = parse_expression(
            right_text
        )

        rhs = parse_expression(
            rhs_expression
        )

    except (
        SyntaxError,
        TypeError,
        ValueError,
        NameError,
        sp.SympifyError,
    ):
        return {
            "correct": False,
            "parse_error": True,
            "error_type": "parse_error",
            "feedback": (
                "I could not understand that separated form. "
                "Try something like: "
                f"{expected_separation_example(rhs_expression)}"
            ),
        }

    fx = sp.simplify(
        rhs / y
    )

    expected_left = 1 / y
    expected_right = fx

    direct_match = (
        sp.simplify(
            left - expected_left
        ) == 0
        and
        sp.simplify(
            right - expected_right
        ) == 0
    )

    reverse_match = (
        sp.simplify(
            left - expected_right
        ) == 0
        and
        sp.simplify(
            right - expected_left
        ) == 0
    )

    if direct_match or reverse_match:
        return {
            "correct": True,
            "parse_error": False,
            "error_type": None,
            "feedback": (
                "Correct. The variables are separated: "
                "the y-expression is on one side and the "
                "x-expression is on the other."
            ),
        }

    return {
        "correct": False,
        "parse_error": False,
        "error_type": "incorrect_separation",
        "feedback": (
            "Not quite. For dy/dx = f(x)*y, divide by y "
            "so the y-side becomes 1/y, while the x-side "
            "keeps f(x)."
        ),
    }


def evaluate_integration_step(
    student_answer: str,
    rhs_expression: str,
) -> dict:
    """
    Validate the result after integrating both sides of

        (1/y) dy = f(x) dx

    Expected form:

        ln|y| = integral(f(x), x) + C

    For backward compatibility we also accept ln(y) or log(y).
    """

    answer = normalize_math_text(
        student_answer
    )

    answer = answer.replace(
        "ln(",
        "log("
    )

    answer = answer.replace(
        "LN(",
        "log("
    )
    answer = normalize_log_absolute_value_y(
        answer
    )

    try:
        fx, integrated_fx = derive_separable_rhs_parts(
            rhs_expression
        )

    except (
        SyntaxError,
        TypeError,
        ValueError,
        NameError,
        TokenError,
        sp.SympifyError,
    ):
        return {
            "correct": False,
            "parse_error": True,
            "error_type": "parse_error",
            "feedback": (
                "I could not understand the differential "
                "equation for this integration step."
            ),
        }

    example = expected_integration_example(
        rhs_expression
    )

    if "=" not in answer:
        return {
            "correct": False,
            "parse_error": True,
            "error_type": "missing_equals",
            "feedback": (
                "Write the result after integrating both sides "
                f"using '='. For example: {example}"
            ),
        }

    left_text, right_text = answer.split(
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

    try:
        left_text = left_text.replace(
            "|y|",
            "Abs(y)",
        )
        left = parse_expr(
            left_text,
            transformations=TRANSFORMATIONS,
            local_dict=local_dict,
            evaluate=True,
        )

        right = parse_expr(
            right_text,
            transformations=TRANSFORMATIONS,
            local_dict=local_dict,
            evaluate=True,
        )
        right_unevaluated = parse_expr(
            right_text,
            transformations=TRANSFORMATIONS,
            local_dict=local_dict,
            evaluate=False,
        )

    except (
        SyntaxError,
        TypeError,
        ValueError,
        NameError,
        TokenError,
        sp.SympifyError,
    ):
        return {
            "correct": False,
            "parse_error": True,
            "error_type": "parse_error",
            "feedback": (
                "I could not understand that integration step. "
                f"Try a form such as: {example}"
            ),
        }

    right_without_constant = right.subs(
        C,
        0
    )
    unevaluated_without_constant = (
        right_unevaluated.subs(
            C,
            0,
        )
    )

    expected_left_values = {
        sp.log(y),
        sp.log(sp.Abs(y)),
    }

    left_correct = any(
        sp.simplify(
            left - expected_left
        )
        == 0
        for expected_left in expected_left_values
    )

    right_correct = (
        sp.simplify(
            right_without_constant
            - integrated_fx
        ) == 0
    )

    has_constant = (
        C in right.free_symbols
    )

    if (
        left_correct
        and right_correct
        and has_constant
    ):
        simplified_integral = sp.simplify(
            unevaluated_without_constant
        )
        suggestion = None

        if (
            sp.simplify(
                simplified_integral
                - integrated_fx
            )
            == 0
            and sp.sstr(
                unevaluated_without_constant
            )
            != sp.sstr(
                simplified_integral
            )
        ):
            suggestion = (
                "Correct. You can simplify "
                f"{sp.sstr(unevaluated_without_constant)} "
                f"to {sp.sstr(simplified_integral)}."
            )

        return {
            "correct": True,
            "parse_error": False,
            "error_type": None,
            "feedback": (
                "Correct. You integrated both sides successfully."
            ),
            "suggestion": suggestion,
        }

    if (
        left_correct
        and right_correct
        and not has_constant
    ):
        return {
            "correct": False,
            "parse_error": False,
            "error_type": "missing_constant",
            "feedback": (
                "The integrations are correct, but this is an "
                "indefinite integral, so remember to include + C."
            ),
        }

    if not left_correct:
        return {
            "correct": False,
            "parse_error": False,
            "error_type": "incorrect_y_integral",
            "feedback": (
                "Look carefully at the y-side. "
                "The integral of 1/y is ln|y|, not a power of y."
            ),
        }

    return {
        "correct": False,
        "parse_error": False,
        "error_type": "incorrect_x_integral",
        "feedback": (
            f"The y-side is correct, but check the x-side. "
            f"You need to integrate {sp.sstr(fx)} with respect to x."
        ),
    }