import json

from src.core.vision.contracts import (
    Ambiguity,
    DiagramFact,
    ExtractedProblem,
)
from src.core.vision.extractor import (
    VisionResponseParseError,
)
from src.core.vision.prompt import EXTRACTION_SCHEMA_ID


REQUIRED_KEYS = frozenset(
    {
        "schema",
        "transcription",
        "language",
        "problem_type_hint",
        "topic_hint",
        "latex_expressions",
        "diagram_present",
        "diagram_type",
        "diagram_facts",
        "ambiguities",
        "warnings",
        "multiple_problems_detected",
        "confidence",
    }
)
ALLOWED_LANGUAGES = frozenset(
    {"en", "bg", "unknown"}
)
ALLOWED_CONFIDENCE = frozenset(
    {"low", "medium", "high"}
)
DIAGRAM_FACT_KEYS = frozenset(
    {"kind", "label", "value", "unit"}
)
AMBIGUITY_KEYS = frozenset(
    {"observation", "span", "candidates"}
)


def parse_extracted_problem(
    raw: str,
) -> ExtractedProblem:
    payload = load_strict_json_object(raw)
    validate_exact_keys(payload)
    schema = payload["schema"]
    if schema is None:
        raise VisionResponseParseError(
            "Missing extraction schema."
        )
    if not isinstance(schema, str):
        raise VisionResponseParseError(
            "Invalid extraction schema."
        )
    if schema != EXTRACTION_SCHEMA_ID:
        raise VisionResponseParseError(
            "Unknown extraction schema."
        )

    transcription = require_str(
        payload,
        "transcription",
    )
    language = require_str(payload, "language")
    if language not in ALLOWED_LANGUAGES:
        raise VisionResponseParseError(
            "Invalid extraction language."
        )

    problem_type_hint = optional_str(
        payload,
        "problem_type_hint",
    )
    topic_hint = optional_str(payload, "topic_hint")
    latex_expressions = require_str_list(
        payload,
        "latex_expressions",
    )
    diagram_present = require_bool(
        payload,
        "diagram_present",
    )
    diagram_type = optional_str(
        payload,
        "diagram_type",
    )
    diagram_facts = parse_diagram_facts(
        payload["diagram_facts"]
    )
    ambiguities = parse_ambiguities(
        payload["ambiguities"]
    )
    warnings = require_str_list(
        payload,
        "warnings",
    )
    multiple_problems_detected = require_bool(
        payload,
        "multiple_problems_detected",
    )
    confidence = optional_confidence(
        payload["confidence"]
    )

    return ExtractedProblem(
        transcription=transcription,
        language=language,
        problem_type_hint=problem_type_hint,
        topic_hint=topic_hint,
        latex_expressions=tuple(latex_expressions),
        diagram_present=diagram_present,
        diagram_type=diagram_type,
        diagram_facts=tuple(diagram_facts),
        ambiguities=tuple(ambiguities),
        warnings=tuple(warnings),
        multiple_problems_detected=(
            multiple_problems_detected
        ),
        confidence=confidence,
    )


def load_strict_json_object(raw: str) -> dict:
    if not isinstance(raw, str):
        raise VisionResponseParseError(
            "Extraction response is not text."
        )
    text = raw.strip()
    if not text:
        raise VisionResponseParseError(
            "Extraction response is empty."
        )
    if text.startswith("```"):
        raise VisionResponseParseError(
            "Extraction response used Markdown fences."
        )
    if not text.startswith("{") or not text.endswith(
        "}"
    ):
        raise VisionResponseParseError(
            "Extraction response is not strict JSON."
        )
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise VisionResponseParseError(
            "Extraction response is not valid JSON."
        ) from error
    if not isinstance(payload, dict):
        raise VisionResponseParseError(
            "Extraction response is not a JSON object."
        )
    return payload


