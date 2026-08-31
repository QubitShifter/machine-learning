import sympy as sp

from src.core.tutor_engine.linear_first_order_checker import (
    evaluate_p_q_identification,
)


x = sp.symbols("x")


expected_p = 2 * x
expected_q = x**2


tests = [
    (
        "2*x",
        "x**2",
    ),
    (
        "2x",
        "x^2",
    ),
    (
        "x",
        "x**2",
    ),
    (
        "2*x",
        "x",
    ),
    (
        "-2*x",
        "-x**2",
    ),
]


for student_p, student_q in tests:
    result = evaluate_p_q_identification(
        student_p=student_p,
        student_q=student_q,
        expected_p=expected_p,
        expected_q=expected_q,
    )

    print(
        "\nP(x):",
        student_p,
    )

    print(
        "Q(x):",
        student_q,
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