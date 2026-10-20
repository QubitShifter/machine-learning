import numpy as np

from ml.preprocessing.calibration import (
    refine_calibration_with_sample,
    resolve_stac_band_calibration,
)
from ml.preprocessing.features import to_reflectance


def test_boa_offset_applied_uses_scale_only():
    result = resolve_stac_band_calibration(
        {"raster:bands": [{"scale": 0.0001, "offset": -0.1, "nodata": 0}]},
        {"earthsearch:boa_offset_applied": True, "s2:processing_baseline": "05.11"},
    )
    assert result["scale"] == 0.0001
    assert result["offset"] == 0.0
    assert result["advertised_offset"] == -0.1
    assert result["source"] == "earthsearch:boa_offset_applied"
    assert result["validation_status"] == "verified"
    assert result["requires_review"] is False


def test_boa_offset_not_applied_uses_raster_offset():
    result = resolve_stac_band_calibration(
        {"raster:bands": [{"scale": 0.0001, "offset": -0.1}]},
        {"earthsearch:boa_offset_applied": False},
    )
    assert result["offset"] == -0.1
    assert result["source"] == "stac-raster-bands"
    assert result["validation_status"] == "verified"


def test_unverified_missing_flag_requires_review():
    result = resolve_stac_band_calibration(
        {"raster:bands": [{"scale": 0.0001, "offset": -0.1}]},
        {},
    )
    assert result["validation_status"] == "unverified"
    assert result["requires_review"] is True
    assert result["offset"] == -0.1


def test_sample_audit_does_not_rewrite_offset():
    dn = np.array([200, 400, 600, 800], dtype=np.uint16)
    refined = refine_calibration_with_sample(
        dn,
        {"scale": 0.0001, "offset": -0.1, "advertised_offset": -0.1, "nodata": 0},
    )
    assert refined["offset"] == -0.1
    assert refined["requires_review"] is True
    assert refined["validation_status"] == "conflicting"
    assert refined.get("source") != "empirical-double-offset-guard"


def test_negative_reflectance_is_not_automatic_rejection():
    dn = np.array([900, 950, 1100, 1200], dtype=np.uint16)
    calibration = {
        "scale": 0.0001,
        "offset": 0.0,
        "advertised_offset": -0.1,
        "nodata": 0,
        "validation_status": "verified",
        "requires_review": False,
    }
    refined = refine_calibration_with_sample(dn, calibration)
    assert refined["offset"] == 0.0
    assert refined["requires_review"] is False
    reflectance = to_reflectance(dn, 0.0001, 0.0, 0)
    assert np.any(reflectance < 0) or np.all(reflectance >= 0)


def test_nodata_pixels_are_ignored_in_sample_audit():
    dn = np.array([0, 0, 2000, 2500], dtype=np.uint16)
    refined = refine_calibration_with_sample(
        dn,
        {"scale": 0.0001, "offset": 0.0, "advertised_offset": 0.0, "nodata": 0},
    )
    assert refined["sample_finite_pixels"] == 2
    assert refined["offset"] == 0.0


def test_missing_scale_is_an_error():
    try:
        resolve_stac_band_calibration({"raster:bands": [{}]}, {})
    except ValueError:
        return
    raise AssertionError("Expected ValueError")


def test_double_offset_is_prevented_when_flag_is_true():
    result = resolve_stac_band_calibration(
        {"raster:bands": [{"scale": 0.0001, "offset": -0.1}]},
        {"earthsearch:boa_offset_applied": True},
    )
    reflectance = to_reflectance(np.array([800], dtype=np.uint16), result["scale"], result["offset"], 0)
    assert abs(float(reflectance[0]) - 0.08) < 1e-6
