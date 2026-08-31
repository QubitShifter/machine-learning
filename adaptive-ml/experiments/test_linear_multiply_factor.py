import sympy as sp

from src.core.tutor_engine.linear_first_order_checker import (
    evaluate_multiply_by_integrating_factor,
)


x = sp.symbols("x")


#
# Test equation:
#
# y' + 2*x*y = x
#
# mu = exp(x**2)
#
expected_p = 2 * x
expected_q = x


tests = [
    # Correct canonical form
    "exp(x**2)*y' + 2*x*exp(x**2)*y = x*exp(x**2)",

    # Same thing using dy/dx
    "exp(x**2)*dy/dx + 2*x*exp(x**2)*y = x*exp(x**2)",

    # Equivalent ordering
    "y'*exp(x**2) + 2*x*y*exp(x**2) = exp(x**2)*x",

    # Missing mu on second left term
    "exp(x**2)*y' + 2*x*y = x*exp(x**2)",

    # Forgot mu on RHS
    "exp(x**2)*y' + 2*x*exp(x**2)*y = x",

    # Wrong integrating factor
    "exp(2*x**2)*y' + 2*x*exp(2*x**2)*y = x*exp(2*x**2)",
]


for answer in tests:
    result = evaluate_multiply_by_integrating_factor(
        student_answer=answer,
        expected_p=expected_p,
        expected_q=expected_q,
    )

    print(
        "\nAnswer:",
        answer,
    )

    print(
        "Correct:",
        result["correct"],
    )

    print(
        "Error type:",
        result["error_type"],
    )

    print(
        "Feedback:",
        result["feedback"],
    )

    print(
        "Suggestion:",
        result["suggestion"],
    )