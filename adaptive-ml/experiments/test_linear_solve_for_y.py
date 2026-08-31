import sympy as sp

from src.core.tutor_engine.linear_first_order_checker import (
    evaluate_linear_solve_for_y,
)


x = sp.symbols("x")


#
# Equation:
#
# y' + 2*x*y = x
#
# mu = exp(x**2)
#
# Integrated equation:
#
# exp(x**2)*y = exp(x**2)/2 + C
#
# Therefore:
#
# y = 1/2 + C*exp(-x**2)
#

expected_p = 2 * x
expected_q = x


tests = [
    # Correct canonical form
    "y = 1/2 + C*exp(-x**2)",

    # Equivalent order
    "y = C*exp(-x**2) + 1/2",

    # Equivalent division form
    "y = (exp(x**2)/2 + C)/exp(x**2)",

    # Human-friendly exponent
    "y = 1/2 + C*exp(-x^2)",

    # Missing arbitrary constant
    "y = 1/2",

    # y not isolated
    "exp(x**2)*y = exp(x**2)/2 + C",

    # Wrong sign in exponent
    "y = 1/2 + C*exp(x**2)",
]


for answer in tests:
    result = evaluate_linear_solve_for_y(
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