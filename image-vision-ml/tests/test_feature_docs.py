from pathlib import Path

import yaml

from scripts.check_feature_docs import validate


def test_feature_docs_validate_current_tree():
    errors = validate()
    assert errors == []


def test_duplicate_feature_ids_are_rejected(tmp_path: Path):
    docs = tmp_path / "docs"
    features = docs / "features" / "satellite"
    features.mkdir(parents=True)
    body = _valid_body()
    for name in ("a.md", "b.md"):
        (features / name).write_text(
            "---\n" + yaml.safe_dump({
                "feature_id": "satellite.ndvi",
                "name": "NDVI",
                "category": "satellite",
                "status": "planned",
                "mathematical_method": "ratio",
                "input_datasets": ["sentinel-2"],
                "source_code": [],
                "configuration": [],
                "outputs": ["ndvi"],
                "tests": [],
                "last_verified": "2026-10-22T07:34:24Z",
            }) + "---\n" + body,
            encoding="utf-8",
        )
    (docs / "feature_registry.md").write_text("`satellite.ndvi`\n", encoding="utf-8")
    errors = validate(tmp_path)
    assert any("Duplicate feature_id" in item for item in errors)


def test_missing_section_is_rejected(tmp_path: Path):
    docs = tmp_path / "docs" / "features" / "weather"
    docs.mkdir(parents=True)
    (tmp_path / "docs" / "feature_registry.md").write_text("`weather.wind`\n", encoding="utf-8")
    (docs / "wind.md").write_text(
        "---\nfeature_id: weather.wind\nname: Wind\ncategory: weather\n"
        "status: planned\nmathematical_method: hypot\ninput_datasets: [era5]\n"
        "source_code: []\nconfiguration: []\noutputs: [wind]\ntests: []\n"
        "last_verified: 2026-10-22T07:34:24Z\n---\n\n## Feature ID and name\n\nx\n",
        encoding="utf-8",
    )
    errors = validate(tmp_path)
    assert any("missing required section" in item for item in errors)


def _valid_body() -> str:
    sections = [
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
    return "\n".join(f"## {index}. {name}\n\nPlaceholder.\n" for index, name in enumerate(sections, 1))
