import random

import sympy as sp


x = sp.symbols("x")
y = sp.symbols("y")


def generate_separable_question(
    difficulty: int = 1
) -> dict:
    if difficulty == 1:
        a = random.randint(1, 5)
        n = random.randint(1, 3)

        rhs = a * x**n * y

        question_text = (
            f"Solve dy/dx = {sp.sstr(rhs)}"
        )

        # dy/y = a*x^n dx
        integral_x = sp.integrate(
            a * x**n,
            x
        )

        answer_text = (
            f"y = C*exp({sp.sstr(integral_x)})"
        )

    elif difficulty == 2:
        a = random.choice(
            [i for i in range(-6, 7) if i != 0]
        )

        rhs = a * x * y

        question_text = (
            f"Solve dy/dx = {sp.sstr(rhs)}"
        )

        integral_x = sp.integrate(
            a * x,
            x
        )

        answer_text = (
            f"y = C*exp({sp.sstr(integral_x)})"
        )

    elif difficulty == 3:
        a = random.choice(
            [i for i in range(-8, 9) if i != 0]
        )
        n = random.randint(2, 5)

        rhs = a * x**n * y

        question_text = (
            f"Solve dy/dx = {sp.sstr(rhs)}"
        )

        integral_x = sp.integrate(
            a * x**n,
            x
        )

        answer_text = (
            f"y = C*exp({sp.sstr(integral_x)})"
        )

    else:
        raise ValueError(
            "Difficulty must be 1, 2, or 3."
        )

    return {
        "id": None,
        "source": "generated",
        "topic": "separable_equations",
        "difficulty": difficulty,
        "skills": [
            "recognize_separable",
            "separate_variables",
            "integrate_separated_equation",
        ],
        "question_type": "symbolic",
        "question": question_text,
        "rhs_expression": sp.sstr(rhs),
        "answer": {
            "type": "symbolic",
            "expression": answer_text,
        },
        "parameters": {
            "a": a,
        },
    }