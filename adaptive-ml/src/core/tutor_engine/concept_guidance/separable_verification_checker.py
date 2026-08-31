import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

from src.core.tutor_engine.concept_guidance.log_solve_stage_checker import (
    detect_common_function_typo,
)


x = sp.symbols("x")
y = sp.symbols("y")
C = sp.symbols("C")


TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)


def normalize_expression(text: str) -> str:
    text = text.strip()

    text = text.replace("X", "x")
    text = text.replace("Y", "y")

    text = text.replace("×", "*")
    text = text.replace("÷", "/")

    text = text.replace("Exp(", "exp(")
    text = text.replace("EXP(", "exp(")

    text = text.replace("Ln(", "ln(")
    text = text.replace("LN(", "ln(")

    text = text.replace("Log(", "log(")
    text = text.replace("LOG(", "log(")

    text = text.replace("ln(", "log(")

    return text


def parse_math(expression: str):
    return parse_expr(
        expression,
        transformations=TRANSFORMATIONS,
        local_dict={
            "x": x,
            "y": y,
            "C": C,
            "exp": sp.exp,
            "log": sp.log,
        },
        evaluate=True,
    )


def evaluate_derivative_step(
    student_answer: str,
    solution_expression,
) -> dict:
    """
    Student verifies the proposed solution by differentiating it.
    Example:  y = C*exp(-5*x**2/2)
    Expected derivative:  dy/dx = -5*x*C*exp(-5*x**2/2)
    """

    typo_correction = detect_common_function_typo(
    student_answer
    )

    if typo_correction is not None:
        return {
            "correct": False,
            "error_type": "likely_typo",
            "feedback": (
                "I noticed what looks like a function-name typo "
                "in your derivative."
            ),
            "suggestion": (
                f"Did you mean '{typo_correction}'?"
            ),
        }

    answer = normalize_expression(
        student_answer
    )

    expected_derivative = sp.diff(
        solution_expression,
        x,
    )

    # Accept:
    # dy/dx = ...
    # y' = ...
    # ...
    if "=" in answer:
        left_text, right_text = answer.split(
            "=",
            maxsplit=1,
        )

        left_text = left_text.strip()
        right_text = right_text.strip()

        valid_left_forms = {
            "dy/dx",
            "y'",
            "yprime",
        }

        if left_text not in valid_left_forms:
            return {
                "correct": False,
                "error_type": "incorrect_left_side",
                "feedback": (
                    "For this step, write the derivative "
                    "on the left side."
                ),
                "suggestion": (
                    "For example: dy/dx = ..."
                ),
            }

        expression_text = right_text

    else:
        #
        # Also allow the student to enter only
        # the derivative expression.
        #
        expression_text = answer

    try:
        student_derivative = parse_math(
            expression_text
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
            "error_type": "parse_error",
            "feedback": (
                "I could not understand the derivative."
            ),
            "suggestion": (
                "Differentiate the proposed solution "
                "with respect to x."
            ),
        }

    directly_correct = (
        sp.simplify(
            student_derivative
            - expected_derivative
        ) == 0
    )

    after_substitution_correct = (
        sp.simplify(
            student_derivative.subs(
                y,
                solution_expression,
            )
            - expected_derivative
        ) == 0
    )

    mathematically_correct = (
        directly_correct
        or after_substitution_correct
    )

    if mathematically_correct:
        return {
            "correct": True,
            "error_type": None,
            "feedback": (
                "Correct. That is the derivative "
                "of the proposed solution."
            ),
            "suggestion": (
                "Next, substitute the proposed y "
                "into the right-hand side of the "
                "original differential equation."
            ),
        }

    return {
        "correct": False,
        "error_type": "incorrect_derivative",
        "feedback": (
            "That derivative does not match the "
            "derivative of the proposed solution."
        ),
        "suggestion": (
            f"Differentiate: "
            f"y = {sp.sstr(solution_expression)}"
        ),
    }


def evaluate_rhs_substitution_step(
    student_answer: str,
    rhs_expression,
    solution_expression,
) -> dict:
    """
    Student substitutes the proposed solution into
    the RHS of the original ODE.

    Example: dy/dx = -5*x*y
        y = C*exp(-5*x**2/2)
    RHS becomes: -5*x*C*exp(-5*x**2/2)
    """
    typo_correction = detect_common_function_typo(
    student_answer
    )

    if typo_correction is not None:
        return {
            "correct": False,
            "error_type": "likely_typo",
            "feedback": (
                "I noticed what looks like a function-name typo "
                "in your derivative."
            ),
            "suggestion": (
                f"Did you mean '{typo_correction}'?"
            ),
        }

    answer = normalize_expression(
        student_answer
    )

    if "=" in answer:
        _, right_text = answer.split(
            "=",
            maxsplit=1,
        )

        expression_text = right_text.strip()

    else:
        expression_text = answer

    try:
        student_rhs = parse_math(
            expression_text
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
            "error_type": "parse_error",
            "feedback": (
                "I could not understand the substituted "
                "right-hand expression."
            ),
            "suggestion": (
                "Replace y in the original right-hand "
                "side with the proposed solution."
            ),
        }

    expected_rhs = sp.simplify(
        rhs_expression.subs(
            y,
            solution_expression,
        )
    )

    mathematically_correct = (
        sp.simplify(
            student_rhs
            - expected_rhs
        ) == 0
    )

    if mathematically_correct:
        return {
            "correct": True,
            "error_type": None,
            "feedback": (
                "Correct. You substituted the proposed "
                "solution into the original right-hand side."
            ),
            "suggestion": (
                "Now compare this expression with dy/dx. "
                "Do they match?"
            ),
        }

    return {
        "correct": False,
        "error_type": "incorrect_substitution",
        "feedback": (
            "The substituted right-hand side is not "
            "equivalent to the original ODE after "
            "replacing y."
        ),
        "suggestion": (
            f"Start from: "
            f"{sp.sstr(rhs_expression)} "
            f"and replace y with "
            f"{sp.sstr(solution_expression)}."
        ),
    }


def evaluate_verification_confirmation(
    derivative_expression,
    rhs_expression,
    solution_expression,
) -> dict:
    """
    Final symbolic verification.

    This is not based on student wording.
    SymPy checks whether:

        d/dx(solution)
        =
        RHS(x, solution)
    """

    lhs = sp.simplify(
        derivative_expression
    )

    rhs = sp.simplify(
        rhs_expression.subs(
            y,
            solution_expression,
        )
    )

    verified = (
        sp.simplify(
            lhs - rhs
        ) == 0
    )

    if verified:
        return {
            "correct": True,
            "verified": True,
            "feedback": (
                "Verified. The derivative of the proposed "
                "solution matches the right-hand side of "
                "the original differential equation."
            ),
        }

    return {
        "correct": False,
        "verified": False,
        "feedback": (
            "The proposed solution does not satisfy "
            "the original differential equation."
        ),
    }