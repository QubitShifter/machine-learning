import numpy as np

from pathlib import Path

from ml.ingestion.config import DEFAULT_QUALITY
from ml.preprocessing.features import NDVI_DENOMINATOR_EPS, make_valid_mask
from ml.validation.dataset_quality import evaluate_scene_quality
from ml.validation.pixel_exclusion import (
    REASON_BLUE_GREEN,
    REASON_DENOMINATOR,
    REASON_RED_NIR,
    REASON_VALID,
    classify_pixel_exclusions,
    residual_exclusion_counts,
)


def _conservation(report: dict) -> None:
    reasons = report["disjoint_by_reason_including_zeros"]
    assert sum(reasons.values()) == report["total_aoi_pixels"]
    assert (
        report["valid_pixels"] + sum(
            count for key, count in reasons.items() if key != REASON_VALID
        )
        == report["total_aoi_pixels"]
    )
    assert report["pixel_conservation_ok"] is True
    assert report["valid_pixels"] + report["excluded_pixels"] == report["total_aoi_pixels"]


def test_disjoint_counts_conserve_every_pixel():
    scl = np.array([
        [4, 5, 11, 2],
        [0, 6, 4, 7],
    ], dtype=np.uint8)
    red = np.array([
        [0.2, 0.1, 0.3, 0.2],
        [0.2, 0.2, np.nan, 0.2],
    ], dtype=np.float32)
    nir = np.array([
        [0.6, 0.4, 0.5, 0.4],
        [0.5, 0.5, 0.4, 0.5],
    ], dtype=np.float32)
    blue = np.full(scl.shape, 0.1, dtype=np.float32)
    green = np.full(scl.shape, 0.15, dtype=np.float32)
    blue[0, 1] = np.nan

    report = classify_pixel_exclusions(
        scl, red=red, nir=nir, blue=blue, green=green
    )
    _conservation(report)
    reasons = report["disjoint_by_reason"]
    assert reasons["scl_snow_ice"] == 1
    assert reasons["scl_dark_area"] == 1
    assert reasons["scl_nodata"] == 1
    assert reasons["scl_water"] == 1
    assert reasons["scl_unclassified"] == 1
    assert reasons[REASON_RED_NIR] == 1
    assert reasons[REASON_BLUE_GREEN] == 1
    assert reasons[REASON_VALID] == 1
    assert report["total_aoi_pixels"] == 8


def test_nodata_and_raster_masks_are_classified():
    scl = np.array([[4, 4], [4, 4]], dtype=np.uint8)
    red = np.array([[0.2, np.nan], [0.2, 0.2]], dtype=np.float32)
    nir = np.array([[0.4, 0.4], [np.inf, 0.5]], dtype=np.float32)
    report = classify_pixel_exclusions(scl, red=red, nir=nir)
    _conservation(report)
    assert report["disjoint_by_reason"][REASON_RED_NIR] == 2
    assert report["disjoint_by_reason"][REASON_VALID] == 2


def test_scl_rejection_and_snow_ice():
    scl = np.array([[11, 11, 3, 8, 9, 10, 1]], dtype=np.uint8)
    red = np.full(scl.shape, 0.2, dtype=np.float32)
    nir = np.full(scl.shape, 0.6, dtype=np.float32)
    report = classify_pixel_exclusions(scl, red=red, nir=nir)
    _conservation(report)
    reasons = report["disjoint_by_reason"]
    assert reasons["scl_snow_ice"] == 2
    assert reasons["scl_cloud_shadow"] == 1
    assert reasons["scl_cloud_medium_probability"] == 1
    assert reasons["scl_cloud_high_probability"] == 1
    assert reasons["scl_thin_cirrus"] == 1
    assert reasons["scl_saturated_or_defective"] == 1
    assert REASON_VALID not in reasons
    assert report["valid_pixels"] == 0


def test_ndvi_denominator_failure_is_disjoint():
    scl = np.array([[4, 5]], dtype=np.uint8)
    red = np.array([[0.0, 1e-12]], dtype=np.float32)
    nir = np.array([[0.0, -1e-12]], dtype=np.float32)
    report = classify_pixel_exclusions(
        scl,
        red=red,
        nir=nir,
        ndvi_denominator_eps=NDVI_DENOMINATOR_EPS,
    )
    _conservation(report)
    assert report["disjoint_by_reason"][REASON_DENOMINATOR] == 2
    assert report["valid_pixels"] == 0


def test_scl_precedence_over_optical_nodata():
    scl = np.array([[11]], dtype=np.uint8)
    red = np.array([[np.nan]], dtype=np.float32)
    nir = np.array([[np.nan]], dtype=np.float32)
    report = classify_pixel_exclusions(scl, red=red, nir=nir)
    _conservation(report)
    assert report["disjoint_by_reason"] == {"scl_snow_ice": 1}
    assert REASON_RED_NIR not in report["disjoint_by_reason"]


