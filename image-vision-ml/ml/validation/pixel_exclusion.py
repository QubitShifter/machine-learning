"""Disjoint AOI pixel-exclusion accounting for Sentinel-2 scenes.

Counts are produced on the processed target grid. Native-resolution SCL
histograms are diagnostic only and must never be subtracted from target-grid
valid-pixel totals.

Each AOI pixel is assigned exactly one disjoint reason using explicit
precedence. Overlapping diagnostic counts are retained separately.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from ml.preprocessing.features import (
    NDVI_DENOMINATOR_EPS,
    VALID_SCL_CLASSES,
    calculate_ndvi,
    make_valid_mask,
    to_reflectance,
)
from ml.preprocessing.grid import deserialize_grid
from ml.preprocessing.raster import (
    BAND_FILES,
    OUTPUT_VALID_MASK,
    read_raster_metadata,
    reproject_categorical,
    reproject_continuous,
)


PIXEL_EXCLUSION_VERSION = "1.0.0"

SCL_CLASS_NAMES: dict[int, str] = {
    0: "scl_nodata",
    1: "scl_saturated_or_defective",
    2: "scl_dark_area",
    3: "scl_cloud_shadow",
    4: "scl_vegetation",
    5: "scl_bare_soil",
    6: "scl_water",
    7: "scl_unclassified",
    8: "scl_cloud_medium_probability",
    9: "scl_cloud_high_probability",
    10: "scl_thin_cirrus",
    11: "scl_snow_ice",
}

REASON_UNKNOWN_SCL = "scl_unknown_class"
REASON_RED_NIR = "optical_red_nir_nodata_or_nonfinite"
REASON_BLUE_GREEN = "optical_blue_green_nodata_or_nonfinite"
REASON_DENOMINATOR = "ndvi_denominator_undefined"
REASON_LAND_NO_NDVI = "land_without_finite_ndvi"
REASON_VALID = "valid_ndvi"

NDVI_CANDIDATES = ("ndvi.tif", "ndvi_corrected.tif")

# Non-land SCL classes are assigned before optical or NDVI failures.
SCL_EXCLUSION_ORDER = (0, 1, 2, 3, 6, 7, 8, 9, 10, 11)


def classify_pixel_exclusions(
    scl: np.ndarray,
    *,
    red: np.ndarray | None = None,
    nir: np.ndarray | None = None,
    blue: np.ndarray | None = None,
    green: np.ndarray | None = None,
    valid_scl_classes: tuple[int, ...] = VALID_SCL_CLASSES,
    ndvi_denominator_eps: float = NDVI_DENOMINATOR_EPS,
) -> dict[str, Any]:
    """Assign every pixel exactly one exclusion or validity reason.

    Precedence (first match wins):

    1. Non-valid SCL class, including nodata, snow/ice, water, cloud, and
       unclassified, using ``SCL_EXCLUSION_ORDER`` then any other unknown code.
    2. Valid SCL land (default 4, 5) with non-finite red or NIR.
    3. Valid SCL land with finite red/NIR but non-finite blue or green.
    4. Valid SCL land with finite optical bands but undefined NDVI denominator.
    5. Valid NDVI.

    Blue/green are part of ``make_valid_mask`` even though they are not in the
    NDVI formula. When optical bands are omitted, remaining land pixels are
    labelled ``land_without_finite_ndvi`` instead of the optical reasons.
    """
    scl_array = np.asarray(scl)
    if scl_array.ndim != 2:
        raise ValueError("SCL array must be 2-dimensional.")
    assigned = np.zeros(scl_array.shape, dtype=bool)
    disjoint: dict[str, int] = {}

    land = np.isin(scl_array, tuple(valid_scl_classes))
    for code in SCL_EXCLUSION_ORDER:
        if code in valid_scl_classes:
            continue
        mask = (scl_array == code) & ~assigned
        reason = SCL_CLASS_NAMES.get(code, f"scl_class_{code}")
        disjoint[reason] = int(mask.sum())
        assigned |= mask

    unknown = ~land & ~assigned
    disjoint[REASON_UNKNOWN_SCL] = int(unknown.sum())
    assigned |= unknown

    remaining_land = land & ~assigned
    have_optical = red is not None and nir is not None
    if have_optical:
        red_a = np.asarray(red)
        nir_a = np.asarray(nir)
        _require_same_shape(scl_array, red_a, "red")
        _require_same_shape(scl_array, nir_a, "nir")
        red_nir_ok = np.isfinite(red_a) & np.isfinite(nir_a)
        red_nir_bad = remaining_land & ~red_nir_ok
        disjoint[REASON_RED_NIR] = int(red_nir_bad.sum())
        assigned |= red_nir_bad
        remaining_land = land & ~assigned

        if blue is not None or green is not None:
            blue_ok = np.ones(scl_array.shape, dtype=bool)
            green_ok = np.ones(scl_array.shape, dtype=bool)
            if blue is not None:
                blue_a = np.asarray(blue)
                _require_same_shape(scl_array, blue_a, "blue")
                blue_ok = np.isfinite(blue_a)
            if green is not None:
                green_a = np.asarray(green)
                _require_same_shape(scl_array, green_a, "green")
                green_ok = np.isfinite(green_a)
            blue_green_bad = remaining_land & ~(blue_ok & green_ok)
            disjoint[REASON_BLUE_GREEN] = int(blue_green_bad.sum())
            assigned |= blue_green_bad
            remaining_land = land & ~assigned

        denominator = nir_a + red_a
        denom_ok = np.abs(denominator) > float(ndvi_denominator_eps)
        denom_bad = remaining_land & red_nir_ok & ~denom_ok
        disjoint[REASON_DENOMINATOR] = int(denom_bad.sum())
        assigned |= denom_bad
        remaining_land = land & ~assigned
    else:
        disjoint[REASON_RED_NIR] = 0
        disjoint[REASON_BLUE_GREEN] = 0
        disjoint[REASON_DENOMINATOR] = 0

    disjoint[REASON_VALID] = int(remaining_land.sum())
    assigned |= remaining_land
    unassigned = int((~assigned).sum())
    if unassigned:
        disjoint["unassigned"] = unassigned

    total = int(scl_array.size)
    valid = int(disjoint.get(REASON_VALID, 0))
    scl_rejected = sum(
        int(disjoint.get(SCL_CLASS_NAMES[code], 0))
        for code in SCL_CLASS_NAMES
        if code not in valid_scl_classes
    ) + int(disjoint.get(REASON_UNKNOWN_SCL, 0))
    other = (
        int(disjoint.get(REASON_RED_NIR, 0))
        + int(disjoint.get(REASON_BLUE_GREEN, 0))
        + int(disjoint.get(REASON_DENOMINATOR, 0))
        + int(disjoint.get(REASON_LAND_NO_NDVI, 0))
        + int(disjoint.get("unassigned", 0))
    )
    unique, counts = np.unique(scl_array, return_counts=True)
    scl_distribution = {str(int(value)): int(count) for value, count in zip(unique, counts)}
    conservation = valid + scl_rejected + other
    return {
        "pixel_exclusion_version": PIXEL_EXCLUSION_VERSION,
        "accounting_mode": "disjoint_target_grid",
        "total_aoi_pixels": total,
        "valid_pixels": valid,
        "excluded_pixels": total - valid,
        "disjoint_by_reason": {key: value for key, value in disjoint.items() if value},
        "disjoint_by_reason_including_zeros": disjoint,
        "scl_rejected_or_non_land": scl_rejected,
        "other_or_unclassified": other,
        "scl_class_distribution_target_grid": scl_distribution,
        "pixel_conservation_ok": conservation == total and unassigned == 0,
        "precedence": [
            "non_valid_scl_class",
            REASON_RED_NIR,
            REASON_BLUE_GREEN,
            REASON_DENOMINATOR,
            REASON_VALID,
        ],
    }


def residual_exclusion_counts(
    *,
    total: int,
    valid: int,
    scl_distribution: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Fallback residual accounting when target-grid rasters are unavailable.

    This mixed-resolution residual is not a scientific exclusion category.
    """
    scl_rejected = 0
    for key, count in (scl_distribution or {}).items():
        try:
            code = int(key)
        except (TypeError, ValueError):
            continue
        if code not in VALID_SCL_CLASSES:
            scl_rejected += int(count)
    excluded = max(int(total) - int(valid), 0)
    return {
        "pixel_exclusion_version": PIXEL_EXCLUSION_VERSION,
        "accounting_mode": "residual_unresolved_grid",
        "total_aoi_pixels": int(total),
        "valid_pixels": int(valid),
        "excluded_pixels": excluded,
        "disjoint_by_reason": {},
        "scl_rejected_or_non_land": scl_rejected,
        "other_or_unclassified": max(excluded - scl_rejected, 0),
        "scl_class_distribution_target_grid": {},
        "pixel_conservation_ok": False,
        "notes": (
            "Residual accounting mixes statistics with whatever SCL histogram "
            "was supplied. It is not a disjoint target-grid classification."
        ),
    }


