from pathlib import Path

import yaml

from scripts.change_log import next_change_id, utc_now, validate


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


def _seed(root: Path) -> None:
    docs = root / "docs"
    docs.mkdir(parents=True)
    (docs / "feature_registry.md").write_text("`ui.satellite_explorer_workspace`\n", encoding="utf-8")
    (docs / "bugs").mkdir()
    (docs / "bugs" / "BUG-0011.md").write_text("# BUG-0011\n", encoding="utf-8")
    (docs / "changes").mkdir()
    (docs / "change_history.md").write_text("CHG-0001\n", encoding="utf-8")
    (root / "frontend" / "src").mkdir(parents=True)
    (root / "frontend" / "src" / "example.tsx").write_text("export {}\n", encoding="utf-8")


def _write_change(root: Path, change_id: str, **fields) -> None:
    payload = {
        "change_id": change_id,
        "title": fields.get("title", "Example"),
        "timestamp": fields.get("timestamp", "2026-10-22T13:53:13Z"),
        "documented_at": fields.get("documented_at", "2026-10-22T13:53:13Z"),
        "phase": fields.get("phase", "3.5 UI Refinement"),
        "change_type": fields.get("change_type", "enhancement"),
        "status": fields.get("status", "tested"),
        "retrospective": fields.get("retrospective", False),
        "related_features": fields.get("related_features", ["ui.satellite_explorer_workspace"]),
        "related_bugs": fields.get("related_bugs", ["BUG-0011"]),
        "git_reference": fields.get("git_reference", "uncommitted"),
        "scientific_impact": fields.get("scientific_impact", "none"),
        "modified_files": fields.get("modified_files", ["frontend/src/example.tsx"]),
    }
    body = fields.get("body") or "\n".join(f"## {section}\ntext\n" for section in REQUIRED_SECTIONS)
    path = root / "docs" / "changes" / f"{change_id}.md"
    path.write_text("---\n" + yaml.safe_dump(payload, sort_keys=False) + "---\n" + body, encoding="utf-8")


def test_unique_change_ids(tmp_path: Path):
    _seed(tmp_path)
    _write_change(tmp_path, "CHG-0001")
    _write_change(tmp_path, "CHG-0002", documented_at="2026-10-22T13:53:14Z")
    (tmp_path / "docs" / "change_history.md").write_text("CHG-0001 CHG-0002\n", encoding="utf-8")
    errors = validate(tmp_path)
    assert errors == []
    assert next_change_id(
        [{"change_id": "CHG-0001"}, {"change_id": "CHG-0002"}]
    ) == "CHG-0003"


def test_invalid_timestamp_and_missing_section(tmp_path: Path):
    _seed(tmp_path)
    _write_change(
        tmp_path,
        "CHG-0001",
        timestamp="22 Oct 2026",
        body="## Reason\nonly\n",
    )
    errors = validate(tmp_path)
    assert any("timestamp" in item for item in errors)
    assert any("missing section" in item for item in errors)


def test_unknown_timestamp_requires_retrospective(tmp_path: Path):
    _seed(tmp_path)
    _write_change(tmp_path, "CHG-0001", timestamp="unknown", retrospective=False)
    errors = validate(tmp_path)
    assert any("non-retrospective" in item for item in errors)
    _write_change(tmp_path, "CHG-0001", timestamp="unknown", retrospective=True)
    errors = validate(tmp_path)
    assert errors == []


def test_referenced_files_and_ids_must_exist(tmp_path: Path):
    _seed(tmp_path)
    _write_change(
        tmp_path,
        "CHG-0001",
        related_features=["missing.feature"],
        related_bugs=["BUG-9999"],
        modified_files=["no/such/file.tsx"],
    )
    errors = validate(tmp_path)
    assert any("related feature" in item for item in errors)
    assert any("related bug" in item for item in errors)
    assert any("modified file does not exist" in item for item in errors)


def test_utc_now_format():
    stamp = utc_now()
    assert stamp.endswith("Z")


def test_current_repository_change_history_validates():
    errors = validate()
    assert errors == []
