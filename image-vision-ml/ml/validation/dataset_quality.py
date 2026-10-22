"""Scene-level and dataset-level quality gates for satellite archives."""

from __future__ import annotations

import csv
import logging
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from ml.ingestion.config import DEFAULT_QUALITY, DEFAULT_READINESS
from ml.ingestion.manifest import (
    read_manifest,
    scene_records,
    write_json_atomic,
)
from ml.validation.calibration_audit import audit_dataset_calibration
from ml.validation.coverage import build_monthly_coverage
from ml.validation.modeling_readiness import assess_task_readiness
from ml.validation.pixel_exclusion import exclusion_report_for_scene
from ml.preprocessing.calibration import (
    STATUS_CONFLICTING,
    STATUS_MISSING,
    STATUS_UNVERIFIED,
    STATUS_VERIFIED,
    summarize_calibration_status,
)
from ml.preprocessing.errors import DatasetNotFoundError, InvalidMetadataError
from ml.preprocessing.grid import validate_dataset_grid
from ml.preprocessing.raster import (
    BAND_FILES,
    default_processed_root,
    default_raw_root,
    read_json,
)


logger = logging.getLogger(__name__)

STATUS_VALID = "valid"
STATUS_WARNING = "warning"
STATUS_REJECTED = "rejected"
STATUS_REVIEW = "requires_review"

SCL_CLOUD_SHADOW = {3, 8, 9, 10}
GROWING_SEASON_MONTHS = {4, 5, 6, 7, 8, 9}


def evaluate_scene_quality(
    scene: dict[str, Any],
    *,
    quality: dict[str, Any] | None = None,
    processed: dict[str, Any] | None = None,
    calibration: dict[str, Any] | None = None,
    grid_status: dict[str, Any] | None = None,
    missing_assets: list[str] | None = None,
    scl_distribution: dict[str, int] | None = None,
    reflectance_ranges: dict[str, dict[str, float | None]] | None = None,
    exclusion_counts: dict[str, int] | None = None,
    processing_error: str | None = None,
) -> dict[str, Any]:
    """Classify one scene using configurable quality gates.

    Geometric footprint overlap and actual raster coverage are stored
    separately. A warning is not treated as a failure unless the
    configured policy says so.
    """
    policy = {**DEFAULT_QUALITY, **(quality or {})}
    reasons: list[str] = []
    status = STATUS_VALID

    missing = list(missing_assets or [])
    if missing:
        status = STATUS_REJECTED
        reasons.append("missing_assets:" + ",".join(missing))

    if processing_error:
        status = STATUS_REJECTED
        reasons.append("processing_error")

    grid_aligned = True
    if grid_status:
        grid_aligned = bool(grid_status.get("aligned", True))
        if not grid_aligned:
            status = STATUS_REJECTED
            reasons.append("crs_or_grid_mismatch")

    calibration_summary = summarize_calibration_status(calibration)
    if policy.get("calibration_policy") == "verified_only":
        if calibration_summary["validation_status"] in {
            STATUS_UNVERIFIED,
            STATUS_CONFLICTING,
            STATUS_MISSING,
        } or calibration_summary["requires_review"]:
            if status != STATUS_REJECTED:
                status = STATUS_REVIEW
            reasons.append("calibration_" + str(calibration_summary["validation_status"]))

    footprint = _as_float(
        scene.get("footprint_overlap_pct", scene.get("aoi_coverage"))
    )
    raster_coverage = _as_float(
        (processed or {}).get("valid_percentage", scene.get("valid_percentage"))
    )
    min_aoi = float(policy["min_aoi_coverage_pct"])
    if footprint is not None and footprint < min_aoi:
        status = STATUS_REJECTED
        reasons.append("geometric_coverage_below_threshold")

    min_valid = float(policy["min_valid_ndvi_pct"])
    warning_valid = float(policy.get("warning_valid_ndvi_pct", min_valid))
    if raster_coverage is not None:
        if raster_coverage < min_valid:
            status = STATUS_REJECTED
            reasons.append("valid_ndvi_below_threshold")
        elif raster_coverage < warning_valid and status == STATUS_VALID:
            status = STATUS_WARNING
            reasons.append("valid_ndvi_warning_threshold")

    ndvi = (processed or {}).get("ndvi") or scene.get("ndvi") or {}
    cloud_shadow = None
    if scl_distribution:
        total = sum(int(value) for value in scl_distribution.values())
        cloudy = sum(
            int(scl_distribution.get(str(code), scl_distribution.get(code, 0)))
            for code in SCL_CLOUD_SHADOW
        )
        cloud_shadow = round(100.0 * cloudy / total, 2) if total else 0.0

    calibration_status = calibration_summary.get("validation_status")
    report = {
        "scene_id": scene.get("scene_id"),
        "acquisition_date": scene.get("acquisition_date"),
        "satellite_platform": scene.get("platform") or (scene.get("properties") or {}).get("platform"),
        "mgrs_tile": scene.get("mgrs_tile") or (scene.get("properties") or {}).get("mgrs"),
        "quality_status": status,
        "scene_quality_status": status,
        "scene_quality_reasons": list(reasons),
        "calibration_status": calibration_status,
        "reasons": reasons,
        "geometric_footprint_overlap_pct": footprint,
        "bbox_overlap_pct": _as_float(scene.get("bbox_overlap_pct")),
        "actual_aoi_coverage_pct": raster_coverage,
        "valid_ndvi_pct": raster_coverage,
        "valid_pixels": (processed or {}).get("valid_pixels", scene.get("valid_pixels")),
        "total_aoi_pixels": (processed or {}).get("total_pixels", scene.get("total_pixels")),
        "scl_class_distribution": scl_distribution or {},
        "cloud_shadow_fraction_pct": cloud_shadow,
        "reflectance_range_by_band": reflectance_ranges or {},
        "ndvi_minimum": ndvi.get("minimum"),
        "ndvi_maximum": ndvi.get("maximum"),
        "ndvi_mean": ndvi.get("mean"),
        "ndvi_median": ndvi.get("median"),
        "ndvi_standard_deviation": ndvi.get("standard_deviation"),
        "grid_aligned": grid_aligned,
        "calibration": calibration_summary,
        "missing_assets": missing,
        "processing_error": processing_error,
        "exclusion_counts": exclusion_counts or {},
        "partial_coverage": bool(
            footprint is not None and footprint < 99.0
        ),
    }
    return report


