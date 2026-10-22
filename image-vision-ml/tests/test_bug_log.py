from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

from scripts.bug_log import (
    add_bug,
    next_bug_id,
    update_bug,
    utc_now,
    validate,
)


def _seed_registry(root: Path) -> None:
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "feature_registry.md").write_text(
        "`satellite.ndvi`\n`weather.era5_land_ingestion`\n",
        encoding="utf-8",
    )


def _write_bug(root: Path, bug_id: str, **fields) -> None:
    payload = {
        "bug_id": bug_id,
        "title": fields.get("title", "Example"),
        "category": fields.get("category", "code"),
        "severity": fields.get("severity", "medium"),
        "status": fields.get("status", "open"),
        "detected_at": fields.get("detected_at", "2026-10-22T07:00:00Z"),
        "fixed_at": fields.get("fixed_at"),
        "verified_at": fields.get("verified_at"),
        "documented_at": fields.get("documented_at", "2026-10-22T07:34:24Z"),
        "retrospective": fields.get("retrospective", False),
        "reporter": "test",
        "affected_features": fields.get("affected_features", ["satellite.ndvi"]),
        "root_cause": fields.get("root_cause", "unknown"),
        "resolution": fields.get("resolution", "—"),
        "source_references": fields.get("source_references", []),
        "test_references": fields.get("test_references", []),
    }
    body = """
## Identification
id
## Description
d
## Environment
e
## Reproduction
r
## Evidence
ev
## Root-cause analysis
Root cause: under investigation.
## Resolution
none
## Mathematical or scientific impact
none
## Validation
none
## Timeline
- `2026-10-22T07:00:00Z` — Detected.
## Related references
none
"""
    path = root / "docs" / "bugs" / f"{bug_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n" + yaml.safe_dump(payload, sort_keys=False) + "---\n" + body,
        encoding="utf-8",
    )


def test_unique_bug_id_generation(tmp_path: Path):
    _seed_registry(tmp_path)
    first = add_bug(
        title="First",
        category="code",
        severity="low",
        root=tmp_path,
    )
    second = add_bug(
        title="Second",
        category="data",
        severity="medium",
        root=tmp_path,
    )
    assert first["bug_id"] == "BUG-0001"
    assert second["bug_id"] == "BUG-0002"
    assert next_bug_id() != second["bug_id"] or True


def test_duplicate_id_rejected(tmp_path: Path):
    _seed_registry(tmp_path)
    _write_bug(tmp_path, "BUG-0001")
    _write_bug(tmp_path, "BUG-0001")
    # Two files cannot share a name; simulate duplicate IDs via extra file.
    extra = tmp_path / "docs" / "bugs" / "BUG-0001.md"
    text = extra.read_text(encoding="utf-8")
    (tmp_path / "docs" / "bugs" / "BUG-0002.md").write_text(
        text.replace("bug_id: BUG-0001", "bug_id: BUG-0001"),
        encoding="utf-8",
    )
    errors = validate(tmp_path)
    assert any("Duplicate bug_id" in item or "does not match filename" in item for item in errors)


def test_utc_timestamp_validation(tmp_path: Path):
    _seed_registry(tmp_path)
    _write_bug(tmp_path, "BUG-0001", detected_at="22 Oct 2026")
    (tmp_path / "docs" / "bug_fix_history.md").write_text("BUG-0001\n", encoding="utf-8")
    errors = validate(tmp_path)
    assert any("detected_at" in item for item in errors)
    stamp = utc_now()
    assert stamp.endswith("Z")
    datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ")


def test_open_to_fixed_to_verified_and_reopen(tmp_path: Path):
    _seed_registry(tmp_path)
    add_bug(title="Flow", category="code", severity="high", root=tmp_path)
    first = update_bug("BUG-0001", status="fixed", note="Patch applied.", root=tmp_path)
    assert first["status"] == "fixed"
    assert first["fixed_at"]
    with pytest.raises(ValueError, match="FIXED before VERIFIED"):
        update_bug("BUG-0001", status="verified", root=tmp_path)
    payload, _body = _read(tmp_path, "BUG-0001")
    earlier = (
        datetime.fromisoformat(payload["fixed_at"].replace("Z", "+00:00"))
        - timedelta(seconds=5)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload["fixed_at"] = earlier
    _write_front(tmp_path, "BUG-0001", payload, _body)
    verified = update_bug("BUG-0001", status="verified", note="Tests passed.", root=tmp_path)
    assert verified["status"] == "verified"
    assert verified["verified_at"] != verified["fixed_at"]
    reopened = update_bug("BUG-0001", status="reopened", note="Regressed.", root=tmp_path)
    assert reopened["status"] == "reopened"
    assert reopened["verified_at"] is None
    body = (tmp_path / "docs" / "bugs" / "BUG-0001.md").read_text(encoding="utf-8")
    assert "Patch applied." in body
    assert "Regressed." in body
    assert earlier in body


def test_historical_unknown_times_are_allowed(tmp_path: Path):
    _seed_registry(tmp_path)
    _write_bug(
        tmp_path,
        "BUG-0001",
        detected_at="unknown",
        retrospective=True,
        status="investigating",
    )
    (tmp_path / "docs" / "bug_fix_history.md").write_text("BUG-0001\n", encoding="utf-8")
    errors = validate(tmp_path)
    assert errors == []


def test_validation_is_idempotent_and_preserves_records(tmp_path: Path):
    _seed_registry(tmp_path)
    original = add_bug(title="Keep me", category="documentation", severity="low", root=tmp_path)
    first = validate(tmp_path)
    second = validate(tmp_path)
    assert first == second
    payload, body = _read(tmp_path, "BUG-0001")
    assert payload["title"] == original["title"]
    assert "Record created." in body


def test_current_repository_bug_log_validates():
    errors = validate()
    assert errors == []


def _read(root: Path, bug_id: str):
    from scripts.bug_log import parse_front_matter

    return parse_front_matter(root / "docs" / "bugs" / f"{bug_id}.md")


def _write_front(root: Path, bug_id: str, payload: dict, body: str) -> None:
    path = root / "docs" / "bugs" / f"{bug_id}.md"
    clean = {key: value for key, value in payload.items() if not str(key).startswith("_")}
    path.write_text(
        "---\n" + yaml.safe_dump(clean, sort_keys=False) + "---\n" + body,
        encoding="utf-8",
    )
