import json

from src.core.imported_problem.contracts import (
    PLAN_SCHEMA_ID,
    PlannedStep,
    StructuredSolutionPlan,
    SUPPORTED_TOPICS,
    UNSUPPORTED_REASON,
)
from src.core.imported_problem.errors import (
    ImportedPlanParseError,
)


REQUIRED_KEYS = frozenset(
    {
        "schema",
        "supported",
        "normalized_topic",
        "title",
        "statement",
        "final_answer",
        "steps",
        "unsupported_reason",
    }
)
STEP_KEYS = frozenset(
    {
        "instruction",
        "expected_answer",
        "hints",
    }
)
OPTIONAL_STEP_KEYS = frozenset(
    {
        "result_latex",
    }
)
MAX_STEPS = 8
MAX_TITLE_CHARS = 120
MAX_TEXT_CHARS = 800
MAX_RESULT_LATEX_CHARS = 160
MAX_ANSWER_ABS = 10_000_000


def parse_solution_plan(raw: str) -> StructuredSolutionPlan:
    payload = load_strict_json_object(raw)
    extra = set(payload) - REQUIRED_KEYS
    missing = REQUIRED_KEYS - set(payload)
    if extra or missing:
        raise ImportedPlanParseError(
            "Solution plan has unexpected keys."
        )
    if payload["schema"] != PLAN_SCHEMA_ID:
        raise ImportedPlanParseError(
            "Unknown solution-plan schema."
        )

    supported = payload["supported"]
    if not isinstance(supported, bool):
        raise ImportedPlanParseError("Invalid supported flag.")

    topic = require_str(payload, "normalized_topic")
    title = require_str(payload, "title")
    statement = require_str(payload, "statement")
    if len(title) > MAX_TITLE_CHARS:
        raise ImportedPlanParseError("Plan title is too long.")

    if not supported:
        if topic != "unsupported":
            raise ImportedPlanParseError(
                "Unsupported plans must use topic unsupported."
            )
        if payload["unsupported_reason"] != UNSUPPORTED_REASON:
            raise ImportedPlanParseError(
                "Invalid unsupported reason."
            )
        if payload["final_answer"] is not None:
            raise ImportedPlanParseError(
                "Unsupported plans must not include a final answer."
            )
        if payload["steps"] != []:
            raise ImportedPlanParseError(
                "Unsupported plans must not include steps."
            )
        return StructuredSolutionPlan(
            supported=False,
            normalized_topic="unsupported",
            title=title,
            statement=statement,
            final_answer=None,
            steps=(),
            unsupported_reason=UNSUPPORTED_REASON,
        )

    if topic not in SUPPORTED_TOPICS:
        raise ImportedPlanParseError(
            "Unsupported normalized topic."
        )
    if payload["unsupported_reason"] is not None:
        raise ImportedPlanParseError(
            "Supported plans must not include an unsupported reason."
        )
    if not statement:
        raise ImportedPlanParseError(
            "Supported plans must include a statement."
        )
    if not title:
        raise ImportedPlanParseError(
            "Supported plans must include a title."
        )

    final_answer = require_int(payload["final_answer"])
    steps = parse_steps(payload["steps"])
    if not steps:
        raise ImportedPlanParseError(
            "Supported plans must include steps."
        )
    if steps[-1].expected_answer != final_answer:
        raise ImportedPlanParseError(
            "Last step must match the final answer."
        )
    return StructuredSolutionPlan(
        supported=True,
        normalized_topic=topic,
        title=title,
        statement=statement,
        final_answer=final_answer,
        steps=tuple(steps),
        unsupported_reason=None,
    )


def parse_steps(value: object) -> list[PlannedStep]:
    if not isinstance(value, list):
        raise ImportedPlanParseError("Invalid steps.")
    if len(value) > MAX_STEPS:
        raise ImportedPlanParseError("Too many steps.")
    steps: list[PlannedStep] = []
    for item in value:
        if not isinstance(item, dict):
            raise ImportedPlanParseError("Invalid steps.")
        extra = set(item) - STEP_KEYS - OPTIONAL_STEP_KEYS
        missing = STEP_KEYS - set(item)
        if extra or missing:
            raise ImportedPlanParseError(
                "Step has unexpected keys."
            )
        instruction = require_plain_str(item, "instruction")
        if not instruction or len(instruction) > MAX_TEXT_CHARS:
            raise ImportedPlanParseError("Invalid step instruction.")
        if "expected_answer" not in item:
            raise ImportedPlanParseError("Missing expected answer.")
        hints = parse_hints(item["hints"])
        steps.append(
            PlannedStep(
                instruction=instruction,
                expected_answer=require_int(
                    item["expected_answer"]
                ),
                hints=tuple(hints),
                result_latex=parse_result_latex(
                    item.get("result_latex")
                ),
            )
        )
    return steps


def parse_result_latex(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or isinstance(value, bool):
        raise ImportedPlanParseError("Invalid result_latex.")
    text = " ".join(value.split())
    if not text:
        return None
    if len(text) > MAX_RESULT_LATEX_CHARS:
        raise ImportedPlanParseError("Invalid result_latex.")
    return text


def parse_hints(value: object) -> list[str]:
    if not isinstance(value, list):
        raise ImportedPlanParseError("Invalid hints.")
    hints: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ImportedPlanParseError("Invalid hints.")
        text = item.strip()
        if not text or len(text) > MAX_TEXT_CHARS:
            raise ImportedPlanParseError("Invalid hints.")
        hints.append(text)
    return hints


def load_strict_json_object(raw: str) -> dict:
    if not isinstance(raw, str):
        raise ImportedPlanParseError("Solution plan is not text.")
    text = raw.strip()
    if not text:
        raise ImportedPlanParseError("Solution plan is empty.")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise ImportedPlanParseError(
            "Solution plan is not valid JSON."
        ) from error
    if not isinstance(payload, dict):
        raise ImportedPlanParseError(
            "Solution plan is not an object."
        )
    return payload


def require_str(payload: dict, key: str) -> str:
    value = payload[key]
    if not isinstance(value, str):
        raise ImportedPlanParseError(f"Invalid {key}.")
    return value.strip()


def require_plain_str(payload: dict, key: str) -> str:
    value = payload[key]
    if not isinstance(value, str):
        raise ImportedPlanParseError(f"Invalid {key}.")
    return value.strip()


def require_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ImportedPlanParseError("Expected an integer value.")
    if abs(value) > MAX_ANSWER_ABS:
        raise ImportedPlanParseError("Integer value is out of range.")
    return value
