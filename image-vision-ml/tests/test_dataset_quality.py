from pathlib import Path

from ml.ingestion.config import validate_dataset_config
from ml.ingestion.manifest import empty_manifest, save_manifest, upsert_scene
from ml.preprocessing.raster import BAND_FILES
from ml.validation.dataset_quality import (
    assess_training_readiness,
    evaluate_dataset_quality,
    evaluate_scene_quality,
    write_quality_outputs,
)


def test_quality_statuses_and_thresholds():
    valid = evaluate_scene_quality(
        {
            "scene_id": "ok",
            "acquisition_date": "2024-06-01",
            "footprint_overlap_pct": 100.0,
            "valid_percentage": 90.0,
        },
        processed={"valid_percentage": 90.0, "valid_pixels": 90, "total_pixels": 100, "ndvi": {"mean": 0.4}},
        calibration={"validation_status": "verified", "requires_review": False, "bands": {}},
        grid_status={"aligned": True},
    )
    assert valid["quality_status"] == "valid"

    warning = evaluate_scene_quality(
        {"scene_id": "warn", "acquisition_date": "2024-06-01", "footprint_overlap_pct": 100.0},
        processed={"valid_percentage": 80.0, "ndvi": {"mean": 0.3}},
        calibration={"validation_status": "verified", "requires_review": False, "bands": {}},
        grid_status={"aligned": True},
    )
    assert warning["quality_status"] == "warning"

    rejected = evaluate_scene_quality(
        {"scene_id": "low", "acquisition_date": "2024-06-01", "footprint_overlap_pct": 40.0},
        processed={"valid_percentage": 40.0},
        calibration={"validation_status": "verified", "requires_review": False, "bands": {}},
    )
    assert rejected["quality_status"] == "rejected"
    assert "geometric_coverage_below_threshold" in rejected["reasons"]

    review = evaluate_scene_quality(
        {"scene_id": "cal", "acquisition_date": "2024-06-01", "footprint_overlap_pct": 100.0},
        processed={"valid_percentage": 90.0},
        calibration={"validation_status": "conflicting", "requires_review": True, "bands": {}},
        grid_status={"aligned": True},
    )
    assert review["quality_status"] == "requires_review"


def test_missing_assets_and_grid_mismatch_are_rejected():
    missing = evaluate_scene_quality(
        {"scene_id": "miss", "acquisition_date": "2024-01-01", "footprint_overlap_pct": 100.0},
        missing_assets=["red_B04.tif"],
        calibration={"validation_status": "verified", "requires_review": False, "bands": {}},
    )
    assert missing["quality_status"] == "rejected"
    assert missing["missing_assets"] == ["red_B04.tif"]

    grid = evaluate_scene_quality(
        {"scene_id": "grid", "acquisition_date": "2024-01-01", "footprint_overlap_pct": 100.0},
        processed={"valid_percentage": 90.0},
        calibration={"validation_status": "verified", "requires_review": False, "bands": {}},
        grid_status={"aligned": False},
    )
    assert grid["quality_status"] == "rejected"
    assert "crs_or_grid_mismatch" in grid["reasons"]


def test_dataset_quality_and_reports(tmp_path: Path):
    config = validate_dataset_config({
        "dataset_id": "plovdiv_2023_2025",
        "source": {"collection": "sentinel-2-l2a"},
        "area": {"bbox": [24.65, 42.05, 24.68, 42.08]},
        "period": {"start": "2023-01-01", "end": "2025-12-31"},
    })
    raw = tmp_path / "raw" / "plovdiv_2023_2025"
    processed = tmp_path / "processed" / "plovdiv_2023_2025"
    manifest = empty_manifest(config)
    upsert_scene(
        manifest,
        "S2A_35TLG_20230601_1_L2A",
        status="processed",
        acquisition_date="2023-06-01",
        footprint_overlap_pct=100.0,
        aoi_coverage=100.0,
        valid_percentage=92.0,
        valid_pixels=92,
        total_pixels=100,
        ndvi={"mean": 0.55, "median": 0.54, "minimum": 0.1, "maximum": 0.8, "standard_deviation": 0.1},
    )
    upsert_scene(
        manifest,
        "S2A_35TLG_20240601_1_L2A",
        status="processed",
        acquisition_date="2024-06-01",
        footprint_overlap_pct=100.0,
        aoi_coverage=100.0,
        valid_percentage=88.0,
        ndvi={"mean": 0.60},
    )
    save_manifest(raw / "manifest.json", manifest)
    processed_manifest = dict(manifest)
    processed_manifest["target_grid"] = {
        "crs": "EPSG:32635",
        "transform": [10, 0, 0, 0, -10, 0],
        "width": 10,
        "height": 10,
    }
    save_manifest(processed / "manifest.json", processed_manifest)
    for scene_id in ("S2A_35TLG_20230601_1_L2A", "S2A_35TLG_20240601_1_L2A"):
        scene_dir = raw / "scenes" / scene_id
        scene_dir.mkdir(parents=True)
        (scene_dir / "calibration.json").write_text(
            '{"validation_status": "verified", "requires_review": false, "bands": {}}',
            encoding="utf-8",
        )
        (scene_dir / "metadata.json").write_text("{}", encoding="utf-8")
        for filename in BAND_FILES.values():
            (scene_dir / filename).write_bytes(b"tif")

    payload = evaluate_dataset_quality(
        "plovdiv_2023_2025",
        raw_root=tmp_path / "raw",
        processed_root=tmp_path / "processed",
        config=config,
    )
    assert payload["dataset"]["validated_scenes"] == 2
    assert "2023-01" in payload["dataset"]["missing_months"]
    files = write_quality_outputs(payload, processed / "quality")
    assert (processed / "quality" / files["json"]).is_file()
    assert (processed / "quality" / files["csv"]).is_file()
    assert (processed / "quality" / files["training_readiness"]).is_file()
    assert payload["training_readiness"]["supervised_soil_forecasting"] == "not_ready"


def test_training_readiness_distinguishes_use_cases():
    summary = {
        "validated_scenes": 4,
        "observation_count_per_year": {"2023": 2, "2024": 2},
        "missing_months": ["2023-02"],
        "temporal_gaps": [{"days": 40}],
        "spatial_grid_consistency": {"consistent": True},
        "calibration_failure_count": 0,
        "period": {"start": "2023-01-01", "end": "2024-12-31"},
        "observation_count_per_month": {"2023-01": 1},
    }
    report = assess_training_readiness(summary, [])
    assert report["historical_satellite_analysis"] == "suitable_for_exploratory_analysis"
    assert report["supervised_soil_forecasting"] == "not_ready"
    assert report["overall"] != "ready_for_soil_forecasting"
