"""Historical monthly coverage diagnostics for Sentinel-2 archives."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from statistics import median
from typing import Any

from ml.ingestion.selection import season_name

STATUS_VALID = "valid"
STATUS_WARNING = "warning"
STATUS_REJECTED = "rejected"
STATUS_REVIEW = "requires_review"


MONTH_VALIDATED = "validated_observation"
MONTH_WARNING = "processed_warning"
MONTH_REVIEW = "requires_calibration_review"
MONTH_REJECTED = "processed_rejected"
MONTH_DOWNLOADED = "downloaded_not_processed"
MONTH_DISCOVERED = "discovered_not_downloaded"
MONTH_NONE = "no_scene_discovered"
MONTH_UNKNOWN = "unknown_discovery_evidence"

ACQUIRED_STATUSES = {"downloaded", "processed", "failed", "downloading", "processing"}


def period_months(start: Any, end: Any) -> list[str]:
    """Inclusive YYYY-MM keys from period start through period end."""
    if not start or not end:
        return []
    try:
        cursor = datetime.fromisoformat(str(start)[:7] + "-01")
        last = datetime.fromisoformat(str(end)[:7] + "-01")
    except ValueError:
        return []
    months: list[str] = []
    while cursor <= last:
        months.append(f"{cursor.year:04d}-{cursor.month:02d}")
        nxt = cursor.month + 1
        cursor = (
            datetime(cursor.year + 1, 1, 1)
            if nxt == 13
            else datetime(cursor.year, nxt, 1)
        )
    return months


def build_monthly_coverage(
    *,
    period: dict[str, Any],
    catalog_records: list[dict[str, Any]] | None,
    quality_scenes: list[dict[str, Any]],
    catalog_known: bool,
) -> dict[str, Any]:
    """Per-month discovery vs ingestion vs validation.

    Unknown discovery is reported as null counts, never as zero.
    """
    months = period_months(period.get("start"), period.get("end"))
    catalog_by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if catalog_known and catalog_records is not None:
        for record in catalog_records:
            key = _month_key(record.get("acquisition_date") or record.get("acquisition_datetime"))
            if key:
                catalog_by_month[key].append(record)

    quality_by_month: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for scene in quality_scenes:
        key = _month_key(scene.get("acquisition_date"))
        if key:
            quality_by_month[key].append(scene)

    rows = []
    for month in months:
        catalog = catalog_by_month.get(month, [])
        quality = quality_by_month.get(month, [])
        rows.append(_month_row(month, catalog, quality, catalog_known=catalog_known))

    validated = [
        scene for scene in quality_scenes
        if scene.get("quality_status") == STATUS_VALID
    ]
    return {
        "period": dict(period),
        "catalog_known": catalog_known,
        "months": rows,
        "summary": _coverage_summary(validated, months, rows),
    }


def _month_row(
    month: str,
    catalog: list[dict[str, Any]],
    quality: list[dict[str, Any]],
    *,
    catalog_known: bool,
) -> dict[str, Any]:
    statuses = [item.get("quality_status") for item in quality]
    ingested = [
        item for item in catalog
        if item.get("status") in ACQUIRED_STATUSES
    ]
    downloaded = [
        item for item in catalog
        if item.get("status") in {"downloaded", "processed"}
    ]
    processed = [item for item in catalog if item.get("status") == "processed"]
    clouds = [
        item.get("cloud_shadow_fraction_pct")
        for item in quality
        if item.get("cloud_shadow_fraction_pct") is not None
    ]
    catalog_clouds = [
        item.get("cloud_cover")
        for item in catalog
        if item.get("cloud_cover") is not None
    ]
    dates = sorted({
        str(item.get("acquisition_date") or "")[:10]
        for item in (quality or catalog)
        if item.get("acquisition_date")
    })
    if any(status == STATUS_VALID for status in statuses):
        coverage_status = MONTH_VALIDATED
    elif any(status == STATUS_WARNING for status in statuses):
        coverage_status = MONTH_WARNING
    elif any(status == STATUS_REVIEW for status in statuses):
        coverage_status = MONTH_REVIEW
    elif any(status == STATUS_REJECTED for status in statuses):
        coverage_status = MONTH_REJECTED
    elif processed:
        coverage_status = MONTH_DOWNLOADED
    elif downloaded or ingested:
        coverage_status = MONTH_DOWNLOADED
    elif catalog_known and catalog:
        coverage_status = MONTH_DISCOVERED
    elif catalog_known:
        coverage_status = MONTH_NONE
    else:
        coverage_status = MONTH_UNKNOWN

    return {
        "month": month,
        "discovered_candidate_scenes": None if not catalog_known else len(catalog),
        "ingested_scenes": len(ingested),
        "validated_observations": sum(1 for status in statuses if status == STATUS_VALID),
        "requires_review": sum(1 for status in statuses if status == STATUS_REVIEW),
        "rejected": sum(1 for status in statuses if status == STATUS_REJECTED),
        "warning": sum(1 for status in statuses if status == STATUS_WARNING),
        "available_acquisition_dates": dates,
        "scene_ids": [item.get("scene_id") for item in quality or catalog if item.get("scene_id")],
        "aoi_cloud_shadow_fraction_pct_mean": _mean(clouds),
        "catalog_cloud_cover_mean": _mean(catalog_clouds),
        "coverage_status": coverage_status,
    }


def _coverage_summary(
    validated: list[dict[str, Any]],
    months: list[str],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    dates = sorted({
        str(item.get("acquisition_date") or "")[:10]
        for item in validated
        if item.get("acquisition_date")
    })
    intervals = []
    for earlier, later in zip(dates, dates[1:]):
        try:
            delta = (
                datetime.fromisoformat(later) - datetime.fromisoformat(earlier)
            ).days
        except ValueError:
            continue
        intervals.append(delta)
    by_year: dict[str, int] = defaultdict(int)
    by_month: dict[str, int] = defaultdict(int)
    by_season: dict[str, int] = defaultdict(int)
    for item in validated:
        date = str(item.get("acquisition_date") or "")[:10]
        if len(date) >= 7:
            by_month[date[:7]] += 1
            by_year[date[:4]] += 1
            by_season[season_name(date)] += 1
    represented = sum(1 for row in rows if row["validated_observations"] > 0)
    consecutive = _consecutive_missing([
        row["month"] for row in rows if row["validated_observations"] == 0
    ])
    return {
        "validated_observations": len(validated),
        "observations_by_year": dict(sorted(by_year.items())),
        "observations_by_month": dict(sorted(by_month.items())),
        "observations_by_season": dict(by_season),
        "months_in_period": len(months),
        "months_with_validated_observation": represented,
        "temporal_sampling_completeness_pct": (
            round(100.0 * represented / len(months), 2) if months else 0.0
        ),
        "median_interval_days": None if not intervals else float(median(intervals)),
        "maximum_interval_days": None if not intervals else int(max(intervals)),
        "longest_observation_gap_days": None if not intervals else int(max(intervals)),
        "consecutive_months_without_validated_observation": consecutive,
        "acquisition_dates": dates,
    }


def _consecutive_missing(missing_months: list[str]) -> list[dict[str, Any]]:
    if not missing_months:
        return []
    runs: list[dict[str, Any]] = []
    start = prev = missing_months[0]
    length = 1
    for month in missing_months[1:]:
        if _next_month(prev) == month:
            length += 1
            prev = month
            continue
        runs.append({"start": start, "end": prev, "months": length})
        start = prev = month
        length = 1
    runs.append({"start": start, "end": prev, "months": length})
    runs.sort(key=lambda item: (-int(item["months"]), item["start"]))
    return runs


def _next_month(month: str) -> str:
    year = int(month[:4])
    value = int(month[5:7]) + 1
    if value == 13:
        return f"{year + 1:04d}-01"
    return f"{year:04d}-{value:02d}"


def _month_key(value: Any) -> str | None:
    text = str(value or "")[:7]
    return text if len(text) == 7 and text[4] == "-" else None


def _mean(values: list[Any]) -> float | None:
    numbers = [float(value) for value in values if value is not None]
    if not numbers:
        return None
    return round(sum(numbers) / len(numbers), 4)
