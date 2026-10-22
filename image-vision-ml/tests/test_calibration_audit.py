from pathlib import Path

from ml.ingestion.config import validate_dataset_config
from ml.ingestion.manifest import empty_manifest, save_manifest, upsert_scene
from ml.validation.calibration_audit import (
    INTERPRETATION_CONFLICTING,
    INTERPRETATION_CONSISTENT,
    INTERPRETATION_CORRUPT,
    INTERPRETATION_INCOMPLETE,
    audit_dataset_calibration,
    audit_scene_calibration,
)


def test_missing_calibration_stays_requires_review():
    report = audit_scene_calibration(
        "missing",
        record={"acquisition_date": "2025-02-08", "processing_baseline": None},
        raw_dir=Path("/tmp/does-not-exist-raw"),
        processed_dir=Path("/tmp/does-not-exist-processed"),
    )
    assert report["current_status"] == "requires_review"
    assert report["interpretation"] == INTERPRETATION_INCOMPLETE
    assert report["processing_baseline"] is None


def test_corrupt_calibration_is_not_invented(tmp_path: Path):
    raw = tmp_path / "raw"
    processed = tmp_path / "processed"
    raw.mkdir()
    processed.mkdir()
    (raw / "calibration.json").write_text("{not-json", encoding="utf-8")
    report = audit_scene_calibration(
        "corrupt",
        record={"acquisition_date": "2025-03-08"},
        raw_dir=raw,
        processed_dir=processed,
    )
    assert report["current_status"] == "requires_review"
    assert report["interpretation"] == INTERPRETATION_CORRUPT


def test_conflicting_offset_is_not_validated_from_ndvi(tmp_path: Path):
    raw = tmp_path / "raw"
    processed = tmp_path / "processed"
    raw.mkdir()
    processed.mkdir()
    (raw / "calibration.json").write_text(
        '{"validation_status": "conflicting", "requires_review": true, '
        '"reason": "majority_negative_after_negative_offset", "bands": {}}',
        encoding="utf-8",
    )
    (processed / "quality_report.json").write_text(
        '{"quality_status": "requires_review", "ndvi_minimum": -1100, "ndvi_maximum": 1097}',
        encoding="utf-8",
    )
    report = audit_scene_calibration(
        "S2B_34TGM_20250208_0_L2A",
        record={
            "acquisition_datetime": "2025-02-08T09:18:47Z",
            "processing_baseline": None,
            "earthsearch_boa_offset_applied": False,
        },
        raw_dir=raw,
        processed_dir=processed,
    )
    assert report["current_status"] == "requires_review"
    assert report["interpretation"] == INTERPRETATION_CONFLICTING
    assert "ndvi_is_not_evidence_of_valid_calibration" in report["review_requirements"]


def test_quality_valid_is_not_downgraded_for_unverified_sidecar(tmp_path: Path):
    raw = tmp_path / "raw"
    processed = tmp_path / "processed"
    raw.mkdir()
    processed.mkdir()
    (raw / "calibration.json").write_text(
        '{"validation_status": "unverified", "requires_review": true, "bands": {}}',
        encoding="utf-8",
    )
    (processed / "quality_report.json").write_text(
        '{"quality_status": "valid", "ndvi_minimum": 0.1, "ndvi_maximum": 0.8}',
        encoding="utf-8",
    )
    report = audit_scene_calibration(
        "accepted",
        record={"acquisition_date": "2023-02-22"},
        raw_dir=raw,
        processed_dir=processed,
    )
    assert report["current_status"] == "valid"
    assert report["previous_status"] == "valid"


def test_source_urls_are_copied_and_not_invented(tmp_path: Path):
    raw = tmp_path / "raw"
    processed = tmp_path / "processed"
    raw.mkdir()
    processed.mkdir()
    (raw / "calibration.json").write_text(
        '{"validation_status": "verified", "requires_review": false, "bands": {}}',
        encoding="utf-8",
    )
    (processed / "quality_report.json").write_text(
        '{"quality_status": "valid", "ndvi_minimum": 0.1, "ndvi_maximum": 0.8}',
        encoding="utf-8",
    )
    href = "https://example.invalid/B04.tif"
    report = audit_scene_calibration(
        "ok",
        record={
            "acquisition_date": "2025-01-19",
            "source_urls": {"red": href, "blue": href, "green": href, "nir": href, "scl": href},
        },
        raw_dir=raw,
        processed_dir=processed,
    )
    assert report["source_metadata_reference"]["stac_asset_hrefs_complete"] is True
    assert report["source_metadata_reference"]["hrefs"]["red"] == href
    missing = audit_scene_calibration(
        "missing-urls",
        record={"acquisition_date": "2025-01-19"},
        raw_dir=raw,
        processed_dir=processed,
    )
    assert missing["source_metadata_reference"]["stac_asset_hrefs_complete"] is False
    assert missing["source_metadata_reference"]["hrefs"]["red"] is None