def exclusion_report_for_scene(
    raw_dir: Path,
    processed_dir: Path,
    *,
    stats: dict[str, Any] | None = None,
    processing_meta: dict[str, Any] | None = None,
    native_scl_distribution: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Classify exclusions on the processed AOI grid when rasters exist."""
    native = native_scl_distribution or _native_scl_distribution(raw_dir)
    try:
        report = _classify_from_rasters(raw_dir, processed_dir, processing_meta)
    except Exception:
        report = None
    if report is None:
        total = 0
        valid = 0
        if stats:
            total = int(stats.get("total_pixels") or 0)
            valid = int(stats.get("valid_pixels") or 0)
        elif processing_meta:
            total = int(processing_meta.get("total_pixels") or 0)
            valid = int(processing_meta.get("valid_pixels") or 0)
        report = residual_exclusion_counts(
            total=total,
            valid=valid,
            scl_distribution=native,
        )
    report["native_scl_class_distribution"] = native
    report["native_scl_is_diagnostic_only"] = True
    return as_exclusion_counts(report)


def as_exclusion_counts(report: dict[str, Any]) -> dict[str, Any]:
    """Flatten a classification report into quality-report exclusion_counts."""
    return {
        "total_pixels": int(report.get("total_aoi_pixels") or 0),
        "valid_pixels": int(report.get("valid_pixels") or 0),
        "excluded_pixels": int(report.get("excluded_pixels") or 0),
        "scl_rejected_or_non_land": int(report.get("scl_rejected_or_non_land") or 0),
        "other_or_unclassified": int(report.get("other_or_unclassified") or 0),
        "disjoint_by_reason": dict(report.get("disjoint_by_reason") or {}),
        "accounting_mode": report.get("accounting_mode"),
        "pixel_conservation_ok": bool(report.get("pixel_conservation_ok")),
        "pixel_exclusion_version": report.get("pixel_exclusion_version"),
        "native_scl_class_distribution": dict(
            report.get("native_scl_class_distribution") or {}
        ),
        "native_scl_is_diagnostic_only": bool(
            report.get("native_scl_is_diagnostic_only", True)
        ),
        "stored_valid_mask_agrees": report.get("stored_valid_mask_agrees"),
        "notes": report.get("notes"),
        "scl_class_distribution_target_grid": dict(
            report.get("scl_class_distribution_target_grid") or {}
        ),
    }


def _classify_from_rasters(
    raw_dir: Path,
    processed_dir: Path,
    processing_meta: dict[str, Any] | None,
) -> dict[str, Any] | None:
    scl_path = raw_dir / BAND_FILES["SCL"]
    if not scl_path.is_file():
        return None
    reference = _reference_grid(processed_dir, processing_meta)
    if reference is None:
        return None
    try:
        scl, _grid = reproject_categorical(scl_path, reference)
    except Exception:
        return None
    reflectance = _load_reflectance(raw_dir, reference, processing_meta)
    if reflectance is None:
        report = classify_pixel_exclusions(scl)
        report["notes"] = (
            "Optical reflectance could not be reconstructed; land pixels "
            "without a non-land SCL class are counted as valid_ndvi."
        )
        return report
    report = classify_pixel_exclusions(
        scl,
        red=reflectance.get("B04"),
        nir=reflectance.get("B08"),
        blue=reflectance.get("B02"),
        green=reflectance.get("B03"),
    )
    mask_path = processed_dir / OUTPUT_VALID_MASK
    if mask_path.is_file() and reflectance.get("B04") is not None:
        try:
            import rasterio

            with rasterio.open(mask_path) as dataset:
                stored = dataset.read(1) > 0
            computed = make_valid_mask(
                scl,
                reflectance["B04"],
                reflectance.get("B03", reflectance["B04"]),
                reflectance.get("B02", reflectance["B04"]),
                reflectance["B08"],
            )
            ndvi = calculate_ndvi(
                reflectance["B04"],
                reflectance["B08"],
                computed,
            )
            report["stored_valid_mask_agrees"] = bool(
                stored.shape == computed.shape and np.array_equal(stored, computed)
            )
            report["stored_ndvi_finite_agrees"] = bool(
                int(np.isfinite(ndvi).sum()) == int(report["valid_pixels"])
            )
        except Exception:
            report["stored_valid_mask_agrees"] = None
    return report


def _load_reflectance(
    raw_dir: Path,
    reference: dict[str, Any],
    processing_meta: dict[str, Any] | None,
) -> dict[str, np.ndarray] | None:
    calibration = (processing_meta or {}).get("calibration") or {}
    reflectance: dict[str, np.ndarray] = {}
    for band in ("B02", "B03", "B04", "B08"):
        path = raw_dir / BAND_FILES[band]
        if not path.is_file():
            return None
        entry = calibration.get(band) or {}
        try:
            array, _grid = reproject_continuous(path, reference)
        except Exception:
            return None
        reflectance[band] = to_reflectance(
            array,
            float(entry["scale"]) if entry.get("scale") is not None else 1.0,
            float(entry["offset"]) if entry.get("offset") is not None else 0.0,
            entry.get("nodata", 0),
        )
    return reflectance


def _reference_grid(
    processed_dir: Path,
    processing_meta: dict[str, Any] | None,
) -> dict[str, Any] | None:
    payload = None
    settings = (processing_meta or {}).get("processing_settings") or {}
    if settings.get("target_grid"):
        payload = settings["target_grid"]
    elif processing_meta and processing_meta.get("raster"):
        payload = processing_meta["raster"]
    if payload and payload.get("crs") and payload.get("transform"):
        try:
            return deserialize_grid(payload)
        except Exception:
            pass
    for name in (OUTPUT_VALID_MASK, *NDVI_CANDIDATES):
        path = processed_dir / name
        if not path.is_file():
            continue
        try:
            return read_raster_metadata(path)
        except Exception:
            continue
    return None


def _native_scl_distribution(raw_dir: Path) -> dict[str, int]:
    path = raw_dir / BAND_FILES["SCL"]
    if not path.is_file():
        return {}
    try:
        import rasterio

        with rasterio.open(path) as dataset:
            array = dataset.read(1)
    except Exception:
        return {}
    values, counts = np.unique(array, return_counts=True)
    return {str(int(value)): int(count) for value, count in zip(values, counts)}


def _require_same_shape(reference: np.ndarray, array: np.ndarray, name: str) -> None:
    if array.shape != reference.shape:
        raise ValueError(f"{name} array must match the SCL shape.")
