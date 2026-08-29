import random

import sympy as sp


x = sp.symbols("x")
C = sp.symbols("C")


def generate_direct_integration_question(difficulty: int = 1) -> dict:
    if difficulty == 1:
        a = random.randint(1, 5)
        n = random.randint(1, 3)

    elif difficulty == 2:
        a = random.choice(
            [i for i in range(-10, 11) if i != 0]
        )
        n = random.randint(1, 5)

    elif difficulty == 3:
        a = random.choice(
            [i for i in range(-15, 16) if i != 0]
        )
        n = random.randint(2, 7)

    else:
        raise ValueError("Difficulty must be 1, 2, or 3.")

    rhs = a * x**n

    solution = sp.integrate(rhs, x)

    question_text = f"Solve dy/dx = {sp.sstr(rhs)}"

    answer_expression = solution + C

    return {
        "id": None,
        "source": "generated",
        "topic": "direct_integration",
        "difficulty": difficulty,
        "skills": [
            "solve_direct_integration",
            "basic_indefinite_integration"
        ],
        "question_type": "symbolic",
        "question": question_text,
        "answer": {
            "type": "symbolic",
            "expression": str(answer_expression)
        },
        "parameters": {
            "a": a,
            "n": n
        }
    }