def test_rejected_scene_can_keep_verified_calibration(tmp_path: Path):
    raw = tmp_path / "raw"
    processed = tmp_path / "processed"
    raw.mkdir()
    processed.mkdir()
    (raw / "calibration.json").write_text(
        '{"validation_status": "verified", "requires_review": false, "bands": {}}',
        encoding="utf-8",
    )
    (processed / "quality_report.json").write_text(
        '{"quality_status": "rejected", "scene_quality_status": "rejected", '
        '"scene_quality_reasons": ["valid_ndvi_below_threshold"], '
        '"ndvi_minimum": -0.29, "ndvi_maximum": 0.99}',
        encoding="utf-8",
    )
    report = audit_scene_calibration(
        "S2B_35TLG_20250119_0_L2A",
        record={"acquisition_date": "2025-01-19", "processing_baseline": "05.11"},
        raw_dir=raw,
        processed_dir=processed,
    )
    assert report["calibration_status"] == "valid"
    assert report["current_status"] == "valid"
    assert report["scene_quality_status"] == "rejected"
    assert report["status_scope"] == "calibration"
    assert "scene_quality_status_independent_of_calibration=rejected" in report["evidence"]
    assert report["source_metadata_reference"]["stac_asset_hrefs_complete"] is False


def test_verified_calibration_keeps_valid_status(tmp_path: Path):
    raw = tmp_path / "raw"
    processed = tmp_path / "processed"
    raw.mkdir()
    processed.mkdir()
    (raw / "calibration.json").write_text(
        '{"validation_status": "verified", "requires_review": false, "bands": {}}',
        encoding="utf-8",
    )
    (processed / "quality_report.json").write_text(
        '{"quality_status": "valid", "ndvi_minimum": 0.1, "ndvi_maximum": 0.8}',
        encoding="utf-8",
    )
    report = audit_scene_calibration(
        "ok",
        record={"acquisition_date": "2023-06-09", "processing_baseline": "05.11"},
        raw_dir=raw,
        processed_dir=processed,
    )
    assert report["current_status"] == "valid"
    assert report["interpretation"] == INTERPRETATION_CONSISTENT


def test_dataset_audit_only_uses_acquired_scenes(tmp_path: Path):
    config = validate_dataset_config({
        "dataset_id": "plovdiv_2023_2025",
        "source": {"collection": "sentinel-2-l2a"},
        "area": {"bbox": [24.65, 42.05, 24.68, 42.08]},
        "period": {"start": "2023-01-01", "end": "2025-12-31"},
    })
    raw = tmp_path / "raw"
    processed = tmp_path / "processed"
    manifest = empty_manifest(config)
    upsert_scene(manifest, "catalog_only", status="discovered", acquisition_date="2023-01-01")
    upsert_scene(manifest, "acquired", status="processed", acquisition_date="2023-06-01")
    save_manifest(raw / "manifest.json", manifest)
    (raw / "scenes" / "acquired").mkdir(parents=True)
    (processed / "scenes" / "acquired").mkdir(parents=True)
    (raw / "scenes" / "acquired" / "calibration.json").write_text(
        '{"validation_status": "verified", "requires_review": false, "bands": {}}',
        encoding="utf-8",
    )
    leftover = processed / "scenes" / "catalog_only"
    leftover.mkdir(parents=True)
    (leftover / "quality_report.json").write_text("{}", encoding="utf-8")
    audit = audit_dataset_calibration(
        "plovdiv_2023_2025",
        raw_dir=raw,
        processed_dir=processed,
    )
    assert audit["scene_count"] == 1
    assert audit["scenes"][0]["scene_id"] == "acquired"
    assert "catalog_only" not in audit["unresolved_scene_ids"]
