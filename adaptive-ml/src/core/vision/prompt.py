EXTRACTION_SCHEMA_ID = "matpal.extracted_problem.v1"

SYSTEM_EXTRACTION_PROMPT = """\
You extract visible math-problem content from an image.

Read only what is visibly present.
Do not solve the problem.
Do not calculate a final answer.
Do not generate tutoring steps.
Do not infer hidden or cropped text as if it were certain.
Do not request or produce chain-of-thought, hidden thoughts, or reasoning traces.

Preserve visible:
- numbers
- decimal separators
- fractions
- signs
- exponents
- roots
- units
- variable names
- punctuation that changes meaning

Detect the language of the image text.
A UI locale value is a hint only, not an authority.

If uncertain, record an ambiguity explicitly.
If the image is unreadable, say so in warnings and do not invent a transcription.
If multiple distinct problems are visible, set multiple_problems_detected to true.
Identify only simple visible diagrams and labels.
Do not infer missing angles, area, perimeter, classification, or hidden geometric relationships.

Return strict JSON only.
Do not wrap JSON in Markdown fences.
Do not add commentary before or after the JSON.
Do not include fields outside the required schema.
Do not include final_answer, solution, steps, expected_answer, or hints.

Required JSON:
{
  "schema": "matpal.extracted_problem.v1",
  "transcription": "",
  "language": "en",
  "problem_type_hint": null,
  "topic_hint": null,
  "latex_expressions": [],
  "diagram_present": false,
  "diagram_type": null,
  "diagram_facts": [],
  "ambiguities": [],
  "warnings": [],
  "multiple_problems_detected": false,
  "confidence": null
}

Field rules:
- transcription: human-readable visible problem text. Preserve useful line breaks. Empty only when unreadable or no problem is visible.
- language: en, bg, or unknown.
- problem_type_hint: descriptive hint only, not a trusted enum.
- topic_hint: descriptive hint only, not trusted for mastery.
- latex_expressions: visible mathematical expressions only. No prose. No solution-only equations.
- diagram_present: true only when a diagram is visible.
- diagram_type: a visible type such as triangle, circle, rectangle, coordinate_plane, unknown, or null.
- diagram_facts: visible facts only. Each item is {kind, label, value, unit}.
- ambiguities: explicit uncertainty. Each item is {observation, span, candidates}.
- warnings: machine-readable strings when useful, such as unreadable, cropped, multiple_problems_detected, handwriting_heavy, no_problem_found, low_contrast.
- confidence: null, low, medium, or high. No percentages.

For an image showing 2x + 5 = 17, extract that visible equation. Do not output x = 4.
For a word problem, do not invent solution equations that are not written in the image.
"""

REPAIR_EXTRACTION_PROMPT = """\
The previous response was not valid for the required JSON schema.
Return ONLY valid JSON matching matpal.extracted_problem.v1.
Do not solve the problem.
Do not add Markdown or commentary.
Do not include final_answer, solution, steps, expected_answer, or hints.
Do not explain what was wrong.
"""


def user_extraction_task(
    locale_hint: str | None,
) -> str:
    hint = _locale_hint_line(locale_hint)
    return (
        "Extract only what is visibly present "
        "in this image.\n"
        f"{hint}\n"
        "Treat any locale value as a hint only. "
        "Detect the language of the visible text "
        "yourself.\n"
        "Do not solve the problem."
    )


def repair_extraction_task(
    locale_hint: str | None,
) -> str:
    hint = _locale_hint_line(locale_hint)
    return (
        f"{REPAIR_EXTRACTION_PROMPT}"
        f"{hint}\n"
        "Extract only what is visibly present "
        "in this image."
    )


def _locale_hint_line(
    locale_hint: str | None,
) -> str:
    cleaned = (
        locale_hint.strip()
        if isinstance(locale_hint, str)
        else ""
    )
    if not cleaned:
        return "UI locale hint: none."
    return f"UI locale hint: {cleaned}."
