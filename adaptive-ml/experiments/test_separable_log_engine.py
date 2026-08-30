import sympy as sp

from src.core.tutor_engine.separable_log_engine import (
    SeparableLogEngine,
)
from src.core.tutor_engine.concept_guidance.separable_session import (
    LogSolveStage,
)


x = sp.symbols("x")

engine = SeparableLogEngine(
    integrated_fx=2 * x**3
)


tests = [
    (
        LogSolveStage.APPLY_EXP,
        "exp(ln(y)) = exp(2*x**3 + C)",
    ),
    (
        LogSolveStage.CANCEL_LOG,
        "|y| = exp(2*x**3 + C)",
    ),
    (
        LogSolveStage.SPLIT_EXPONENTIAL,
        "|y| = exp(2*x**3)*exp(C)",
    ),
    (
        LogSolveStage.RENAME_EXP_CONSTANT,
        "|y| = K*exp(2*x**3)",
    ),
    (
        LogSolveStage.REMOVE_ABSOLUTE_VALUE,
        "y = +/- K*exp(2*x**3)",
    ),
    (
        LogSolveStage.ABSORB_CONSTANT,
        "y = C*exp(2*x**3)",
    ),
]


for stage, answer in tests:
    print(
        f"\n{engine.get_step_title(stage)}"
    )

    result = engine.evaluate(
        stage=stage,
        student_answer=answer,
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
        "Advance:",
        result["advance"],
    )

    print(
        "Feedback:",
        result["feedback"],
    )

    print(
        "Suggestion:",
        result["suggestion"],
    )


print(
    "\n--- Concept question ---"
)

result = engine.evaluate(
    stage=LogSolveStage.RENAME_EXP_CONSTANT,
    student_answer=(
        "why can exp(C) become another constant?"
    ),
)

print(
    "Kind:",
    result["kind"],
)

print(
    "Advance:",
    result["advance"],
)

print(
    "Feedback:",
    result["feedback"],
)