def test_valid_mask_matches_valid_ndvi_reason():
    scl = np.array([[4, 5, 6, 11], [0, 4, 4, 2]], dtype=np.uint8)
    red = np.array([[0.2, 0.1, 0.2, 0.2], [0.2, np.nan, 0.0, 0.2]], dtype=np.float32)
    nir = np.array([[0.6, 0.4, 0.4, 0.5], [0.4, 0.4, 0.0, 0.4]], dtype=np.float32)
    blue = np.full(scl.shape, 0.1, dtype=np.float32)
    green = np.full(scl.shape, 0.1, dtype=np.float32)
    mask = make_valid_mask(scl, red, green, blue, nir)
    ndvi_ok = mask & np.isfinite(red) & np.isfinite(nir) & (
        np.abs(nir + red) > NDVI_DENOMINATOR_EPS
    )
    report = classify_pixel_exclusions(
        scl, red=red, nir=nir, blue=blue, green=green
    )
    _conservation(report)
    assert report["valid_pixels"] == int(ndvi_ok.sum())


def test_residual_accounting_is_not_treated_as_conservation():
    residual = residual_exclusion_counts(
        total=87978,
        valid=57307,
        scl_distribution={"2": 1620, "4": 789, "5": 13661, "6": 13, "11": 5847},
    )
    assert residual["accounting_mode"] == "residual_unresolved_grid"
    assert residual["other_or_unclassified"] == 23191
    assert residual["pixel_conservation_ok"] is False


def test_calibration_valid_when_scene_rejected():
    report = evaluate_scene_quality(
        {
            "scene_id": "S2B_35TLG_20250119_0_L2A",
            "acquisition_date": "2025-01-19",
            "footprint_overlap_pct": 100.0,
        },
        processed={
            "valid_percentage": 65.14,
            "valid_pixels": 57307,
            "total_pixels": 87978,
            "ndvi": {"mean": 0.34, "minimum": -0.29, "maximum": 0.99},
        },
        calibration={"validation_status": "verified", "requires_review": False, "bands": {}},
        grid_status={"aligned": True},
        exclusion_counts={"valid_pixels": 57307, "total_pixels": 87978},
    )
    assert report["quality_status"] == "rejected"
    assert report["scene_quality_status"] == "rejected"
    assert report["calibration_status"] == "verified"
    assert "valid_ndvi_below_threshold" in report["scene_quality_reasons"]
    assert report["quality_status"] != report["calibration_status"]


JANUARY_SCENE = (
    Path("data/processed/satellite/plovdiv_2023_2025/scenes")
    / "S2B_35TLG_20250119_0_L2A"
)


def test_january_2025_scene_remains_rejected_with_conserved_pixels():
    raw = Path("data/raw/satellite/plovdiv_2023_2025/scenes/S2B_35TLG_20250119_0_L2A")
    processed = JANUARY_SCENE
    if not (processed / "quality_report.json").is_file() or not (raw / "scl.tif").is_file():
        return
    from ml.preprocessing.raster import read_json
    from ml.validation.pixel_exclusion import exclusion_report_for_scene

    stats = read_json(processed / "statistics.json") if (processed / "statistics.json").is_file() else None
    meta = read_json(processed / "processing_metadata.json")
    report = exclusion_report_for_scene(
        raw,
        processed,
        stats=stats,
        processing_meta=meta,
    )
    assert report["accounting_mode"] == "disjoint_target_grid"
    assert report["total_pixels"] == 87978
    assert report["valid_pixels"] == 57307
    assert report["pixel_conservation_ok"] is True
    reasons = report["disjoint_by_reason"]
    assert reasons["valid_ndvi"] == 57307
    assert reasons["scl_snow_ice"] == 23388
    assert reasons["scl_dark_area"] == 6480
    assert sum(reasons.values()) == 87978
    quality = evaluate_scene_quality(
        {
            "scene_id": "S2B_35TLG_20250119_0_L2A",
            "acquisition_date": "2025-01-19",
            "footprint_overlap_pct": 100.0,
        },
        processed={
            "valid_percentage": 65.14,
            "valid_pixels": 57307,
            "total_pixels": 87978,
        },
        calibration={"validation_status": "verified", "requires_review": False, "bands": {}},
        grid_status={"aligned": True},
        exclusion_counts=report,
    )
    assert quality["scene_quality_status"] == "rejected"
    assert quality["calibration_status"] == "verified"
    assert DEFAULT_QUALITY["min_valid_ndvi_pct"] == 70.0


def test_quality_thresholds_are_not_lowered():
    assert DEFAULT_QUALITY["min_aoi_coverage_pct"] == 95.0
    assert DEFAULT_QUALITY["min_valid_ndvi_pct"] == 70.0
    assert DEFAULT_QUALITY["calibration_policy"] == "verified_only"
    borderline = evaluate_scene_quality(
        {"scene_id": "edge", "acquisition_date": "2025-01-19", "footprint_overlap_pct": 95.0},
        processed={"valid_percentage": 70.0, "valid_pixels": 70, "total_pixels": 100},
        calibration={"validation_status": "verified", "requires_review": False, "bands": {}},
        grid_status={"aligned": True},
    )
    assert borderline["quality_status"] == "warning"
    below = evaluate_scene_quality(
        {"scene_id": "below", "acquisition_date": "2025-01-19", "footprint_overlap_pct": 94.9},
        processed={"valid_percentage": 69.99},
        calibration={"validation_status": "verified", "requires_review": False, "bands": {}},
        grid_status={"aligned": True},
    )
    assert below["quality_status"] == "rejected"
    assert "geometric_coverage_below_threshold" in below["reasons"]
    assert "valid_ndvi_below_threshold" in below["reasons"]
