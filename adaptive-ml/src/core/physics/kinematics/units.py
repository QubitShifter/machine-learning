from __future__ import annotations

import re


CANONICAL_UNITS = {
    "m": "m",
    "s": "s",
    "m/s": "m/s",
    "m/s^2": "m/s^2",
}

UNIT_ALIASES = {
    "m": "m",
    "s": "s",
    "m/s": "m/s",
    "m s^-1": "m/s",
    "m*s^-1": "m/s",
    "ms^-1": "m/s",
    "m s-1": "m/s",
    "m*s-1": "m/s",
    "m/s^2": "m/s^2",
    "m/s²": "m/s^2",
    "m/s^{2}": "m/s^2",
    "m s^-2": "m/s^2",
    "m*s^-2": "m/s^2",
    "ms^-2": "m/s^2",
    "m s-2": "m/s^2",
    "m*s-2": "m/s^2",
}

DIMENSION_FOR_UNIT = {
    "m": "length",
    "s": "time",
    "m/s": "velocity",
    "m/s^2": "acceleration",
}

QUANTITY_UNITS = {
    "v0": "m/s",
    "v": "m/s",
    "a": "m/s^2",
    "t": "s",
    "dx": "m",
}

_UNIT_BOUNDARIES = set(" ,.;:)&")
_ALIASES_LONGEST_FIRST = tuple(
    sorted(UNIT_ALIASES, key=len, reverse=True)
)


def normalize_unit(unit: str | None) -> str | None:
    if unit is None:
        return None

    cleaned = " ".join(unit.strip().split())
    cleaned = cleaned.replace("²", "^2")
    cleaned = cleaned.replace("^{2}", "^2")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return UNIT_ALIASES.get(cleaned)


def unit_dimension(unit: str | None) -> str | None:
    canonical = normalize_unit(unit)
    if canonical is None:
        return None
    return DIMENSION_FOR_UNIT[canonical]


def match_leading_unit(text: str) -> str | None:
    cleaned = text.lstrip().replace("²", "^2")
    cleaned = cleaned.replace("^{2}", "^2")

    for alias in _ALIASES_LONGEST_FIRST:
        alias_form = alias.replace("²", "^2").replace(
            "^{2}",
            "^2",
        )
        if not cleaned.startswith(alias_form):
            continue

        rest = cleaned[len(alias_form):]
        if rest and rest[0] not in _UNIT_BOUNDARIES:
            continue

        return alias

    return None


def parse_quantity_answer(
    answer: str,
) -> tuple[float | None, str | None, str]:
    raw = " ".join(answer.strip().split())
    if not raw:
        return None, None, ""

    match = re.match(
        r"^([+-]?(?:\d+(?:\.\d+)?|\.\d+))\s*(.*)$",
        raw,
    )
    if match is None:
        return None, None, raw

    value = float(match.group(1))
    unit_text = match.group(2).strip()
    return value, unit_text or None, raw
