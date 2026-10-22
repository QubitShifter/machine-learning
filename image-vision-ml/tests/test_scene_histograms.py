"""Deterministic tests for mask-aware NDVI/reflectance/SCL histograms."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from rasterio.transform import Affine

from ml.analysis.scene_histograms import (
    DEFAULT_BINS,
    HISTOGRAM_VERSION,
    NDVI_DOMAIN,
    auto_zoom_upper,
    build_scene_histograms,
    equal_width_edges,
    masked_histogram,
    scene_histogram_payload,
    scl_distribution,
    scl_distribution_from_counts,
    summarize_values,
    viewport_outside_fraction,
)
from ml.preprocessing.raster import write_geotiff


def test_equal_width_edges_cover_ndvi_domain():
    edges = equal_width_edges(-1, 1, 45)
    assert len(edges) == 46
    assert edges[0] == -1.0
    assert edges[-1] == 1.0
    widths = np.diff(edges)
    assert np.allclose(widths, widths[0])


def test_masked_pixels_are_never_counted_as_zero():
    values = np.array([[0.0, 0.4], [np.nan, 0.8]], dtype=np.float32)
    mask = np.array([[False, True], [True, True]])
    result = masked_histogram(values, mask, low=-1, high=1, bins=4)
    assert result["masked_or_nodata_count"] == 1
    assert result["masked_treated_as_zero"] is False
    assert result["clamped"] is False
    assert result["valid_pixel_count"] == 2
    assert result["pixel_conservation_ok"] is True
    stats = result["statistics"]
    assert stats["mean"] == pytest.approx(0.6)
    assert stats["minimum"] == pytest.approx(0.4)
    assert 0.0 not in result["counts"] or result["in_range_count"] == 2


def test_pixel_conservation_includes_out_of_range_and_nonfinite():
    values = np.array([0.2, 1.5, np.nan, -0.1, 0.0], dtype=np.float64)
    mask = np.array([True, True, True, False, True])
    result = masked_histogram(values, mask, low=0.0, high=1.0, bins=5)
    assert result["total_pixels"] == 5
    assert result["masked_or_nodata_count"] == 1
    assert result["out_of_range_count"] == 1
    assert result["nonfinite_unmasked_count"] == 1
    assert result["in_range_count"] == 2
    assert result["pixel_conservation_ok"] is True
    assert result["in_range_count"] + result["out_of_range_count"] + result["nonfinite_unmasked_count"] + result["masked_or_nodata_count"] == 5


def test_invalid_ndvi_is_not_clamped_into_domain():
    values = np.array([[1.4, -1.2], [0.3, 0.1]])
    mask = np.ones((2, 2), dtype=bool)
    result = masked_histogram(values, mask, low=-1, high=1, bins=10)
    assert result["out_of_range_count"] == 2
    assert result["valid_pixel_count"] == 2
    assert result["clamped"] is False
    assert result["statistics"]["maximum"] <= 1.0
    assert result["statistics"]["minimum"] >= -1.0


def test_percentiles_and_summary():
    values = np.arange(1, 11, dtype=np.float64)
    stats = summarize_values(values)
    assert stats["count"] == 10
    assert stats["mean"] == 5.5
    assert stats["median"] == 5.5
    assert stats["p10"] == 1.9
    assert stats["p90"] == 9.1
    assert stats["p99"] == pytest.approx(9.91)
    empty = summarize_values(np.array([]))
    assert empty["mean"] is None
    assert empty["p99"] is None


def test_auto_zoom_uses_highest_p99_with_padding_and_full_range_cap():
    assert auto_zoom_upper([0.2, 0.16, 0.12]) == pytest.approx(0.23)
    assert auto_zoom_upper([0.96]) == 1.0
    assert auto_zoom_upper([None, None]) == 1.0
    values = np.array([0.04] * 98 + [0.20, 0.80])
    mask = np.ones(values.shape, dtype=bool)
    hist = masked_histogram(values, mask, low=0, high=1, bins=20)
    assert hist["histogrammed_count"] == 100
    assert hist["masked_count"] == 0
    assert hist["statistics"]["p99"] is not None
    zoom = auto_zoom_upper([hist["statistics"]["p99"]])
    outside = viewport_outside_fraction(
        hist["histogram"],
        zoom_high=zoom,
        in_range_count=hist["in_range_count"],
    )
    assert outside["outside_count"] >= 1
    assert hist["counts"] == [int(item["count"]) for item in hist["histogram"]]


def test_band_histogram_counts_may_differ_without_forcing_equality():
    mask = np.array([[True, True], [True, False]])
    red = np.array([[0.1, 0.2], [np.nan, 0.9]])
    green = np.array([[0.1, 0.2], [0.3, 0.9]])
    payload = scene_histogram_payload(
        ndvi=np.array([[0.4, 0.5], [0.6, 0.7]]),
        valid_mask=mask,
        reflectance={"B04": red, "B03": green, "B02": green},
        bins=8,
    )
    red_n = payload["reflectance"]["channels"]["red"]["in_range_count"]
    green_n = payload["reflectance"]["channels"]["green"]["in_range_count"]
    assert red_n == green_n - 1
    assert payload["reflectance"]["band_count_agreement"]["forced_equal"] is False
    assert payload["reflectance"]["band_count_agreement"]["in_range_spread"] == 1


def test_scl_distribution_uses_10m_counts_not_native_20m():
    scl = np.array([[4, 4, 5], [11, 6, 8]], dtype=np.uint8)
    payload = scl_distribution(scl)
    assert payload["grid"] == "target_10m_aoi"
    assert payload["native_20m_mixed"] is False
    assert payload["total_pixels"] == 6
    assert payload["pixel_conservation_ok"] is True
    by_code = {item["code"]: item for item in payload["classes"]}
    assert by_code[4]["count"] == 2
    assert by_code[11]["name"] == "Snow / ice"
    groups = {item["group"]: item for item in payload["groups"]}
    assert groups["vegetation"]["count"] == 2
    assert groups["bare_soil"]["count"] == 1
    assert groups["snow_ice"]["count"] == 1
    assert groups["water"]["count"] == 1
    assert groups["cloud_and_shadow"]["count"] == 1


def test_rejected_scene_is_not_labelled_validated():
    ndvi = np.array([[0.2, 0.4], [0.6, 0.8]])
    mask = np.ones((2, 2), dtype=bool)
    payload = scene_histogram_payload(
        ndvi=ndvi,
        valid_mask=mask,
        bins=8,
        quality={
            "scene_quality_status": "rejected",
            "scene_quality_reasons": ["valid_ndvi_below_threshold"],
            "calibration_status": "verified",
        },
        scene_id="S2B_rejected",
    )
    assert payload["scientific_use"] == "rejected_or_review"
    assert payload["scene_quality_status"] == "rejected"
    assert payload["calibration_status"] == "verified"
    assert any("not validated" in item.lower() or "not be treated" in item.lower() for item in payload["warnings"])
    assert payload["ndvi"]["valid_pixel_count"] == 4


def test_reflectance_histogram_excludes_mask_and_keeps_provenance():
    red = np.array([[0.05, 0.2], [1.2, np.nan]])
    mask = np.array([[True, True], [True, False]])
    payload = scene_histogram_payload(
        ndvi=np.array([[0.1, 0.2], [0.3, 0.4]]),
        valid_mask=mask,
        reflectance={"B04": red, "B03": red, "B02": red},
        calibration={"B04": {"scale": 0.0001, "offset": 0.0, "source": "earthsearch"}},
        bins=10,
    )
    channel = payload["reflectance"]["channels"]["red"]
    assert payload["reflectance"]["is_display_rgb"] is False
    assert channel["unit"] == "surface_reflectance"
    assert channel["out_of_range_count"] == 1
    assert channel["masked_or_nodata_count"] == 1
    assert channel["calibration"]["scale"] == 0.0001
    assert channel["pixel_conservation_ok"] is True


def test_build_scene_histograms_from_rasters_and_cache(tmp_path: Path):
    processed = tmp_path / "processed" / "ds" / "scenes" / "SCENE1"
    raw = tmp_path / "raw" / "ds" / "scenes" / "SCENE1"
    processed.mkdir(parents=True)
    transform = Affine(10.0, 0.0, 0.0, 0.0, -10.0, 0.0)
    grid = {"crs": "EPSG:32635", "transform": transform, "width": 3, "height": 2}
    ndvi = np.array([[0.1, 0.5, np.nan], [0.9, 0.0, 1.4]], dtype=np.float32)
    mask = np.array([[1, 1, 0], [1, 0, 1]], dtype=np.uint8)
    write_geotiff(processed / "ndvi.tif", ndvi, grid, nodata=None)
    write_geotiff(processed / "valid_mask.tif", mask, grid, nodata=0)
    (processed / "quality_report.json").write_text(json.dumps({
        "scene_quality_status": "valid",
        "calibration_status": "verified",
        "acquisition_date": "2023-03-26",
        "exclusion_counts": {
            "scl_class_distribution_target_grid": {"4": 4, "5": 2},
        },
    }), encoding="utf-8")
    (processed / "processing_metadata.json").write_text(json.dumps({
        "processing_version": "1.1.0",
        "calibration": {"B04": {"scale": 0.0001, "offset": 0.0}},
    }), encoding="utf-8")

    first = build_scene_histograms(
        "ds",
        "SCENE1",
        bins=DEFAULT_BINS,
        processed_root=tmp_path / "processed",
        raw_root=tmp_path / "raw",
        use_cache=True,
    )
    assert first["histogram_version"] == HISTOGRAM_VERSION
    assert first["ndvi"]["domain"] == list(NDVI_DOMAIN)
    assert first["ndvi"]["pixel_conservation_ok"] is True
    assert first["ndvi"]["masked_or_nodata_count"] == 2
    assert first["ndvi"]["out_of_range_count"] == 1
    assert first["ndvi"]["valid_pixel_count"] == 3
    assert first["scl"]["native_20m_mixed"] is False
    assert first["reflectance"]["available"] is False
    cache_path = processed / f"histograms_b{DEFAULT_BINS}.json"
    assert cache_path.is_file()

    second = build_scene_histograms(
        "ds",
        "SCENE1",
        bins=DEFAULT_BINS,
        processed_root=tmp_path / "processed",
        raw_root=tmp_path / "raw",
        use_cache=True,
    )
    assert second["cached"] is True
    assert second["ndvi"]["counts"] == first["ndvi"]["counts"]
    _ = raw


def test_quality_scl_counts_are_not_mixed_with_native_20m():
    payload = scl_distribution_from_counts({"4": 20148, "5": 66184, "0": 258}, total=87978)
    assert payload["native_20m_mixed"] is False
    assert payload["pixel_conservation_ok"] is False
    groups = {item["group"]: item for item in payload["groups"]}
    assert groups["vegetation"]["count"] == 20148
    assert groups["bare_soil"]["count"] == 66184
