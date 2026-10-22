"""Non-destructive Sentinel-2 expansion preview from local discovery evidence.

Network STAC refresh and raster downloads remain opt-in. This module never
overwrites raw imagery or rewrites a validated dataset.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from ml.ingestion.selection import season_name
from ml.validation.coverage import MONTH_UNKNOWN, MONTH_VALIDATED, period_months

STATUS_VALID = "valid"

PREFERRED_MGRS = "35TLG"


def _mgrs_tile(value: Any) -> str:
    return str(value or "").upper().replace("MGRS-", "").strip()


def _is_native(record: dict[str, Any]) -> bool:
    return _mgrs_tile(record.get("mgrs_tile")) == PREFERRED_MGRS
ACTION_SKIP_EXISTING = "skip_existing_record"
ACTION_CANDIDATE_DOWNLOAD = "candidate_for_opt_in_download"
ACTION_ALTERNATIVE = "candidate_alternative_for_review_month"
ACTION_UNAVAILABLE = "no_scientifically_acceptable_candidate_in_catalog"


def preview_expansion_candidates(
    *,
    config: dict[str, Any],
    catalog_records: list[dict[str, Any]] | None,
    catalog_known: bool,
    quality_scenes: list[dict[str, Any]],
    coverage: dict[str, Any],
    limit: int = 12,
    refresh_stac: bool = False,
) -> dict[str, Any]:
    """Prioritize missing months, long gaps, season balance, AOI-native tiles."""
    period = config.get("period") or {}
    months = period_months(period.get("start"), period.get("end"))
    ingested_ids = {
        str(item.get("scene_id"))
        for item in (catalog_records or [])
        if item.get("scene_id") and item.get("status") in {
            "downloaded", "processed", "failed", "downloading"
        }
    }
    validated_dates = {
        str(item.get("acquisition_date") or "")[:10]
        for item in quality_scenes
        if item.get("quality_status") == STATUS_VALID
    }
    month_status = {
        row["month"]: row["coverage_status"]
        for row in (coverage.get("months") or [])
    }
    catalog_by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if catalog_known and catalog_records:
        for record in catalog_records:
            key = str(record.get("acquisition_date") or "")[:7]
            if len(key) == 7:
                catalog_by_month[key].append(record)

    missing_months = [
        month for month in months
        if month_status.get(month) not in {MONTH_VALIDATED}
    ]
    candidates: list[dict[str, Any]] = []
    for month in missing_months:
        record, reason = _pick_for_month(
            catalog_by_month.get(month, []),
            ingested_ids=ingested_ids,
            month_status=month_status.get(month, MONTH_UNKNOWN),
            config=config,
        )
        if record is None:
            candidates.append(_unavailable(month, month_status.get(month), catalog_known))
            continue
        scene_id = str(record.get("scene_id") or "")
        already = scene_id in ingested_ids
        action = ACTION_SKIP_EXISTING if already else ACTION_CANDIDATE_DOWNLOAD
        if month_status.get(month) == "requires_calibration_review" and not already:
            action = ACTION_ALTERNATIVE
        candidates.append({
            "month": month,
            "scene_id": scene_id,
            "acquisition_date": record.get("acquisition_date"),
            "acquisition_datetime": record.get("acquisition_datetime"),
            "source": record.get("source") or (config.get("source") or {}).get("provider"),
            "collection": record.get("collection"),
            "mgrs_tile": record.get("mgrs_tile"),
            "aoi_overlap_pct": record.get("aoi_overlap_pct")
            if record.get("aoi_overlap_pct") is not None
            else record.get("footprint_overlap_pct"),
            "footprint_overlap_pct": record.get("footprint_overlap_pct")
            if record.get("footprint_overlap_pct") is not None
            else record.get("aoi_overlap_pct"),
            "catalog_cloud_cover": record.get("cloud_cover"),
            "processing_baseline": record.get("processing_baseline"),
            "earthsearch_boa_offset_applied": record.get("earthsearch_boa_offset_applied"),
            "existing_record_status": record.get("status") or "catalog",
            "selection_reason": reason,
            "expected_action": action,
            "external_data_retrieval_required": action in {
                ACTION_CANDIDATE_DOWNLOAD, ACTION_ALTERNATIVE
            },
            "stac_verified": bool(refresh_stac),
        })

    assessments = list(candidates)
    actionable = [
        item for item in candidates
        if item.get("expected_action") in {ACTION_CANDIDATE_DOWNLOAD, ACTION_ALTERNATIVE}
    ]
    ranked = _rank(actionable, validated_dates=validated_dates, limit=limit)
    unverifiable = []
    if not catalog_known:
        unverifiable.append("discovered_candidate_counts")
    if not refresh_stac:
        unverifiable.append("live_stac_item_metadata")
        unverifiable.append("aoi_level_clear_pixel_fraction_before_download")
        unverifiable.append("authoritative_calibration_flags_absent_from_manifest")
    return {
        "dataset_id": config.get("dataset_id"),
        "dry_run": True,
        "refresh_stac": bool(refresh_stac),
        "catalog_known": catalog_known,
        "selection_rules": [
            "prefer_months_without_validated_observation",
            "prefer_months_in_longest_coverage_gaps",
            "prefer_under-represented_seasons",
            "prefer_native_mgrs_tile_35TLG_when_available",
            "never_use_scene_cloud_cover_as_aoi_quality",
            "skip_already_ingested_scene_ids",
            "do_not_assume_missing_months_have_acceptable_imagery",
            "network_download_is_opt_in",
        ],
        "months_without_validated_observation": missing_months,
        "month_assessments": assessments,
        "candidate_count": len(ranked),
        "candidates": ranked,
        "unverified_without_network": unverifiable,
        "download_command_example": (
            "python -m scripts.satellite_dataset download --config "
            "configs/satellite_multiyear.yaml --scene-id <SCENE_ID>"
        ),
    }


def _pick_for_month(
    records: list[dict[str, Any]],
    *,
    ingested_ids: set[str],
    month_status: str,
    config: dict[str, Any],
) -> tuple[dict[str, Any] | None, str]:
    if not records:
        return None, "no_catalog_record_for_month"
    unused = [item for item in records if str(item.get("scene_id")) not in ingested_ids]
    pool = unused or records
    native = [item for item in pool if _is_native(item)]
    ranked = sorted(
        native or pool,
        key=lambda item: (
            0 if _is_native(item) else 1,
            float(item.get("cloud_cover") if item.get("cloud_cover") is not None else 999),
            -float(
                item.get("aoi_overlap_pct")
                if item.get("aoi_overlap_pct") is not None
                else item.get("footprint_overlap_pct")
                or 0
            ),
            str(item.get("acquisition_date") or ""),
        ),
    )
    chosen = ranked[0]
    reasons = ["fills_month_without_validated_observation"]
    if _is_native(chosen):
        reasons.append("native_mgrs_tile")
    if str(chosen.get("scene_id")) in ingested_ids:
        reasons.append("already_ingested_record")
    if month_status == "requires_calibration_review":
        reasons.append("alternative_or_existing_review_month")
    max_cloud = float((config.get("discovery") or {}).get("max_scene_cloud_cover") or 20)
    cloud = chosen.get("cloud_cover")
    if cloud is not None and float(cloud) > max_cloud:
        reasons.append("catalog_cloud_exceeds_filter_use_aoi_mask_after_download")
    return chosen, ",".join(reasons)


def _unavailable(month: str, status: str | None, catalog_known: bool) -> dict[str, Any]:
    return {
        "month": month,
        "scene_id": None,
        "acquisition_date": None,
        "source": None,
        "aoi_overlap_pct": None,
        "catalog_cloud_cover": None,
        "existing_record_status": status,
        "selection_reason": (
            "unknown_discovery_evidence" if not catalog_known else "no_catalog_scene_for_month"
        ),
        "expected_action": ACTION_UNAVAILABLE,
        "external_data_retrieval_required": False,
        "stac_verified": False,
    }


def _rank(
    candidates: list[dict[str, Any]],
    *,
    validated_dates: set[str],
    limit: int,
) -> list[dict[str, Any]]:
    dated = sorted(validated_dates)
    def gap_score(month: str) -> int:
        probe = f"{month}-15"
        if not dated:
            return 0
        try:
            target = datetime.fromisoformat(probe)
            nearest = min(
                abs((datetime.fromisoformat(item) - target).days)
                for item in dated
            )
            return nearest
        except ValueError:
            return 0

    season_counts: dict[str, int] = defaultdict(int)
    for date in dated:
        season_counts[season_name(date)] += 1

    def sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
        month = str(item.get("month") or "")
        action = str(item.get("expected_action") or "")
        actionable = 0 if action in {ACTION_CANDIDATE_DOWNLOAD, ACTION_ALTERNATIVE} else 1
        season = season_name(f"{month}-15") if month else "unknown"
        return (
            actionable,
            -gap_score(month),
            season_counts.get(season, 0),
            month,
        )

    ordered = sorted(candidates, key=sort_key)
    return ordered[: max(0, int(limit))]