def validate_exact_keys(payload: dict) -> None:
    keys = set(payload)
    missing = REQUIRED_KEYS - keys
    extra = keys - REQUIRED_KEYS
    if "schema" not in keys:
        raise VisionResponseParseError(
            "Missing extraction schema."
        )
    if missing:
        raise VisionResponseParseError(
            "Extraction response is missing required fields."
        )
    if extra:
        unexpected = sorted(extra)[0]
        raise VisionResponseParseError(
            f"Unexpected field: {unexpected}"
        )


def require_str(payload: dict, key: str) -> str:
    value = payload[key]
    if not isinstance(value, str):
        raise VisionResponseParseError(
            f"Invalid {key}."
        )
    return value


def optional_str(
    payload: dict,
    key: str,
) -> str | None:
    value = payload[key]
    if value is None:
        return None
    if not isinstance(value, str):
        raise VisionResponseParseError(
            f"Invalid {key}."
        )
    return value


def require_bool(payload: dict, key: str) -> bool:
    value = payload[key]
    if not isinstance(value, bool):
        raise VisionResponseParseError(
            f"Invalid {key}."
        )
    return value


def require_str_list(
    payload: dict,
    key: str,
) -> list[str]:
    value = payload[key]
    if not isinstance(value, list):
        raise VisionResponseParseError(
            f"Invalid {key}."
        )
    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise VisionResponseParseError(
                f"Invalid {key}."
            )
        items.append(item)
    return items


def optional_confidence(
    value: object,
) -> str | None:
    if value is None:
        return None
    if (
        not isinstance(value, str)
        or value not in ALLOWED_CONFIDENCE
    ):
        raise VisionResponseParseError(
            "Invalid extraction confidence."
        )
    return value


def parse_diagram_facts(
    value: object,
) -> list[DiagramFact]:
    if not isinstance(value, list):
        raise VisionResponseParseError(
            "Invalid diagram_facts."
        )
    facts: list[DiagramFact] = []
    for item in value:
        if not isinstance(item, dict):
            raise VisionResponseParseError(
                "Invalid diagram_facts."
            )
        extra = set(item) - DIAGRAM_FACT_KEYS
        if extra or "kind" not in item:
            raise VisionResponseParseError(
                "Invalid diagram_facts."
            )
        kind = item["kind"]
        if not isinstance(kind, str) or not kind:
            raise VisionResponseParseError(
                "Invalid diagram_facts."
            )
        facts.append(
            DiagramFact(
                kind=kind,
                label=optional_nested_str(
                    item,
                    "label",
                ),
                value=optional_nested_str(
                    item,
                    "value",
                ),
                unit=optional_nested_str(
                    item,
                    "unit",
                ),
            )
        )
    return facts


def parse_ambiguities(
    value: object,
) -> list[Ambiguity]:
    if not isinstance(value, list):
        raise VisionResponseParseError(
            "Invalid ambiguities."
        )
    items: list[Ambiguity] = []
    for item in value:
        if not isinstance(item, dict):
            raise VisionResponseParseError(
                "Invalid ambiguities."
            )
        extra = set(item) - AMBIGUITY_KEYS
        if extra or "observation" not in item:
            raise VisionResponseParseError(
                "Invalid ambiguities."
            )
        observation = item["observation"]
        if not isinstance(observation, str):
            raise VisionResponseParseError(
                "Invalid ambiguities."
            )
        candidates_value = item.get(
            "candidates",
            [],
        )
        if not isinstance(candidates_value, list):
            raise VisionResponseParseError(
                "Invalid ambiguities."
            )
        candidates: list[str] = []
        for candidate in candidates_value:
            if not isinstance(candidate, str):
                raise VisionResponseParseError(
                    "Invalid ambiguities."
                )
            candidates.append(candidate)
        items.append(
            Ambiguity(
                observation=observation,
                span=optional_nested_str(
                    item,
                    "span",
                ),
                candidates=tuple(candidates),
            )
        )
    return items


def optional_nested_str(
    payload: dict,
    key: str,
) -> str | None:
    if key not in payload:
        return None
    value = payload[key]
    if value is None:
        return None
    if not isinstance(value, str):
        raise VisionResponseParseError(
            "Invalid nested string field."
        )
    return value
