import sympy as sp

from src.core.tutor_engine.linear_first_order_checker import (
    evaluate_product_derivative,
)


x = sp.symbols("x")


#
# Equation:
#
# y' + 2*x*y = x
#
# mu(x) = exp(x**2)
#
# After multiplying:
#
# exp(x**2)y'
# + 2*x*exp(x**2)y
# = x*exp(x**2)
#
# Therefore:
#
# d/dx(exp(x**2)y)
# = x*exp(x**2)
#

expected_p = 2 * x
expected_q = x


tests = [
    # Correct
    "d/dx(exp(x**2)*y) = x*exp(x**2)",

    # Human-friendly implicit multiplication
    "d/dx(exp(x^2)y) = x*exp(x^2)",

    # Alternative notation
    "derivative(exp(x**2)*y) = x*exp(x**2)",

    # Wrong product
    "d/dx(exp(x**2)) = x*exp(x**2)",

    # Correct product, wrong RHS
    "d/dx(exp(x**2)*y) = x",

    # Has not recognized product derivative
    (
        "exp(x**2)*y' "
        "+ 2*x*exp(x**2)*y "
        "= x*exp(x**2)"
    ),
]


for answer in tests:
    result = evaluate_product_derivative(
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