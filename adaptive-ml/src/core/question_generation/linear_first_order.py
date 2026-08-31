import random

import sympy as sp


x = sp.symbols("x")
y = sp.symbols("y")


def generate_linear_first_order_question(
    difficulty: int = 1,
) -> dict:
    """
    Generate a first-order linear ODE of the form:

        dy/dx + P(x)y = Q(x)

    The first version deliberately uses equations that are
    already written in standard linear form.

    Later difficulties can require the student to rearrange
    the equation before identifying P(x) and Q(x).
    """

    if difficulty == 1:
        p_choices = [
            1,
            2,
            -1,
            -2,
            3,
        ]

        q_choices = [
            1,
            2,
            x,
            2 * x,
            -x,
        ]

    elif difficulty == 2:
        p_choices = [
            x,
            2 * x,
            -x,
            -2 * x,
            3 * x,
        ]

        q_choices = [
            1,
            x,
            x**2,
            2 * x,
            -x,
        ]

    else:
        p_choices = [
            x**2,
            2 * x**2,
            -x**2,
            3 * x,
            -2 * x,
        ]

        q_choices = [
            x,
            x**2,
            2 * x**2,
            x**3,
            -x**2,
        ]

    P = random.choice(
        p_choices
    )

    Q = random.choice(
        q_choices
    )

    question_text = (
        "Solve "
        f"dy/dx + ({sp.sstr(P)})*y "
        f"= {sp.sstr(Q)}"
    )

    return {
        "type": "linear_first_order",
        "difficulty": difficulty,
        "question": question_text,
        "P": sp.sstr(P),
        "Q": sp.sstr(Q),
        "p_expression": P,
        "q_expression": Q,
    }