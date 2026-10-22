"""Traceable calibration audit for Sentinel-2 scenes.

Does not invent processing baselines or rewrite reflectance coefficients.
Unresolved scenes remain ``requires_review``.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ml.ingestion.manifest import read_manifest, scene_records
from ml.preprocessing.raster import PROCESSING_VERSION

STATUS_REVIEW = "requires_review"
STATUS_VALID = "valid"
STATUS_WARNING = "warning"

INTERPRETATION_CONSISTENT = "consistent_with_source_metadata"
INTERPRETATION_CONFLICTING = "conflicting_offset_and_sample"
INTERPRETATION_UNVERIFIED = "unverified_missing_source_metadata"
INTERPRETATION_INCOMPLETE = "incomplete_calibration_record"
INTERPRETATION_INVALID_NDVI = "physically_implausible_ndvi_after_calibration"
INTERPRETATION_CORRUPT = "corrupt_or_unreadable_calibration_record"

ACQUIRED = {"downloaded", "processed", "failed", "downloading", "processing"}


def audit_dataset_calibration(
    dataset_id: str,
    *,
    raw_dir: Path,
    processed_dir: Path,
) -> dict[str, Any]:
    """Build a scene-level calibration audit from stored evidence only."""
    manifest_path = raw_dir / "manifest.json"
    if not manifest_path.is_file():
        return {
            "dataset_id": dataset_id,
            "processing_version": PROCESSING_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "scene_count": 0,
            "unresolved_scene_ids": [],
            "calibration_consistency": True,
            "scenes": [],
        }
    manifest = read_manifest(manifest_path)
    records = scene_records(manifest)
    scenes = []
    for record in records:
        scene_id = str(record.get("scene_id") or "")
        if not scene_id:
            continue
        processed_scene = processed_dir / "scenes" / scene_id
        raw_scene = raw_dir / "scenes" / scene_id
        ingested = record.get("status") in ACQUIRED
        has_products = (processed_scene / "processing_metadata.json").is_file() or (
            raw_scene / "calibration.json"
        ).is_file()
        if not ingested and not has_products:
            continue
        scenes.append(
            audit_scene_calibration(
                scene_id,
                record=record,
                raw_dir=raw_scene,
                processed_dir=processed_scene,
            )
        )
    unresolved = [
        scene["scene_id"]
        for scene in scenes
        if scene.get("current_status") == STATUS_REVIEW
    ]
    return {
        "dataset_id": dataset_id,
        "processing_version": PROCESSING_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scene_count": len(scenes),
        "unresolved_scene_ids": unresolved,
        "calibration_consistency": not unresolved,
        "scenes": scenes,
    }


def audit_scene_calibration(
    scene_id: str,
    *,
    record: dict[str, Any],
    raw_dir: Path,
    processed_dir: Path,
) -> dict[str, Any]:
    calibration, calibration_corrupt = _read_json(raw_dir / "calibration.json")
    if calibration is None:
        processed_cal, processed_corrupt = _read_json(processed_dir / "calibration.json")
        calibration = processed_cal
        calibration_corrupt = calibration_corrupt or processed_corrupt
    processing, _ = _read_json(processed_dir / "processing_metadata.json")
    quality, _ = _read_json(processed_dir / "quality_report.json")
    if quality is None:
        quality, _ = _read_json(processed_dir / "quality.json")

    previous_status = (
        (quality or {}).get("quality_status")
        or record.get("quality_status")
        or "unknown"
    )
    if calibration_corrupt:
        interpretation = INTERPRETATION_CORRUPT
        current_status = STATUS_REVIEW
        evidence = ["calibration_json_unreadable"]
        review = ["restore_source_calibration_json_without_inventing_coefficients"]
    elif calibration is None:
        interpretation = INTERPRETATION_INCOMPLETE
        current_status = STATUS_REVIEW
        evidence = [
            "processed_calibration_json_missing",
            "authoritative_coefficients_not_available",
        ]
        review = ["restore_or_reprocess_calibration_json_from_source_stac"]
    else:
        interpretation, evidence, review = _interpret(calibration, quality, processing)
        current_status = _status_for(
            interpretation,
            previous_status,
            implausible_ndvi=_implausible_ndvi(
                (quality or {}).get("ndvi_minimum", (quality or {}).get("ndvi_min")),
                (quality or {}).get("ndvi_maximum", (quality or {}).get("ndvi_max")),
            ),
        )
        if current_status in {STATUS_VALID, STATUS_WARNING} and previous_status == current_status:
            interpretation = INTERPRETATION_CONSISTENT
            review = []
            evidence.append(f"quality_report_status={previous_status}")

    bands = (calibration or {}).get("bands") or {}
    if not bands and processing:
        bands = (processing.get("calibration") or {})
    optical = {
        name: {
            "scale": (payload or {}).get("scale") if isinstance(payload, dict) else None,
            "offset": (payload or {}).get("offset") if isinstance(payload, dict) else None,
            "source": (payload or {}).get("source") if isinstance(payload, dict) else None,
        }
        for name, payload in bands.items()
        if name in {"blue", "green", "red", "nir"}
    }
    ndvi_min = (quality or {}).get("ndvi_minimum")
    ndvi_max = (quality or {}).get("ndvi_maximum")
    if ndvi_min is None:
        ndvi_min = (quality or {}).get("ndvi_min")
    if ndvi_max is None:
        ndvi_max = (quality or {}).get("ndvi_max")
    stored_urls = record.get("assets") or record.get("source_urls") or {}
    hrefs = {
        name: stored_urls.get(name)
        for name in ("blue", "green", "red", "nir", "scl")
    }
    missing_hrefs = [
        name for name, href in hrefs.items() if not href
    ]
    if missing_hrefs:
        evidence.append(
            "stac_asset_hrefs_unavailable:" + ",".join(missing_hrefs)
        )
    scene_quality_status = (
        (quality or {}).get("scene_quality_status")
        or (quality or {}).get("quality_status")
        or record.get("quality_status")
        or "unknown"
    )
    scene_quality_reasons = list(
        (quality or {}).get("scene_quality_reasons")
        or (quality or {}).get("reasons")
        or []
    )
    if scene_quality_status != current_status:
        evidence.append(
            "scene_quality_status_independent_of_calibration="
            + str(scene_quality_status)
        )
    return {
        "scene_id": scene_id,
        "acquisition_datetime": record.get("acquisition_datetime")
        or record.get("acquisition_date"),
        "source_metadata_reference": {
            "stac_item_id": record.get("stac_item_id") or scene_id,
            "collection": record.get("collection"),
            "source": record.get("source"),
            "hrefs": hrefs,
            "stac_asset_hrefs_complete": not missing_hrefs,
        },
        "processing_baseline": record.get("processing_baseline"),
        "earthsearch_boa_offset_applied": record.get("earthsearch_boa_offset_applied"),
        "scaling_and_offsets_applied": optical,
        "calibration_interpretation": interpretation,
        "interpretation": interpretation,
        "previous_status": previous_status,
        "current_status": current_status,
        "calibration_status": current_status,
        "scene_quality_status": scene_quality_status,
        "scene_quality_reasons": scene_quality_reasons,
        "status_scope": "calibration",
        "evidence": evidence,
        "review_requirements": review,
        "processing_version": (processing or {}).get("processing_version")
        or PROCESSING_VERSION,
        "ndvi_range": {"min": ndvi_min, "max": ndvi_max},
    }


def _interpret(
    calibration: dict[str, Any],
    quality: dict[str, Any] | None,
    processing: dict[str, Any] | None,
) -> tuple[str, list[str], list[str]]:
    evidence: list[str] = []
    review: list[str] = []
    status = str(calibration.get("validation_status") or calibration.get("status") or "")
    reason = str(calibration.get("reason") or "")
    evidence.append(f"stored_calibration_status={status}")
    if reason:
        evidence.append(f"stored_calibration_reason={reason}")
    if calibration.get("requires_review"):
        evidence.append("stored_requires_review=true")

    bands = calibration.get("bands") or {}
    missing_source = [
        name
        for name in ("blue", "green", "red", "nir")
        if isinstance(bands.get(name), dict) and bands[name].get("source") == "missing"
    ]
    if missing_source:
        evidence.append("optical_band_source_missing:" + ",".join(missing_source))

    processed_bands = (processing or {}).get("calibration") or {}
    negative = [
        name
        for name, payload in processed_bands.items()
        if isinstance(payload, dict)
        and name in {"blue", "green", "red", "nir"}
        and (payload.get("negative_fraction") or 0) >= 0.5
    ]
    if negative:
        evidence.append("majority_negative_reflectance:" + ",".join(negative))

    ndvi_min = (quality or {}).get("ndvi_minimum", (quality or {}).get("ndvi_min"))
    ndvi_max = (quality or {}).get("ndvi_maximum", (quality or {}).get("ndvi_max"))
    implausible_ndvi = _implausible_ndvi(ndvi_min, ndvi_max)
    if implausible_ndvi:
        evidence.append(
            f"stored_ndvi_range_outside_physical_bounds:{ndvi_min},{ndvi_max}"
        )

    conflict = (
        status == "conflicting"
        or calibration.get("requires_review")
        or "majority_negative_after_negative_offset" in reason
        or any(
            isinstance(payload, dict) and payload.get("discrepancy")
            for payload in processed_bands.values()
        )
    )
    if conflict:
        review.extend(
            [
                "do_not_rewrite_coefficients_from_sample_statistics",
                "compare_earthsearch_boa_offset_applied_with_raster_band_offset",
                "inspect_original_COG_sample_without_assuming_baseline_from_scene_id",
            ]
        )
        if implausible_ndvi:
            review.append("ndvi_is_not_evidence_of_valid_calibration")
        return INTERPRETATION_CONFLICTING, evidence, review

    if status == "unverified" or missing_source:
        review.append("authoritative_stac_raster_bands_or_offset_flag_missing")
        return INTERPRETATION_UNVERIFIED, evidence, review

    if implausible_ndvi:
        review.append("investigate_why_ndvi_exceeds_physical_bounds")
        return INTERPRETATION_INVALID_NDVI, evidence, review

    if status == "verified":
        return INTERPRETATION_CONSISTENT, evidence, []

    return INTERPRETATION_UNVERIFIED, evidence, ["calibration_status_not_verified"]


def _status_for(
    interpretation: str,
    previous_status: str,
    *,
    implausible_ndvi: bool = False,
) -> str:
    if previous_status in {STATUS_VALID, STATUS_WARNING}:
        if implausible_ndvi:
            return STATUS_REVIEW
        return previous_status
    if interpretation == INTERPRETATION_CONSISTENT:
        return STATUS_VALID
    return STATUS_REVIEW


def _implausible_ndvi(ndvi_min: Any, ndvi_max: Any) -> bool:
    try:
        low = float(ndvi_min)
        high = float(ndvi_max)
    except (TypeError, ValueError):
        return False
    return low < -1.5 or high > 1.5


def _read_json(path: Path) -> tuple[dict[str, Any] | None, bool]:
    if not path.is_file():
        return None, False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, True
    if not isinstance(payload, dict):
        return None, True
    return payload, False
