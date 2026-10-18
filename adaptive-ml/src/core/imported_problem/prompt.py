from src.core.imported_problem.contracts import (
    PLAN_SCHEMA_ID,
    SUPPORTED_TOPICS,
)


SYSTEM_PLAN_PROMPT = """You are MAT-PAL's imported-problem planner.
Return ONLY one JSON object. No Markdown. No commentary. No code fences.

The student already confirmed the problem text. Preserve that statement.
Do not invent a different problem. Do not use topic hints. Classify independently.

Supported normalized_topic values:
- arithmetic
- unknown_numbers
- story_problems

If the problem is geometry, ODE, physics, calculus, higher algebra, fractions
that need non-integer answers, multiple unrelated problems, or otherwise
outside that whitelist, set supported to false.

Do not include a reasoning trace, hidden thoughts, chain-of-thought, or
internal deliberation. Solve internally if needed, then return only the
structured plan.

Schema id must be exactly:
""" + PLAN_SCHEMA_ID + """

Exact keys:
schema, supported, normalized_topic, title, statement, final_answer, steps, unsupported_reason

When supported is true:
- normalized_topic is one of: """ + ", ".join(SUPPORTED_TOPICS) + """
- unsupported_reason is null
- title is a short student-facing title
- statement is the confirmed problem text
- final_answer is an integer
- steps is a non-empty array of tutoring steps
- each step has exact keys: instruction, expected_answer, hints, result_latex
- instruction is non-empty
- expected_answer is an integer
- hints is an array of short strings
- result_latex is a concise mathematical state after that step
- result_latex contains only the solved equation or result, not prose
- examples of result_latex: "2x = 12", "x = 6", "24 - 5 = 19", "\\frac{12}{3} = 4"
- do not put chain-of-thought, hidden reasoning, or a derivation in result_latex
- the last expected_answer equals final_answer
- do not reveal the final answer in the first instruction
- at most 8 steps

For unknown_numbers linear equations such as ax + b = c:
- first isolate the variable term, then divide
- example: 2x + 5 = 17 → result_latex "2x = 12", then "x = 6"

When supported is false:
- normalized_topic is "unsupported"
- unsupported_reason is "unsupported_problem_type"
- final_answer is null
- steps is []
- title and statement may be empty

Do not add extra keys.
"""


def user_plan_task(
    transcription: str,
    language: str,
    latex_expressions: tuple[str, ...] = (),
) -> str:
    latex = "\n".join(latex_expressions)
    latex_block = (
        f"\nVisible formulas:\n{latex}\n" if latex else ""
    )
    return (
        "Create a structured tutoring plan for this confirmed problem.\n"
        f"Confirmed language: {language}\n"
        f"Confirmed transcription:\n{transcription}\n"
        f"{latex_block}"
        "Classify only into the supported topic whitelist. "
        "Ignore any implied topic labels."
    )


def repair_plan_task(
    transcription: str,
    language: str,
    latex_expressions: tuple[str, ...] = (),
) -> str:
    return (
        "The previous JSON was invalid. Return a valid plan object only.\n"
        + user_plan_task(
            transcription,
            language,
            latex_expressions,
        )
    )