def evaluate_dataset_quality(
    dataset_id: str,
    *,
    raw_root: Path | None = None,
    processed_root: Path | None = None,
    quality: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build scene reports, dataset totals, and a training-readiness assessment."""
    raw = (raw_root or default_raw_root()) / dataset_id
    processed = (processed_root or default_processed_root()) / dataset_id
    raw_manifest_path = raw / "manifest.json"
    if not raw_manifest_path.is_file():
        raise DatasetNotFoundError(f"Unknown satellite dataset: {dataset_id}")
    raw_manifest = read_manifest(raw_manifest_path)
    processed_manifest = (
        read_manifest(processed / "manifest.json")
        if (processed / "manifest.json").is_file()
        else {"scenes": {}, "target_grid": None}
    )
    policy = {
        **DEFAULT_QUALITY,
        **((config or {}).get("quality") or {}),
        **(quality or {}),
    }
    period = raw_manifest.get("period") or (config or {}).get("period") or {}
    grid_report = validate_dataset_grid(
        dataset_id,
        processed_root=processed.parent,
        expected=processed_manifest.get("target_grid"),
    )

    scene_reports = []
    for record in scene_records(raw_manifest):
        scene_id = record["scene_id"]
        processed_record = (processed_manifest.get("scenes") or {}).get(scene_id, {})
        acquired = record.get("status") in {"downloaded", "processed", "failed"} or (
            processed_record.get("status") in {"processed", "failed"}
        )
        if not acquired:
            continue
        raw_dir = raw / "scenes" / scene_id
        processed_dir = processed / "scenes" / scene_id
        stats = _read_optional_json(processed_dir / "statistics.json")
        processing_meta = _read_optional_json(
            processed_dir / "processing_metadata.json"
        )
        calibration = _read_optional_json(raw_dir / "calibration.json")
        calibration = _merge_process_calibration(calibration, processing_meta)
        missing = _missing_raw_assets(raw_dir)
        native_scl = _scl_distribution(raw_dir)
        exclusion = exclusion_report_for_scene(
            raw_dir,
            processed_dir,
            stats=stats,
            processing_meta=processing_meta,
            native_scl_distribution=native_scl,
        )
        scl_distribution = (
            exclusion.get("scl_class_distribution_target_grid") or native_scl
        )
        reflectance_ranges = _reflectance_ranges(processing_meta)
        merged_processed = dict(processed_record)
        if stats:
            merged_processed.setdefault("valid_pixels", stats.get("valid_pixels"))
            merged_processed.setdefault("total_pixels", stats.get("total_pixels"))
            merged_processed.setdefault("valid_percentage", stats.get("valid_percentage"))
            merged_processed.setdefault("ndvi", {
                "minimum": stats.get("minimum"),
                "maximum": stats.get("maximum"),
                "mean": stats.get("mean"),
                "median": stats.get("median"),
                "standard_deviation": stats.get("standard_deviation"),
            })
        scene_reports.append(
            evaluate_scene_quality(
                {**record, **merged_processed},
                quality=policy,
                processed=merged_processed,
                calibration=calibration,
                grid_status=_scene_grid_status(scene_id, grid_report),
                missing_assets=missing,
                scl_distribution=scl_distribution,
                reflectance_ranges=reflectance_ranges,
                exclusion_counts=exclusion,
                processing_error=processed_record.get("error") or record.get("error"),
            )
        )

    discovered = len(scene_records(raw_manifest))
    geometrically_eligible = sum(
        1 for item in scene_records(raw_manifest)
        if (
            item.get("footprint_overlap_pct")
            if item.get("footprint_overlap_pct") is not None
            else item.get("aoi_coverage") or 0
        ) >= float(policy["min_aoi_coverage_pct"])
    )
    downloaded = sum(
        1 for item in scene_records(raw_manifest)
        if item.get("status") in {"downloaded", "processed"}
    )
    processed_count = sum(
        1 for item in scene_records(processed_manifest)
        if item.get("status") == "processed"
    )
    status_counts = Counter(item["quality_status"] for item in scene_reports)
    valid_reports = [item for item in scene_reports if item["quality_status"] == STATUS_VALID]
    coverages = [
        item["actual_aoi_coverage_pct"]
        for item in scene_reports
        if item.get("actual_aoi_coverage_pct") is not None
    ]
    monthly_counts = _counts_by_month(valid_reports)
    yearly_counts = _counts_by_year(valid_reports)
    missing_months = _period_missing_months(
        period.get("start"),
        period.get("end"),
        set(monthly_counts),
    )
    gaps = _temporal_gaps(valid_reports)
    duplicates = _duplicate_observations(scene_reports)

    summary = {
        "dataset_id": dataset_id,
        "period": period,
        "total_discovered_scenes": discovered,
        "geometrically_eligible_scenes": geometrically_eligible,
        "downloaded_scenes": downloaded,
        "processed_scenes": processed_count,
        "validated_scenes": status_counts.get(STATUS_VALID, 0),
        "warning_scenes": status_counts.get(STATUS_WARNING, 0),
        "rejected_scenes": status_counts.get(STATUS_REJECTED, 0),
        "requires_review_scenes": status_counts.get(STATUS_REVIEW, 0),
        "missing_months": missing_months,
        "observation_count_per_month": monthly_counts,
        "observation_count_per_year": yearly_counts,
        "mean_valid_pixel_coverage": _mean(coverages),
        "median_valid_pixel_coverage": _median(coverages),
        "spatial_grid_consistency": grid_report,
        "calibration_failure_count": sum(
            1 for item in scene_reports
            if item.get("calibration", {}).get("validation_status")
            in {STATUS_CONFLICTING, STATUS_MISSING}
            or item.get("calibration", {}).get("requires_review")
        ),
        "processing_failure_count": sum(
            1 for item in scene_records(processed_manifest)
            if item.get("status") == "failed"
        ),
        "temporal_gaps": gaps,
        "duplicate_observations": duplicates,
        "quality_policy": policy,
        "aggregation_notes": (
            "Monthly and yearly NDVI summaries weight each scene equally. "
            "They are not pixel-area-weighted monthly climatologies."
        ),
    }
    readiness = assess_training_readiness(summary, scene_reports, config=config)
    catalog_records = scene_records(raw_manifest)
    catalog_known = (raw / "discovered.json").is_file() or any(
        item.get("status") == "discovered" for item in catalog_records
    )
    coverage = build_monthly_coverage(
        period=period,
        catalog_records=catalog_records if catalog_known else None,
        quality_scenes=scene_reports,
        catalog_known=catalog_known,
    )
    calibration_audit = audit_dataset_calibration(
        dataset_id,
        raw_dir=raw,
        processed_dir=processed,
    )
    integration_metrics = _integration_metrics(dataset_id, processed.parent)
    task_readiness = assess_task_readiness(
        quality={
            **readiness,
            "coverage": coverage,
            "ground_truth_soil_moisture_available": False,
        },
        integration_metrics=integration_metrics,
        thresholds=(config or {}).get("readiness") or DEFAULT_READINESS,
    )
    payload = {
        "dataset_id": dataset_id,
        "scenes": scene_reports,
        "dataset": summary,
        "training_readiness": readiness,
        "coverage": coverage,
        "calibration_audit": calibration_audit,
        "task_readiness": task_readiness,
    }
    return payload


def write_quality_outputs(
    payload: dict[str, Any],
    output_dir: Path,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "dataset_quality.json"
    csv_path = output_dir / "dataset_quality.csv"
    readiness_path = output_dir / "training_readiness.json"
    write_json_atomic(json_path, payload)
    write_json_atomic(readiness_path, payload["training_readiness"])
    _write_scene_csv(csv_path, payload["scenes"])
    extras = {}
    if payload.get("coverage") is not None:
        coverage_path = output_dir / "coverage.json"
        write_json_atomic(coverage_path, payload["coverage"])
        extras["coverage"] = coverage_path.name
    if payload.get("calibration_audit") is not None:
        audit_path = output_dir / "calibration_audit.json"
        write_json_atomic(audit_path, payload["calibration_audit"])
        extras["calibration_audit"] = audit_path.name
    if payload.get("task_readiness") is not None:
        tasks_path = output_dir / "task_readiness.json"
        write_json_atomic(tasks_path, payload["task_readiness"])
        extras["task_readiness"] = tasks_path.name
    return {
        "json": json_path.name,
        "csv": csv_path.name,
        "training_readiness": readiness_path.name,
        **extras,
    }


def assess_training_readiness(
    summary: dict[str, Any],
    scenes: list[dict[str, Any]],
    *,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Describe readiness for analysis, vegetation research, and soil forecasting.

    A three-year NDVI archive is not sufficient for supervised soil-moisture
    forecasting. Weather and in-situ labels are still absent.
    """
    validated = int(summary.get("validated_scenes") or 0)
    years = sorted(summary.get("observation_count_per_year") or {})
    missing_months = list(summary.get("missing_months") or [])
    gaps = list(summary.get("temporal_gaps") or [])
    longest_gap = max((item.get("days") or 0) for item in gaps) if gaps else 0
    grid_ok = bool((summary.get("spatial_grid_consistency") or {}).get("consistent", False))
    calibration_failures = int(summary.get("calibration_failure_count") or 0)
    low_coverage = [
        item["scene_id"]
        for item in scenes
        if (item.get("actual_aoi_coverage_pct") or 0) < 70
    ]
    bands = ((config or {}).get("processing") or {}).get("bands") or [
        "blue", "green", "red", "nir", "scl"
    ]

    historical = "not_ready"
    vegetation = "not_ready"
    soil = "not_ready"
    if validated >= 3 and years and grid_ok:
        historical = "suitable_for_exploratory_analysis"
    elif validated > 0:
        historical = "limited"
    if validated >= 6 and len(years) >= 2 and grid_ok:
        vegetation = "limited"
    if validated >= 12 and len(years) >= 3 and longest_gap <= 90:
        vegetation = "suitable_for_exploratory_analysis"

    overall = historical
    limitations = [
        "NDVI describes canopy greenness, not soil moisture.",
        "Meteorological covariates are not integrated.",
        "No in-situ soil moisture labels are available.",
        "Scene-level monthly means weight observations equally, not pixels.",
    ]
    if missing_months:
        limitations.append(
            f"{len(missing_months)} months in the configured period have no validated observation."
        )
    if calibration_failures:
        limitations.append(
            f"{calibration_failures} scene(s) have unverified or conflicting calibration."
        )
    if not grid_ok:
        limitations.append("Processed rasters are not all on one canonical grid.")
        overall = "not_ready"
        historical = "not_ready"

    return {
        "overall": overall,
        "historical_satellite_analysis": historical,
        "vegetation_forecasting_research": vegetation,
        "supervised_soil_forecasting": soil,
        "validated_observations": validated,
        "years_represented": years,
        "year_count": len(years),
        "temporal_sampling_completeness_pct": _completeness(
            summary.get("period") or {},
            summary.get("observation_count_per_month") or {},
        ),
        "longest_observation_gap_days": longest_gap,
        "spatial_grid_consistency": grid_ok,
        "calibration_consistency": calibration_failures == 0,
        "ndvi_validity": validated > 0,
        "missing_months": missing_months,
        "low_coverage_periods": low_coverage,
        "available_spectral_bands": list(bands),
        "known_biases_and_limitations": limitations,
    }


def _missing_raw_assets(raw_dir: Path) -> list[str]:
    if not raw_dir.is_dir():
        return list(BAND_FILES.values()) + ["metadata.json"]
    missing = [
        filename for filename in BAND_FILES.values()
        if not (raw_dir / filename).is_file()
    ]
    if not (raw_dir / "metadata.json").is_file():
        missing.append("metadata.json")
    return missing


def _scl_distribution(raw_dir: Path) -> dict[str, int]:
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


def _merge_process_calibration(
    calibration: dict[str, Any] | None,
    processing_meta: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not processing_meta:
        return calibration
    processed_bands = (processing_meta.get("calibration") or {})
    if not processed_bands:
        return calibration
    merged = dict(calibration or {})
    bands = dict(merged.get("bands") or {})
    review = bool(merged.get("requires_review"))
    statuses = []
    for band, entry in processed_bands.items():
        if str(band).upper() == "SCL" or not isinstance(entry, dict):
            continue
        current = dict(bands.get(band) or {})
        current.update({
            "scale": entry.get("scale", current.get("scale")),
            "offset": entry.get("offset", current.get("offset")),
            "source": entry.get("source", current.get("source")),
            "negative_fraction": entry.get("negative_fraction"),
        })
        if entry.get("requires_review") or entry.get("discrepancy"):
            current["requires_review"] = True
            current["validation_status"] = entry.get(
                "validation_status", STATUS_CONFLICTING
            )
            review = True
        bands[band] = current
        if current.get("validation_status"):
            statuses.append(str(current["validation_status"]))
    merged["bands"] = bands
    merged["requires_review"] = review
    if review and merged.get("validation_status") == STATUS_VERIFIED:
        merged["validation_status"] = STATUS_CONFLICTING
    elif statuses:
        if STATUS_CONFLICTING in statuses:
            merged["validation_status"] = STATUS_CONFLICTING
        elif STATUS_UNVERIFIED in statuses:
            merged["validation_status"] = STATUS_UNVERIFIED
    return merged


def _reflectance_ranges(processing_meta: dict[str, Any] | None) -> dict[str, dict[str, float | None]]:
    if not processing_meta:
        return {}
    calibration = processing_meta.get("calibration") or {}
    ranges = {}
    for band, entry in calibration.items():
        if not isinstance(entry, dict):
            continue
        ranges[band] = {
            "scale": entry.get("scale"),
            "offset": entry.get("offset"),
            "negative_fraction": entry.get("negative_fraction"),
        }
    return ranges


def _exclusion_counts(
    stats: dict[str, Any] | None,
    processing_meta: dict[str, Any] | None,
    scl_distribution: dict[str, int],
) -> dict[str, Any]:
    """Deprecated residual helper; prefer exclusion_report_for_scene."""
    from ml.validation.pixel_exclusion import residual_exclusion_counts

    total = 0
    valid = 0
    if stats:
        total = int(stats.get("total_pixels") or 0)
        valid = int(stats.get("valid_pixels") or 0)
    elif processing_meta:
        total = int(processing_meta.get("total_pixels") or 0)
        valid = int(processing_meta.get("valid_pixels") or 0)
    return residual_exclusion_counts(
        total=total,
        valid=valid,
        scl_distribution=scl_distribution,
    )


def _scene_grid_status(scene_id: str, grid_report: dict[str, Any]) -> dict[str, Any]:
    mismatches = {
        item["scene_id"]: item
        for item in grid_report.get("mismatches") or []
    }
    if scene_id in mismatches:
        return {"aligned": False, **mismatches[scene_id]}
    inspected = scene_id in set(grid_report.get("inspected_scenes") or [])
    return {"aligned": True if not inspected else True, "inspected": inspected}


def _counts_by_month(reports: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for item in reports:
        date = str(item.get("acquisition_date") or "")[:7]
        if len(date) == 7:
            counts[date] += 1
    return dict(sorted(counts.items()))


def _counts_by_year(reports: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for item in reports:
        date = str(item.get("acquisition_date") or "")[:4]
        if len(date) == 4:
            counts[date] += 1
    return dict(sorted(counts.items()))


def _period_missing_months(
    start: Any,
    end: Any,
    observed: set[str],
) -> list[str]:
    if not start or not end:
        return []
    try:
        cursor = datetime.fromisoformat(str(start)[:7] + "-01")
        last = datetime.fromisoformat(str(end)[:7] + "-01")
    except ValueError:
        return []
    missing = []
    while cursor <= last:
        key = f"{cursor.year:04d}-{cursor.month:02d}"
        if key not in observed:
            missing.append(key)
        month = cursor.month + 1
        cursor = datetime(cursor.year + 1, 1, 1) if month == 13 else datetime(cursor.year, month, 1)
    return missing


def _temporal_gaps(reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dates = sorted(
        {
            str(item.get("acquisition_date") or "")[:10]
            for item in reports
            if item.get("acquisition_date")
        }
    )
    gaps = []
    for earlier, later in zip(dates, dates[1:]):
        try:
            delta = (
                datetime.fromisoformat(later) - datetime.fromisoformat(earlier)
            ).days
        except ValueError:
            continue
        if delta > 1:
            gaps.append({"from_date": earlier, "to_date": later, "days": delta})
    return gaps


def _duplicate_observations(reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_date: dict[str, list[str]] = defaultdict(list)
    for item in reports:
        date = str(item.get("acquisition_date") or "")[:10]
        if date:
            by_date[date].append(str(item.get("scene_id")))
    return [
        {"date": date, "scene_ids": ids}
        for date, ids in sorted(by_date.items())
        if len(ids) > 1
    ]


def _write_scene_csv(path: Path, scenes: list[dict[str, Any]]) -> None:
    fieldnames = [
        "scene_id",
        "acquisition_date",
        "quality_status",
        "scene_quality_status",
        "geometric_footprint_overlap_pct",
        "actual_aoi_coverage_pct",
        "valid_ndvi_pct",
        "ndvi_mean",
        "grid_aligned",
        "calibration_status",
        "scene_quality_reasons",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for item in scenes:
            writer.writerow({
                "scene_id": item.get("scene_id"),
                "acquisition_date": item.get("acquisition_date"),
                "quality_status": item.get("quality_status"),
                "scene_quality_status": item.get("scene_quality_status")
                or item.get("quality_status"),
                "geometric_footprint_overlap_pct": item.get("geometric_footprint_overlap_pct"),
                "actual_aoi_coverage_pct": item.get("actual_aoi_coverage_pct"),
                "valid_ndvi_pct": item.get("valid_ndvi_pct"),
                "ndvi_mean": item.get("ndvi_mean"),
                "grid_aligned": item.get("grid_aligned"),
                "calibration_status": item.get("calibration_status")
                or (item.get("calibration") or {}).get("validation_status"),
                "scene_quality_reasons": ";".join(item.get("scene_quality_reasons") or item.get("reasons") or []),
            })


def _integration_metrics(dataset_id: str, processed_root: Path) -> dict[str, Any] | None:
    # processed_root is data/processed/satellite; integration lives beside it.
    path = processed_root.parent / "integration" / dataset_id / "integration_quality.json"
    payload = _read_optional_json(path)
    if not payload:
        return None
    return {
        "complete_window_count": int(
            payload.get("weather_feature_window_complete_count") or 0
        ),
        "observation_count": int(payload.get("observation_count") or 0),
        "weather_integration_readiness": payload.get("weather_integration_readiness"),
    }


def _read_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = read_json(path)
    except InvalidMetadataError:
        return None
    return payload if isinstance(payload, dict) else None


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return float(sum(values) / len(values))


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[mid])
    return float((ordered[mid - 1] + ordered[mid]) / 2)


def _completeness(period: dict[str, Any], monthly: dict[str, int]) -> float:
    missing = _period_missing_months(period.get("start"), period.get("end"), set(monthly))
    if not period.get("start") or not period.get("end"):
        return 0.0
    try:
        start = datetime.fromisoformat(str(period["start"])[:7] + "-01")
        end = datetime.fromisoformat(str(period["end"])[:7] + "-01")
    except ValueError:
        return 0.0
    total = (end.year - start.year) * 12 + (end.month - start.month) + 1
    if total <= 0:
        return 0.0
    return round(100.0 * (total - len(missing)) / total, 2)
