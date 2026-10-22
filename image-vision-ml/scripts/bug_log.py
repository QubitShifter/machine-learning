"""Markdown-first bug and fix history maintenance."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "docs" / "bug_fix_history.md"
BUGS_DIR = ROOT / "docs" / "bugs"
REGISTRY = ROOT / "docs" / "feature_registry.md"

STATUSES = {
    "open",
    "investigating",
    "fixed",
    "verified",
    "deferred",
    "not_a_bug",
    "reopened",
}
CATEGORIES = {
    "code",
    "data",
    "science",
    "integration",
    "api",
    "documentation",
    "environment",
}
SEVERITIES = {"critical", "high", "medium", "low", "informational"}
ISO8601 = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2}(?::\d{2})?)$"
)
DATE_ONLY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
UNKNOWN = {"unknown", "n/a", ""}
ID_PATTERN = re.compile(r"^BUG-\d{4}$")


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


def bug_files(root: Path | None = None) -> list[Path]:
    directory = (root or ROOT) / "docs" / "bugs"
    if not directory.is_dir():
        return []
    return sorted(
        path for path in directory.glob("BUG-*.md") if path.name != "README.md"
    )


def load_bugs(root: Path | None = None) -> list[dict[str, Any]]:
    records = []
    for path in bug_files(root):
        payload, body = parse_front_matter(path)
        payload["_path"] = path
        payload["_body"] = body
        records.append(payload)
    return records


def next_bug_id(records: list[dict[str, Any]] | None = None) -> str:
    records = records if records is not None else load_bugs()
    numbers = []
    for item in records:
        match = re.fullmatch(r"BUG-(\d{4})", str(item.get("bug_id") or ""))
        if match:
            numbers.append(int(match.group(1)))
    return f"BUG-{(max(numbers) + 1) if numbers else 1:04d}"


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


def _valid_time(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, datetime):
        return True
    text = str(value).strip()
    if text.lower() in UNKNOWN:
        return True
    return bool(ISO8601.fullmatch(text) or DATE_ONLY.fullmatch(text))


def _parse_time(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        stamp = value
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        return stamp.astimezone(timezone.utc)
    text = str(value or "").strip()
    if not text or text.lower() in UNKNOWN:
        return None
    if DATE_ONLY.fullmatch(text):
        return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)
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


def validate(root: Path | None = None) -> list[str]:
    base = root or ROOT
    errors: list[str] = []
    history = base / "docs" / "bug_fix_history.md"
    if not history.is_file():
        errors.append("docs/bug_fix_history.md is missing.")
    records = []
    ids: list[str] = []
    known_features = _feature_ids(base)
    for path in bug_files(base):
        try:
            payload, body = parse_front_matter(path)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        bug_id = str(payload.get("bug_id") or "")
        expected = path.stem
        if bug_id != expected:
            errors.append(f"{path.name}: bug_id `{bug_id}` does not match filename.")
        if not ID_PATTERN.fullmatch(bug_id):
            errors.append(f"{path.name}: invalid bug_id.")
        ids.append(bug_id)
        status = str(payload.get("status") or "").lower()
        if status not in STATUSES:
            errors.append(f"{path.name}: invalid status `{status}`.")
        category = str(payload.get("category") or "").lower()
        if category not in CATEGORIES:
            errors.append(f"{path.name}: invalid category `{category}`.")
        severity = str(payload.get("severity") or "").lower()
        if severity not in SEVERITIES:
            errors.append(f"{path.name}: invalid severity `{severity}`.")
        for field in ("title", "detected_at", "reporter"):
            if not payload.get(field) and payload.get(field) != "unknown":
                errors.append(f"{path.name}: missing `{field}`.")
        for field in ("detected_at", "fixed_at", "verified_at", "documented_at"):
            if field in payload and not _valid_time(payload.get(field)):
                errors.append(f"{path.name}: `{field}` is not ISO 8601 UTC or unknown.")
        detected = _parse_time(payload.get("detected_at"))
        fixed = _parse_time(payload.get("fixed_at"))
        verified = _parse_time(payload.get("verified_at"))
        if detected and fixed and fixed < detected:
            errors.append(f"{path.name}: fixed_at precedes detected_at.")
        if fixed and verified and verified < fixed:
            errors.append(f"{path.name}: verified_at precedes fixed_at.")
        if status in {"fixed", "verified"} and not payload.get("fixed_at"):
            errors.append(f"{path.name}: {status} record is missing fixed_at.")
        if status == "verified" and not payload.get("verified_at"):
            errors.append(f"{path.name}: verified record is missing verified_at.")
        if status == "verified" and payload.get("fixed_at") and payload.get("verified_at"):
            if str(payload.get("fixed_at")) == str(payload.get("verified_at")):
                errors.append(
                    f"{path.name}: fix and verification timestamps must be distinct events."
                )
        for feature_id in payload.get("affected_features") or []:
            if known_features and feature_id not in known_features:
                errors.append(
                    f"{path.name}: affected feature `{feature_id}` is not in the registry."
                )
        for item in payload.get("source_references") or []:
            if not (base / str(item)).exists():
                errors.append(f"{path.name}: source reference missing: {item}")
        for item in payload.get("test_references") or []:
            if not (base / str(item)).exists():
                errors.append(f"{path.name}: test reference missing: {item}")
        for heading in (
            "Identification",
            "Description",
            "Environment",
            "Reproduction",
            "Evidence",
            "Root-cause analysis",
            "Resolution",
            "Mathematical or scientific impact",
            "Validation",
            "Timeline",
            "Related references",
        ):
            if f"## {heading}" not in body:
                errors.append(f"{path.name}: missing section `{heading}`.")
        records.append(payload)
        if history.is_file() and bug_id not in history.read_text(encoding="utf-8"):
            errors.append(f"{path.name}: `{bug_id}` is not listed in bug_fix_history.md.")
    duplicates = {item for item in ids if ids.count(item) > 1}
    for item in sorted(duplicates):
        errors.append(f"Duplicate bug_id `{item}`.")
    return errors


def _dump_front_matter(payload: dict[str, Any]) -> str:
    clean = {
        key: value
        for key, value in payload.items()
        if not str(key).startswith("_")
    }
    for key in ("detected_at", "fixed_at", "verified_at", "documented_at"):
        if key in clean:
            text = _as_time_text(clean[key])
            if text and str(text).lower() not in UNKNOWN:
                parsed = _parse_time(clean[key])
                clean[key] = parsed.strftime("%Y-%m-%dT%H:%M:%SZ") if parsed else text
            elif text is not None and str(text).lower() in UNKNOWN:
                clean[key] = "unknown"
    return yaml.safe_dump(clean, sort_keys=False, allow_unicode=False).strip()


def add_bug(
    *,
    title: str,
    category: str,
    severity: str,
    status: str = "open",
    affected_features: list[str] | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    base = root or ROOT
    records = load_bugs(base)
    bug_id = next_bug_id(records)
    if any(item.get("bug_id") == bug_id for item in records):
        raise ValueError(f"Duplicate bug_id `{bug_id}`.")
    now = utc_now()
    payload = {
        "bug_id": bug_id,
        "title": title,
        "category": category.lower(),
        "severity": severity.lower(),
        "status": status.lower(),
        "detected_at": now,
        "fixed_at": None,
        "verified_at": None,
        "documented_at": now,
        "retrospective": False,
        "reporter": "cursor-agent",
        "affected_features": affected_features or [],
        "source_references": [],
        "test_references": [],
    }
    body = _template_body(bug_id, title, now)
    path = base / "docs" / "bugs" / f"{bug_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{_dump_front_matter(payload)}\n---\n{body}", encoding="utf-8")
    refresh_history(base)
    return payload


def update_bug(
    bug_id: str,
    *,
    status: str | None = None,
    note: str | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    base = root or ROOT
    path = base / "docs" / "bugs" / f"{bug_id}.md"
    if not path.is_file():
        raise FileNotFoundError(f"{bug_id} does not exist.")
    payload, body = parse_front_matter(path)
    previous_status = payload.get("status")
    now = utc_now()
    if status:
        payload["status"] = status.lower()
        if payload["status"] in {"fixed", "verified"} and not payload.get("fixed_at"):
            payload["fixed_at"] = now
        if payload["status"] == "verified":
            if payload.get("fixed_at") == now:
                # A separate verification instant is required; wait 1s is not
                # reliable. Require an existing fixed_at distinct from now.
                raise ValueError(
                    "Mark FIXED before VERIFIED; verification is a later event."
                )
            if not payload.get("verified_at"):
                payload["verified_at"] = now
        if payload["status"] == "reopened":
            payload["verified_at"] = None
    event = f"- `{now}` —"
    if status:
        event += f" status {previous_status} → {payload['status']}."
    if note:
        event += f" {note}"
    if "## Timeline" not in body:
        body += "\n## Timeline\n\n"
    body = body.rstrip() + f"\n{event}\n"
    path.write_text(f"---\n{_dump_front_matter(payload)}\n---\n{body}\n", encoding="utf-8")
    refresh_history(base)
    return payload


def _template_body(bug_id: str, title: str, now: str) -> str:
    return f"""
