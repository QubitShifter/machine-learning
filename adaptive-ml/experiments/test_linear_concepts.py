import sympy as sp

from src.core.tutor_engine.linear_first_order_engine import (
    LinearFirstOrderEngine,
)

from src.core.tutor_engine.linear_first_order_session import (
    LinearODEStage,
)


x = sp.symbols("x")


engine = LinearFirstOrderEngine(
    p_expression=2 * x,
    q_expression=x,
)


tests = [
    (
        LinearODEStage.FIND_INTEGRATING_FACTOR,
        "why do we need an integrating factor?",
    ),
    (
        LinearODEStage.FIND_INTEGRATING_FACTOR,
        "what is mu?",
    ),
    (
        LinearODEStage.RECOGNIZE_PRODUCT_DERIVATIVE,
        "why does this become a product derivative?",
    ),
    (
        LinearODEStage.RECOGNIZE_PRODUCT_DERIVATIVE,
        "how does the product rule work here?",
    ),
    (
        LinearODEStage.INTEGRATE_BOTH_SIDES,
        "why do we add C?",
    ),
    (
        LinearODEStage.SOLVE_FOR_Y,
        "why do we divide by the integrating factor?",
    ),
]


for stage, question in tests:
    print()
    print(
        "Stage:",
        stage.value,
    )

    print(
        "Question:",
        question,
    )

    result = engine.evaluate(
        stage=stage,
        student_answer=question,
    )

    print(
        "Kind:",
        result.get("kind"),
    )

    print(
        "Correct:",
        result["correct"],
    )

    print(
        "Advance:",
        result.get("advance"),
    )

    print(
        "Feedback:"
    )

    print(
        result["feedback"]
    )