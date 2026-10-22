"""Validate the feature registry and per-feature Markdown documentation."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs" / "feature_registry.md"
FEATURES_DIR = ROOT / "docs" / "features"

ALLOWED_STATUSES = {"implemented", "planned", "partial", "deprecated"}
REQUIRED_SECTIONS = [
    "Feature ID and name",
    "Status and version",
    "Purpose",
    "Scientific background",
    "Mathematical formula or algorithm",
    "Explanation of every variable and unit",
    "Worked numerical example",
    "Source datasets and provenance",
    "Input requirements",
    "Processing steps",
    "Implementation paths and functions",
    "Configuration parameters",
    "Outputs and units",
    "Validation criteria",
    "Missing-value handling",
    "Temporal leakage considerations",
    "Tests and expected assertions",
    "Scientific limitations",
    "Related feature dependencies",
    "Related bug/fix IDs",
    "Last reviewed timestamp in UTC",
]
FRONT_MATTER_FIELDS = [
    "feature_id",
    "name",
    "category",
    "status",
    "mathematical_method",
    "input_datasets",
    "source_code",
    "configuration",
    "outputs",
    "tests",
    "last_verified",
]


def feature_files() -> list[Path]:
    if not FEATURES_DIR.is_dir():
        return []
    return sorted(
        path
        for path in FEATURES_DIR.rglob("*.md")
        if path.name != "README.md"
    )


def parse_front_matter(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError(f"{path.relative_to(ROOT)} is missing YAML front matter.")
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not match:
        raise ValueError(f"{path.relative_to(ROOT)} has invalid YAML front matter.")
    payload = yaml.safe_load(match.group(1)) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"{path.relative_to(ROOT)} front matter must be a mapping.")
    return payload, match.group(2)


def _as_list(value: Any) -> list[str]:
    if value in (None, "", "none", []):
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value]


def _headings(body: str) -> list[str]:
    headings = []
    for line in body.splitlines():
        if line.startswith("## "):
            headings.append(re.sub(r"^\d+\.\s*", "", line[3:].strip()))
    return headings


def _iso8601(value: str) -> bool:
    return bool(
        re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2}(?::\d{2})?)",
            value,
        )
    )


def validate_feature(
    path: Path,
    payload: dict[str, Any],
    body: str,
    *,
    root: Path | None = None,
) -> list[str]:
    errors: list[str] = []
    base = root or ROOT
    rel = str(path.relative_to(base))
    for field in FRONT_MATTER_FIELDS:
        if field not in payload or payload[field] in (None, ""):
            errors.append(f"{rel}: missing front-matter field `{field}`.")
    status = str(payload.get("status") or "")
    if status and status not in ALLOWED_STATUSES:
        errors.append(f"{rel}: invalid status `{status}`.")
    feature_id = str(payload.get("feature_id") or "")
    if feature_id and not re.fullmatch(r"[a-z][a-z0-9_.]+", feature_id):
        errors.append(f"{rel}: invalid feature_id `{feature_id}`.")
    verified = str(payload.get("last_verified") or "")
    if verified and not _iso8601(verified):
        errors.append(f"{rel}: last_verified is not ISO 8601 UTC.")

    headings = _headings(body)
    for section in REQUIRED_SECTIONS:
        if section not in headings:
            errors.append(f"{rel}: missing required section `{section}`.")

    if status == "implemented":
        code_paths = _as_list(payload.get("source_code"))
        if not code_paths:
            errors.append(f"{rel}: implemented feature has no source_code paths.")
        for item in code_paths:
            if not (base / item).exists():
                errors.append(f"{rel}: source_code path does not exist: {item}")
        for item in _as_list(payload.get("configuration")):
            if not (base / item).exists():
                errors.append(f"{rel}: configuration path does not exist: {item}")
        tests = _as_list(payload.get("tests"))
        if not tests:
            errors.append(f"{rel}: implemented feature has no tests.")
        for item in tests:
            if not (base / item).exists():
                errors.append(f"{rel}: test path does not exist: {item}")
    elif status == "planned":
        for item in _as_list(payload.get("source_code")):
            if (ROOT / item).exists():
                # Planned may still cite future paths; existing paths are allowed.
                continue
    for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", body):
        target = match.group(1)
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        resolved = (path.parent / target).resolve()
        try:
            resolved.relative_to(base.resolve())
        except ValueError:
            continue
        if not resolved.exists():
            errors.append(f"{rel}: broken relative link {target}")
    return errors


def registry_ids(text: str) -> list[str]:
    return re.findall(r"`([a-z][a-z0-9_.]+)`", text)


def validate(root: Path | None = None) -> list[str]:
    base = root or ROOT
    registry = base / "docs" / "feature_registry.md"
    features_dir = base / "docs" / "features"
    errors: list[str] = []
    if not registry.is_file():
        return [f"{registry.relative_to(base)} is missing."]
    files = sorted(
        path
        for path in features_dir.rglob("*.md")
        if path.name != "README.md"
    ) if features_dir.is_dir() else []
    if not files:
        errors.append("No feature Markdown files were found under docs/features/.")
    ids: list[str] = []
    registry_text = registry.read_text(encoding="utf-8")
    listed = set(registry_ids(registry_text))
    for path in files:
        try:
            payload, body = parse_front_matter(path)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        feature_id = str(payload.get("feature_id") or "")
        if feature_id:
            ids.append(feature_id)
            if feature_id not in listed:
                errors.append(
                    f"{path.relative_to(base)}: feature_id `{feature_id}` "
                    "is not listed in docs/feature_registry.md."
                )
        errors.extend(validate_feature(path, payload, body, root=base))
        rel = str(path.relative_to(base)).replace("\\", "/")
        short = str(path.relative_to(base / "docs")).replace("\\", "/")
        if rel not in registry_text and short not in registry_text:
            errors.append(
                f"{path.relative_to(base)} is not linked from docs/feature_registry.md."
            )
    duplicates = {item for item in ids if ids.count(item) > 1}
    for item in sorted(duplicates):
        errors.append(f"Duplicate feature_id `{item}`.")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    errors = validate()
    if errors:
        for item in errors:
            print(item, file=sys.stderr)
        print(f"Feature documentation validation failed ({len(errors)} issue(s)).", file=sys.stderr)
        return 1
    print(f"Feature documentation OK ({len(feature_files())} features).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
