import sympy as sp

from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)


x = sp.symbols("x")
C = sp.symbols("C")


TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)


def normalize_student_expression(answer: str) -> str:
    answer = answer.strip()

    # Allow y = expression
    if answer.startswith("y="):
        answer = answer[2:].strip()

    if answer.startswith("y ="):
        answer = answer[3:].strip()

    # Some common human-friendly replacements
    answer = answer.replace("×", "*")
    answer = answer.replace("÷", "/")
    answer = answer.replace("X", "x")

    return answer


def parse_math_expression(expression: str):
    return parse_expr(
        expression,
        transformations=TRANSFORMATIONS,
        local_dict={
            "x": x,
            "C": C,
        },
        evaluate=True,
    )


def evaluate_indefinite_solution(
    student_answer: str,
    expected_expression: str
) -> dict:
    student_answer = normalize_student_expression(student_answer)

    try:
        student_expr = parse_math_expression(student_answer)
        expected_expr = parse_math_expression(expected_expression)

    except (
        SyntaxError,
        TypeError,
        ValueError,
        NameError,
        sp.SympifyError,
    ):
        return {
            "correct": False,
            "core_correct": False,
            "missing_constant": False,
            "parse_error": True,
            "error_type": "parse_error",
            "feedback": (
                "I could not understand the mathematical expression."
            ),
            "steps": [
                "You can write multiplication naturally, for example 9x or 9*x.",
                "You can also use ^ or ** for powers, for example x^4 or x**4.",
            ],
        }

    if not isinstance(student_expr, sp.Expr):
        return {
            "correct": False,
            "core_correct": False,
            "missing_constant": False,
            "parse_error": True,
            "error_type": "parse_error",
            "feedback": (
                "I could not understand the mathematical expression."
            ),
            "steps": [],
        }

    if not isinstance(expected_expr, sp.Expr):
        raise ValueError(
            "Expected expression is not a valid SymPy expression."
        )

    student_has_constant = C in student_expr.free_symbols

    student_without_constant = student_expr.subs(C, 0)
    expected_without_constant = expected_expr.subs(C, 0)

    difference = sp.simplify(
        student_without_constant - expected_without_constant
    )

    core_correct = difference == 0

    if core_correct and student_has_constant:
        return {
            "correct": True,
            "core_correct": True,
            "missing_constant": False,
            "parse_error": False,
            "error_type": None,
            "feedback": "Correct.",
            "steps": [],
        }

    if core_correct and not student_has_constant:
        return {
            "correct": False,
            "core_correct": True,
            "missing_constant": True,
            "parse_error": False,
            "error_type": "missing_constant",
            "feedback": (
                "Your integration is correct, but remember "
                "the constant of integration C."
            ),
            "steps": [
                "Your main calculation is correct.",
                "For an indefinite integral, add + C.",
            ],
        }

    rhs = sp.simplify(
        sp.diff(expected_without_constant, x)
    )

    differentiated_rhs = sp.simplify(
        sp.diff(rhs, x)
    )

    if sp.simplify(
        student_without_constant - differentiated_rhs
    ) == 0:
        return {
            "correct": False,
            "core_correct": False,
            "missing_constant": False,
            "parse_error": False,
            "error_type": "differentiated_instead_of_integrated",
            "feedback": (
                "It looks like you differentiated the right-hand "
                "side instead of integrating it."
            ),
            "steps": [
                f"We have dy/dx = {sp.sstr(rhs)}.",
                "We are looking for y, so integrate both sides.",
                f"y = integral({sp.sstr(rhs)}) dx",
                (
                    "Use the power rule: "
                    "integral(x^n) dx = x^(n+1)/(n+1)."
                ),
                "Increase the exponent by 1, then divide by the new exponent.",
                "Finally remember to add + C.",
            ],
        }

    return {
        "correct": False,
        "core_correct": False,
        "missing_constant": False,
        "parse_error": False,
        "error_type": "incorrect_solution",
        "feedback": (
            "That is not the correct antiderivative. "
            "Let's work through the integration."
        ),
        "steps": [
            f"We have dy/dx = {sp.sstr(rhs)}.",
            "To find y, integrate the right-hand side with respect to x.",
            f"Start with: y = integral({sp.sstr(rhs)}) dx",
            "Apply the appropriate integration rule.",
            "Then add the constant of integration + C.",
        ],
    }