"""Markdown-first development change-history maintenance."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "docs" / "change_history.md"
CHANGES_DIR = ROOT / "docs" / "changes"
REGISTRY = ROOT / "docs" / "feature_registry.md"
BUGS_DIR = ROOT / "docs" / "bugs"

CHANGE_TYPES = {
    "feature",
    "enhancement",
    "bug fix",
    "refactor",
    "documentation",
    "configuration",
    "data migration",
}
STATUSES = {
    "implemented",
    "tested",
    "verified",
    "pending_verification",
    "retrospective",
}
ISO8601 = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2}(?::\d{2})?)$"
)
UNKNOWN = {"unknown", "n/a", ""}
ID_PATTERN = re.compile(r"^CHG-\d{4}$")
REQUIRED_SECTIONS = [
    "Reason",
    "Previous behavior",
    "New behavior",
    "Modified files",
    "Scientific impact",
    "Backward-compatibility impact",
    "Tests",
    "Related features",
    "Related bugs",
    "Git reference",
    "Validation status",
]
FRONT_MATTER_FIELDS = [
    "change_id",
    "title",
    "timestamp",
    "documented_at",
    "phase",
    "change_type",
    "status",
    "retrospective",
    "related_features",
    "related_bugs",
    "git_reference",
    "scientific_impact",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_front_matter(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError(f"{path.name} is missing YAML front matter.")
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not match:
        raise ValueError(f"{path.name} has invalid YAML front matter.")
    payload = yaml.safe_load(match.group(1)) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} front matter must be a mapping.")
    return payload, match.group(2)


def change_files(root: Path | None = None) -> list[Path]:
    directory = (root or ROOT) / "docs" / "changes"
    if not directory.is_dir():
        return []
    return sorted(
        path for path in directory.glob("CHG-*.md") if path.name != "README.md"
    )


def load_changes(root: Path | None = None) -> list[dict[str, Any]]:
    records = []
    for path in change_files(root):
        payload, body = parse_front_matter(path)
        payload["_path"] = path
        payload["_body"] = body
        records.append(payload)
    return records


def next_change_id(records: list[dict[str, Any]] | None = None) -> str:
    records = records if records is not None else load_changes()
    numbers = []
    for item in records:
        match = re.fullmatch(r"CHG-(\d{4})", str(item.get("change_id") or ""))
        if match:
            numbers.append(int(match.group(1)))
    return f"CHG-{(max(numbers) + 1) if numbers else 1:04d}"


def _as_list(value: Any) -> list[str]:
    if value in (None, "", "none", []):
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value]


def _as_time_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        stamp = value
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        return stamp.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    text = str(value).strip()
    return text


def _valid_time(value: Any, *, allow_unknown: bool = True) -> bool:
    if value is None:
        return True
    if isinstance(value, datetime):
        return True
    text = str(value).strip()
    if allow_unknown and text.lower() in UNKNOWN:
        return True
    return bool(ISO8601.fullmatch(text))


def _parse_time(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        stamp = value
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        return stamp.astimezone(timezone.utc)
    text = str(value).strip() if value is not None else ""
    if text.lower() in UNKNOWN or not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        stamp = datetime.fromisoformat(text)
    except ValueError:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp.astimezone(timezone.utc)


def _feature_ids(root: Path) -> set[str]:
    registry = root / "docs" / "feature_registry.md"
    if not registry.is_file():
        return set()
    return set(re.findall(r"`([a-z][a-z0-9_.]+)`", registry.read_text(encoding="utf-8")))


def _bug_ids(root: Path) -> set[str]:
    directory = root / "docs" / "bugs"
    if not directory.is_dir():
        return set()
    return {path.stem for path in directory.glob("BUG-*.md") if path.name != "README.md"}


def validate(root: Path | None = None) -> list[str]:
    base = root or ROOT
    errors: list[str] = []
    history = base / "docs" / "change_history.md"
    if not history.is_file():
        errors.append("docs/change_history.md is missing.")
    history_text = history.read_text(encoding="utf-8") if history.is_file() else ""
    known_features = _feature_ids(base)
    known_bugs = _bug_ids(base)
    ids: list[str] = []
    documented_times: list[tuple[str, datetime]] = []
    for path in change_files(base):
        try:
            payload, body = parse_front_matter(path)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        change_id = str(payload.get("change_id") or "")
        if change_id != path.stem:
            errors.append(f"{path.name}: change_id `{change_id}` does not match filename.")
        if not ID_PATTERN.fullmatch(change_id):
            errors.append(f"{path.name}: invalid change_id.")
        ids.append(change_id)
        for field in FRONT_MATTER_FIELDS:
            if field not in payload:
                errors.append(f"{path.name}: missing front-matter field `{field}`.")
        change_type = str(payload.get("change_type") or "").lower()
        if change_type and change_type not in CHANGE_TYPES:
            errors.append(f"{path.name}: invalid change_type `{change_type}`.")
        status = str(payload.get("status") or "").lower()
        if status and status not in STATUSES:
            errors.append(f"{path.name}: invalid status `{status}`.")
        retrospective = bool(payload.get("retrospective"))
        if not _valid_time(payload.get("timestamp"), allow_unknown=True):
            errors.append(f"{path.name}: timestamp is not ISO 8601 UTC or unknown.")
        if not _valid_time(payload.get("documented_at"), allow_unknown=False):
            errors.append(f"{path.name}: documented_at must be an actual ISO 8601 UTC timestamp.")
        if retrospective and str(payload.get("timestamp") or "").lower() not in UNKNOWN:
            # Retrospective may still have a known time; unknown is the expected default.
            pass
        if not retrospective and str(payload.get("timestamp") or "").lower() in UNKNOWN:
            errors.append(f"{path.name}: non-retrospective changes need an actual timestamp.")
        git_reference = str(payload.get("git_reference") or "").strip()
        if not git_reference:
            errors.append(f"{path.name}: git_reference is required (`uncommitted` or a commit hash).")
        headings = [
            re.sub(r"^\d+\.\s*", "", line[3:].strip())
            for line in body.splitlines()
            if line.startswith("## ")
        ]
        for section in REQUIRED_SECTIONS:
            if section not in headings:
                errors.append(f"{path.name}: missing section `{section}`.")
        for feature_id in _as_list(payload.get("related_features")):
            if known_features and feature_id not in known_features:
                errors.append(
                    f"{path.name}: related feature `{feature_id}` is not in the registry."
                )
        for bug_id in _as_list(payload.get("related_bugs")):
            if known_bugs and bug_id not in known_bugs:
                errors.append(f"{path.name}: related bug `{bug_id}` does not exist.")
        for item in _as_list(payload.get("modified_files")):
            if item.endswith("/"):
                continue
            if not (base / item).exists():
                errors.append(f"{path.name}: modified file does not exist: {item}")
        if history_text and change_id not in history_text:
            errors.append(f"{path.name}: `{change_id}` is not listed in change_history.md.")
        documented = _parse_time(payload.get("documented_at"))
        if documented:
            documented_times.append((change_id, documented))
    duplicates = {item for item in ids if ids.count(item) > 1}
    for item in sorted(duplicates):
        errors.append(f"Duplicate change_id `{item}`.")
    ordered = sorted(documented_times, key=lambda pair: pair[0])
    previous: datetime | None = None
    previous_id = ""
    for change_id, stamp in ordered:
        if previous and stamp < previous:
            errors.append(
                f"{change_id}: documented_at precedes {previous_id}; "
                "append later records instead of rewriting earlier timestamps."
            )
        previous = stamp
        previous_id = change_id
    return errors


def rebuild_table(root: Path | None = None) -> None:
    base = root or ROOT
    history = base / "docs" / "change_history.md"
    rows = [
        "| Change ID | Timestamp | Phase | Type | Status | Description | Git | Details |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for item in load_changes(base):
        change_id = item.get("change_id")
        rel = f"changes/{change_id}.md"
        rows.append(
            "| `{id}` | {ts} | {phase} | {kind} | {status} | {title} | `{git}` | [{id}]({rel}) |".format(
                id=change_id,
                ts=item.get("timestamp") or "unknown",
                phase=item.get("phase") or "—",
                kind=item.get("change_type") or "—",
                status=item.get("status") or "—",
                title=(item.get("title") or "").replace("|", "/"),
                git=item.get("git_reference") or "uncommitted",
                rel=rel,
            )
        )
    table = "\n".join(rows)
    if history.is_file():
        text = history.read_text(encoding="utf-8")
        updated, count = re.subn(
            r"<!-- CHANGE_TABLE_START -->.*?<!-- CHANGE_TABLE_END -->",
            f"<!-- CHANGE_TABLE_START -->\n{table}\n<!-- CHANGE_TABLE_END -->",
            text,
            flags=re.S,
        )
        if count:
            history.write_text(updated, encoding="utf-8")
            return
    history.parent.mkdir(parents=True, exist_ok=True)
    history.write_text(
        "# Development Change History\n\n<!-- CHANGE_TABLE_START -->\n"
        + table
        + "\n<!-- CHANGE_TABLE_END -->\n",
        encoding="utf-8",
    )


def list_changes(root: Path | None = None) -> list[dict[str, Any]]:
    return [
        {
            "change_id": item.get("change_id"),
            "title": item.get("title"),
            "status": item.get("status"),
            "change_type": item.get("change_type"),
            "timestamp": item.get("timestamp"),
        }
        for item in load_changes(root)
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="List change records")
    sub.add_parser("validate", help="Validate change records and history table")
    sub.add_parser("refresh", help="Rebuild the change-history index table")
    args = parser.parse_args(argv)
    if args.command == "list":
        for item in list_changes():
            print(f"{item['change_id']}\t{item['status']}\t{item['title']}")
        return 0
    if args.command == "refresh":
        rebuild_table()
        print("Change history table refreshed.")
        return 0
    errors = validate()
    if errors:
        for item in errors:
            print(item, file=sys.stderr)
        print(f"Change history validation failed ({len(errors)} issue(s)).", file=sys.stderr)
        return 1
    print(f"Change history OK ({len(change_files())} records).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
