import sympy as sp

from src.core.tutor_engine.linear_first_order_checker import (
    evaluate_linear_integration_step,
)


x = sp.symbols("x")


#
# Equation:
#
# y' + 2*x*y = x
#
# mu = exp(x**2)
#
# Product derivative:
#
# d/dx(exp(x**2)*y)
#     = x*exp(x**2)
#
# Integration:
#
# exp(x**2)*y
#     = exp(x**2)/2 + C
#

expected_p = 2 * x
expected_q = x


tests = [
    # Correct
    "exp(x**2)*y = exp(x**2)/2 + C",

    # Equivalent ordering
    "y*exp(x**2) = C + exp(x**2)/2",

    # Equivalent unsimplified coefficient
    "exp(x**2)*y = 0.5*exp(x**2) + C",

    # Missing C
    "exp(x**2)*y = exp(x**2)/2",

    # Wrong left side
    "y = exp(x**2)/2 + C",

    # Wrong integral
    "exp(x**2)*y = x*exp(x**2) + C",
]


for answer in tests:
    result = evaluate_linear_integration_step(
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