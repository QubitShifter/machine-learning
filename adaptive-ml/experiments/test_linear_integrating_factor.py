import sympy as sp

from src.core.tutor_engine.linear_first_order_checker import (
    evaluate_integrating_factor,
)


x = sp.symbols("x")


tests = [
    (
        2 * x,
        "exp(x**2)",
    ),
    (
        2 * x,
        "mu = exp(x^2)",
    ),
    (
        2 * x,
        "exp(2*x**2/2)",
    ),
    (
        3,
        "exp(3*x)",
    ),
    (
        -x,
        "exp(-x**2/2)",
    ),
    (
        2 * x,
        "exp(2*x**2)",
    ),
]


for expected_p, answer in tests:
    result = evaluate_integrating_factor(
        student_answer=answer,
        expected_p=expected_p,
    )

    print(
        "\nP(x):",
        expected_p,
    )

    print(
        "Answer:",
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