## Identification

- Bug ID: `{bug_id}`
- Title: {title}
- Detected: `{now}`

## Description

To be completed.

## Environment

See repository `pyproject.toml`. No credentials are stored here.

## Reproduction

To be completed.

## Evidence

To be completed.

## Root-cause analysis

Root cause: under investigation.

## Resolution

Not yet resolved.

## Mathematical or scientific impact

Under investigation.

## Validation

Not yet validated.

## Timeline

- `{now}` — Record created.

## Related references

None yet.
"""


def refresh_history(root: Path | None = None) -> None:
    base = root or ROOT
    history = base / "docs" / "bug_fix_history.md"
    records = load_bugs(base)
    records.sort(key=lambda item: str(item.get("bug_id") or ""))
    rows = [
        "| Bug ID | Title | Category | Severity | Status | Detected at | Fixed at | Verified at | Affected feature | Root cause | Resolution | Details |"
        ,
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for item in records:
        features = ", ".join(f"`{name}`" for name in (item.get("affected_features") or [])[:3]) or "—"
        rel = f"docs/bugs/{item.get('bug_id')}.md"
        rows.append(
            "| `{id}` | {title} | {category} | {severity} | {status} | {detected} | {fixed} | {verified} | {features} | {cause} | {resolution} | [{id}]({rel}) |".format(
                id=item.get("bug_id"),
                title=item.get("title") or "",
                category=item.get("category") or "",
                severity=item.get("severity") or "",
                status=item.get("status") or "",
                detected=item.get("detected_at") or "unknown",
                fixed=item.get("fixed_at") or "—",
                verified=item.get("verified_at") or "—",
                features=features,
                cause=(item.get("root_cause") or "unknown").replace("|", "/"),
                resolution=(item.get("resolution") or "—").replace("|", "/"),
                rel=rel.replace("docs/", ""),
            )
        )
    table = "\n".join(rows)
    if history.is_file():
        text = history.read_text(encoding="utf-8")
        updated, count = re.subn(
            r"<!-- BUG_TABLE_START -->.*?<!-- BUG_TABLE_END -->",
            f"<!-- BUG_TABLE_START -->\n{table}\n<!-- BUG_TABLE_END -->",
            text,
            flags=re.S,
        )
        if count:
            history.write_text(updated, encoding="utf-8")
            return
    history.parent.mkdir(parents=True, exist_ok=True)
    history.write_text(
        "# Bug and Fix History\n\n<!-- BUG_TABLE_START -->\n"
        + table
        + "\n<!-- BUG_TABLE_END -->\n",
        encoding="utf-8",
    )


def list_bugs(root: Path | None = None) -> list[dict[str, Any]]:
    records = load_bugs(root)
    return [
        {
            "bug_id": item.get("bug_id"),
            "title": item.get("title"),
            "status": item.get("status"),
            "category": item.get("category"),
            "severity": item.get("severity"),
        }
        for item in records
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    add_p = sub.add_parser("add", help="Create a new bug record")
    add_p.add_argument("--title", required=True)
    add_p.add_argument("--category", required=True)
    add_p.add_argument("--severity", required=True)
    add_p.add_argument("--status", default="open")
    add_p.add_argument("--feature", action="append", default=[])
    upd = sub.add_parser("update", help="Append a timestamped status change")
    upd.add_argument("bug_id")
    upd.add_argument("--status")
    upd.add_argument("--note")
    sub.add_parser("list", help="List bug records")
    sub.add_parser("validate", help="Validate bug records and history table")
    args = parser.parse_args(argv)
    if args.command == "add":
        payload = add_bug(
            title=args.title,
            category=args.category,
            severity=args.severity,
            status=args.status,
            affected_features=args.feature,
        )
        print(payload["bug_id"])
        return 0
    if args.command == "update":
        payload = update_bug(args.bug_id, status=args.status, note=args.note)
        print(payload["bug_id"], payload["status"])
        return 0
    if args.command == "list":
        for item in list_bugs():
            print(f"{item['bug_id']}\t{item['status']}\t{item['title']}")
        return 0
    errors = validate()
    if errors:
        for item in errors:
            print(item, file=sys.stderr)
        print(f"Bug history validation failed ({len(errors)} issue(s)).", file=sys.stderr)
        return 1
    print(f"Bug history OK ({len(bug_files())} records).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
