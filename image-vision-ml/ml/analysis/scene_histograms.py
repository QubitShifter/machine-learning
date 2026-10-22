"""Mask-aware NDVI, reflectance, and SCL distributions for one scene.

Histograms are computed from processed GeoTIFFs on the AOI target grid.
Masked pixels are never counted as NDVI or reflectance zero. Invalid values
are not clamped into the scientific domain.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from ml.preprocessing.errors import MissingProcessedOutputError
from ml.preprocessing.raster import (
    BAND_FILES,
    OUTPUT_VALID_MASK,
    default_processed_root,
    default_raw_root,
    read_json,
    read_raster_metadata,
)
from ml.validation.pixel_exclusion import (
    NDVI_CANDIDATES,
    PIXEL_EXCLUSION_VERSION,
    SCL_CLASS_NAMES,
    _load_reflectance,
    _reference_grid,
)


HISTOGRAM_VERSION = "3.5.0"
DEFAULT_BINS = 45
REFLECTANCE_DISPLAY_BINS = 100
NDVI_DOMAIN = (-1.0, 1.0)
REFLECTANCE_DOMAIN = (0.0, 1.0)
REFLECTANCE_CHANNELS = ("B04", "B03", "B02")
AUTO_ZOOM_PADDING = 0.15
AUTO_ZOOM_FLOOR = 0.05
AUTO_ZOOM_CAP = 1.0
CHANNEL_NAMES = {
    "B04": "red",
    "B03": "green",
    "B02": "blue",
}

SCL_GROUPS = {
    "snow_ice": (11,),
    "cloud_and_shadow": (3, 8, 9, 10),
    "water": (6,),
    "vegetation": (4,),
    "bare_soil": (5,),
    "other": (0, 1, 2, 7),
}

SCL_DISPLAY_NAMES = {
    0: "No data",
    1: "Saturated or defective",
    2: "Dark area",
    3: "Cloud shadow",
    4: "Vegetation",
    5: "Bare soil",
    6: "Water",
    7: "Unclassified",
    8: "Cloud (medium probability)",
    9: "Cloud (high probability)",
    10: "Thin cirrus",
    11: "Snow / ice",
}


def equal_width_edges(low: float, high: float, bins: int) -> np.ndarray:
    if bins < 1:
        raise ValueError("bins must be >= 1.")
    if high <= low:
        raise ValueError("histogram domain high must exceed low.")
    return np.linspace(float(low), float(high), int(bins) + 1)


def summarize_values(values: np.ndarray) -> dict[str, float | None]:
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "standard_deviation": None,
            "minimum": None,
            "maximum": None,
            "p10": None,
            "p90": None,
            "p99": None,
        }
    return {
        "count": int(finite.size),
        "mean": float(finite.mean()),
        "median": float(np.median(finite)),
        "standard_deviation": float(finite.std()),
        "minimum": float(finite.min()),
        "maximum": float(finite.max()),
        "p10": float(np.percentile(finite, 10)),
        "p90": float(np.percentile(finite, 90)),
        "p99": float(np.percentile(finite, 99)),
    }


def auto_zoom_upper(
    p99_values: list[float | None] | tuple[float | None, ...],
    *,
    padding: float = AUTO_ZOOM_PADDING,
    floor: float = AUTO_ZOOM_FLOOR,
    cap: float = AUTO_ZOOM_CAP,
) -> float:
    """Upper X-axis bound from enabled-channel P99 values.

    Visible domain always starts at 0. The upper bound is
    ``min(cap, max(floor, max(P99) * (1 + padding)))``.
    """
    peaks = [
        float(value)
        for value in p99_values
        if value is not None and np.isfinite(value)
    ]
    if not peaks:
        return float(cap)
    return float(min(cap, max(floor, max(peaks) * (1.0 + float(padding)))))


def viewport_outside_fraction(
    histogram: list[dict[str, Any]],
    *,
    zoom_high: float,
    in_range_count: int,
) -> dict[str, Any]:
    """Count in-range samples whose bin lies entirely above the zoom window.

    Bins that straddle ``zoom_high`` stay in the viewport. Underlying counts
    are not merged or rebinned.
    """
    outside = 0
    for item in histogram:
        if float(item["edge_left"]) >= float(zoom_high):
            outside += int(item["count"])
    total = int(in_range_count)
    return {
        "outside_count": outside,
        "in_range_count": total,
        "percent": None if total == 0 else 100.0 * outside / total,
    }


def masked_histogram(
    values: np.ndarray,
    valid_mask: np.ndarray,
    *,
    low: float,
    high: float,
    bins: int,
) -> dict[str, Any]:
    """Histogram finite unmasked samples on [low, high]. Masked pixels are excluded."""
    array = np.asarray(values)
    mask = np.asarray(valid_mask, dtype=bool)
    if array.shape != mask.shape:
        raise ValueError("values and valid_mask must have the same shape.")
    total = int(array.size)
    masked = int((~mask).sum())
    unmasked = array[mask]
    finite = unmasked[np.isfinite(unmasked)]
    nonfinite_unmasked = int(unmasked.size - finite.size)
    in_range = finite[(finite >= low) & (finite <= high)]
    out_of_range = int(finite.size - in_range.size)
    edges = equal_width_edges(low, high, bins)
    counts, _ = np.histogram(in_range, bins=edges)
    counts_list = [int(value) for value in counts]
    bins_out = []
    for index, count in enumerate(counts_list):
        left = float(edges[index])
        right = float(edges[index + 1])
        bins_out.append({
            "index": index,
            "edge_left": left,
            "edge_right": right,
            "center": (left + right) / 2.0,
            "count": count,
            "percent_of_valid": (
                None if in_range.size == 0 else 100.0 * count / in_range.size
            ),
            "percent_of_total": None if total == 0 else 100.0 * count / total,
        })
    conservation = int(counts.sum()) + out_of_range + nonfinite_unmasked + masked
    stats = summarize_values(in_range)
    return {
        "domain": [float(low), float(high)],
        "bins": int(bins),
        "binning": "equal_width",
        "edges": [float(value) for value in edges],
        "counts": counts_list,
        "histogram": bins_out,
        "in_range_count": int(in_range.size),
        "out_of_range_count": out_of_range,
        "nonfinite_unmasked_count": nonfinite_unmasked,
        "masked_or_nodata_count": masked,
        "total_pixels": total,
        "valid_pixel_count": int(in_range.size),
        "valid_percentage": None if total == 0 else 100.0 * in_range.size / total,
        "histogrammed_count": int(in_range.size),
        "masked_count": masked,
        "nonfinite_count": nonfinite_unmasked,
        "out_of_domain_count": out_of_range,
        "pixel_conservation_ok": conservation == total,
        "clamped": False,
        "masked_treated_as_zero": False,
        "statistics": stats,
    }


def scl_distribution_from_counts(
    counts: dict[int, int] | dict[str, int],
    *,
    total: int | None = None,
    source: str = "target_grid_raster",
) -> dict[str, Any]:
    lookup: dict[int, int] = {}
    for key, value in (counts or {}).items():
        try:
            lookup[int(key)] = int(value)
        except (TypeError, ValueError):
            continue
    counted = sum(lookup.values())
    total_pixels = int(total) if total is not None else counted
    by_class = []
    for code in sorted(set(SCL_CLASS_NAMES) | set(lookup)):
        count = lookup.get(code, 0)
        by_class.append({
            "code": code,
            "name": SCL_DISPLAY_NAMES.get(code, SCL_CLASS_NAMES.get(code, f"class_{code}")),
            "count": count,
            "percent": None if total_pixels == 0 else 100.0 * count / total_pixels,
        })
    groups = []
    assigned: set[int] = set()
    for key, codes in SCL_GROUPS.items():
        count = sum(lookup.get(code, 0) for code in codes)
        assigned.update(codes)
        groups.append({
            "group": key,
            "codes": list(codes),
            "count": count,
            "percent": None if total_pixels == 0 else 100.0 * count / total_pixels,
        })
    other_codes = [code for code in lookup if code not in assigned]
    if other_codes:
        extra = sum(lookup[code] for code in other_codes)
        other = next(item for item in groups if item["group"] == "other")
        other["count"] += extra
        other["codes"] = list(other["codes"]) + other_codes
        other["percent"] = None if total_pixels == 0 else 100.0 * other["count"] / total_pixels
    return {
        "grid": "target_10m_aoi",
        "native_20m_mixed": False,
        "source": source,
        "total_pixels": total_pixels,
        "classes": by_class,
        "groups": groups,
        "pixel_conservation_ok": counted == total_pixels,
    }


def scl_distribution(scl: np.ndarray) -> dict[str, Any]:
    array = np.asarray(scl)
    unique, counts = np.unique(array, return_counts=True)
    lookup = {int(value): int(count) for value, count in zip(unique, counts)}
    return scl_distribution_from_counts(
        lookup,
        total=int(array.size),
        source="target_grid_raster",
    )


def scene_histogram_payload(
    *,
    ndvi: np.ndarray,
    valid_mask: np.ndarray,
    reflectance: dict[str, np.ndarray] | None = None,
    scl: np.ndarray | None = None,
    bins: int = DEFAULT_BINS,
    quality: dict[str, Any] | None = None,
    calibration: dict[str, Any] | None = None,
    processing_version: str | None = None,
    dataset_id: str | None = None,
    scene_id: str | None = None,
) -> dict[str, Any]:
    ndvi_hist = masked_histogram(
        ndvi, valid_mask, low=NDVI_DOMAIN[0], high=NDVI_DOMAIN[1], bins=bins
    )
    channels = {}
    if reflectance:
        for band in REFLECTANCE_CHANNELS:
            array = reflectance.get(band)
            if array is None:
                continue
            channels[CHANNEL_NAMES[band]] = {
                "band": band,
                "unit": "surface_reflectance",
                "is_display_rgb": False,
                **masked_histogram(
                    array,
                    valid_mask,
                    low=REFLECTANCE_DOMAIN[0],
                    high=REFLECTANCE_DOMAIN[1],
                    bins=bins,
                ),
                "calibration": (calibration or {}).get(band),
            }
    scl_payload = None if scl is None else scl_distribution(scl)
    quality = quality or {}
    scene_quality = quality.get("scene_quality_status") or quality.get("quality_status")
    rejected = str(scene_quality or "").lower() in {"rejected", "requires_review"}
    warnings = []
    if rejected:
        warnings.append(
            "Scene quality is not validated. Distributions are shown for inspection "
            "and must not be treated as validated agricultural science."
        )
        warnings.extend(list(quality.get("scene_quality_reasons") or quality.get("reasons") or []))
    return {
        "dataset_id": dataset_id,
        "scene_id": scene_id,
        "histogram_version": HISTOGRAM_VERSION,
        "pixel_exclusion_version": PIXEL_EXCLUSION_VERSION,
        "processing_version": processing_version,
        "acquisition_date": quality.get("acquisition_date"),
        "scene_quality_status": scene_quality,
        "calibration_status": quality.get("calibration_status")
        or ((quality.get("calibration") or {}).get("validation_status")),
        "scientific_use": "rejected_or_review" if rejected else "validated_or_unknown",
        "warnings": warnings,
        "ndvi": {
            "unit": "NDVI",
            "formula": "(NIR-RED)/(NIR+RED)",
            "mask": "processed valid_mask.tif; masked pixels excluded, never counted as 0",
            **ndvi_hist,
        },
        "reflectance": {
            "unit": "BOA surface reflectance (dimensionless)",
            "domain": list(REFLECTANCE_DOMAIN),
            "is_display_rgb": False,
            "note": "Calibrated B02/B03/B04 reflectance, not 8-bit tone-mapped preview PNG.",
            "channels": channels,
            "available": bool(channels),
            "band_count_agreement": _band_count_agreement(channels),
        },
        "scl": scl_payload,
        "source": {
            "kind": "sentinel-2_l2a_processed",
            "spatial_support": "AOI target grid, 10 m",
        },
    }


def build_scene_histograms(
    dataset_id: str,
    scene_id: str,
    *,
    bins: int = DEFAULT_BINS,
    processed_root: Path | None = None,
    raw_root: Path | None = None,
    use_cache: bool = True,
) -> dict[str, Any]:
    processed_dir = (processed_root or default_processed_root()) / dataset_id / "scenes" / scene_id
    raw_root = raw_root or default_raw_root()
    raw_dir = raw_root / dataset_id / "scenes" / scene_id
    if not raw_dir.is_dir():
        raw_dir = raw_root / scene_id
    ndvi_path = _ndvi_path(processed_dir)
    mask_path = processed_dir / OUTPUT_VALID_MASK
    if ndvi_path is None or not mask_path.is_file():
        raise MissingProcessedOutputError(
            "Processed NDVI raster or valid mask is not available for histograms."
        )
    bins = int(bins)
    if bins < 8 or bins > 200:
        raise ValueError("bins must be between 8 and 200.")
    fingerprints = {
        "ndvi": _file_fingerprint(ndvi_path),
        "valid_mask": _file_fingerprint(mask_path),
        "quality": _file_fingerprint(processed_dir / "quality_report.json"),
        "metadata": _file_fingerprint(processed_dir / "processing_metadata.json"),
        "bins": bins,
        "histogram_version": HISTOGRAM_VERSION,
    }
    for band in (*REFLECTANCE_CHANNELS, "B08", "SCL"):
        fingerprints[band] = _file_fingerprint(raw_dir / BAND_FILES[band])
    cache_path = processed_dir / f"histograms_b{bins}.json"
    if use_cache and cache_path.is_file():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cached = None
        if cached and cached.get("source_fingerprints") == fingerprints:
            cached = dict(cached)
            cached["cached"] = True
            return cached

    ndvi = _read_array(ndvi_path)
    mask = _read_array(mask_path) > 0
    if ndvi.shape != mask.shape:
        raise MissingProcessedOutputError(
            "NDVI raster and valid mask are not on the same grid."
        )
    quality = _read_json_if_present(processed_dir / "quality_report.json")
    meta = _read_json_if_present(processed_dir / "processing_metadata.json")
    calibration = (meta.get("calibration") or {}).get("bands") or meta.get("calibration") or {}
    reflectance = None
    scl = None
    try:
        reference = _reference_grid(processed_dir, meta) or read_raster_metadata(mask_path)
        reflectance = _load_reflectance(raw_dir, reference, meta)
        scl_path = raw_dir / BAND_FILES["SCL"]
        if scl_path.is_file():
            from ml.preprocessing.raster import reproject_categorical

            scl, _grid = reproject_categorical(scl_path, reference)
    except Exception:
        reflectance = None
        scl = None

    payload = scene_histogram_payload(
        ndvi=ndvi,
        valid_mask=mask,
        reflectance=reflectance,
        scl=scl,
        bins=bins,
        quality=quality,
        calibration=calibration,
        processing_version=meta.get("processing_version"),
        dataset_id=dataset_id,
        scene_id=scene_id,
    )
    if payload.get("scl") is None:
        payload["scl"] = _scl_from_quality(quality, total=int(ndvi.size))
    payload["source_fingerprints"] = fingerprints
    payload["cached"] = False
    if use_cache:
        _write_json(cache_path, payload)
        payload["cached"] = True
        payload["cache_path"] = cache_path.name
    return payload


def _ndvi_path(processed_dir: Path) -> Path | None:
    for name in NDVI_CANDIDATES:
        path = processed_dir / name
        if path.is_file():
            return path
    return None


def _read_array(path: Path) -> np.ndarray:
    import rasterio

    with rasterio.open(path) as dataset:
        return dataset.read(1)


def _file_fingerprint(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"name": path.name, "present": False}
    stat = path.stat()
    digest = hashlib.sha256(f"{path.name}:{stat.st_size}:{stat.st_mtime_ns}".encode()).hexdigest()[:16]
    return {
        "name": path.name,
        "present": True,
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "key": digest,
    }


def _read_json_if_present(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return read_json(path)
    except Exception:
        return {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temporary.replace(path)


def _band_count_agreement(channels: dict[str, Any]) -> dict[str, Any]:
    """Report legitimate per-band histogrammed-count differences.

    The valid_mask is shared. A band may still have extra non-finite or
    out-of-domain samples after that mask, so in-range counts are not forced
    equal.
    """
    names = list(channels)
    in_range = {name: int(channels[name].get("in_range_count") or 0) for name in names}
    totals = {name: int(channels[name].get("total_pixels") or 0) for name in names}
    spread = (max(in_range.values()) - min(in_range.values())) if in_range else 0
    return {
        "total_pixels_match": len(set(totals.values())) <= 1,
        "in_range_spread": spread,
        "in_range_by_channel": in_range,
        "forced_equal": False,
        "note": (
            "Per-band histogrammed counts may differ by a few pixels when a "
            "band is non-finite or out of domain after the shared valid_mask. "
            "Totals are not forced equal."
        ),
    }


def _scl_from_quality(quality: dict[str, Any], *, total: int) -> dict[str, Any] | None:
    exclusion = quality.get("exclusion_counts") or {}
    counts = (
        exclusion.get("scl_class_distribution_target_grid")
        or quality.get("scl_class_distribution_target_grid")
    )
    if not counts:
        return None
    return scl_distribution_from_counts(
        counts,
        total=total,
        source="quality_report_target_grid",
    )
