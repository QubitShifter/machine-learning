import sympy as sp

from src.core.math_input import normalize_math_text
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


# OUTSIDE the for loop
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


def assert_step_3_4_rename_constant_checker():
    step_engine = SeparableLogEngine(
        integrated_fx=x**2
    )

    accepted_answers = [
        "|y| = K*exp(x^2)",
        "|y| = exp(x^2)*K",
        normalize_math_text(
            r"|y|=Ke^{x^{2}}",
            input_type="math",
        ),
        normalize_math_text(
            r"\left|y\right|=Ke^{x^{^2}}",
            input_type="math",
        ),
    ]

    for answer in accepted_answers:
        result = step_engine.evaluate(
            stage=LogSolveStage.RENAME_EXP_CONSTANT,
            student_answer=answer,
        )
        assert result["correct"], answer

    rejected_answers = [
        "|y| = exp(x^2)",
        "|y| = K*x^2",
        "|y| = K*exp(2*x^2)",
    ]

    for answer in rejected_answers:
        result = step_engine.evaluate(
            stage=LogSolveStage.RENAME_EXP_CONSTANT,
            student_answer=answer,
        )
        assert not result["correct"], answer


def assert_step_3_2_instruction_names_the_expression():
    prompt = engine.get_prompt(
        LogSolveStage.CANCEL_LOG
    )

    assert "Simplify the expression" in prompt
    assert "exp(ln|y|)" in prompt
    assert "Simplify exp(ln|y|)." not in prompt


def assert_step_3_6_instruction_is_spaced_prose():
    prompt = engine.get_prompt(
        LogSolveStage.ABSORB_CONSTANT
    )

    assert "Combine +/- K" in prompt
    assert "into one new arbitrary constant C." in prompt
    assert "intoonenewarbitraryconstant" not in prompt
    assert prompt.splitlines()[-1] == (
        "Combine +/- K into one new arbitrary "
        "constant C."
    )


assert_step_3_4_rename_constant_checker()
assert_step_3_2_instruction_names_the_expression()
assert_step_3_6_instruction_is_spaced_prose()

print("separable_log_engine tests passed")


# ALSO OUTSIDE the for loop
print(
    "\n--- Multi-step answer test ---"
)

result = engine.evaluate(
    stage=LogSolveStage.CANCEL_LOG,
    student_answer=(
        "|y| = exp(2*x**3) * exp(C)"
    ),
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
    "Steps completed:",
    result.get(
        "steps_completed"
    ),
)

print(
    "Feedback:",
    result["feedback"],
)