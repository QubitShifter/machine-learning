"""Optional quality-gated satellite recency features.

Unobserved days stay null. There is no forward fill of NDVI.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from ml.agricultural_ml.features import empty_satellite_features
from ml.agricultural_ml.time_semantics import iso_z, issue_datetime_utc, parse_utc_date
from ml.forecasting.contracts import parse_utc
from ml.preprocessing.raster import default_processed_root, read_json
from ml.preprocessing.weather import _maybe_float


def load_eligible_satellite_observations(
    satellite_dataset_id: str,
    *,
    processed_root: Path | None = None,
    quality_statuses: tuple[str, ...] = ("valid",),
    calibration_statuses: tuple[str, ...] = ("verified",),
    exclude_scene_quality: tuple[str, ...] = ("rejected", "requires_review"),
) -> list[dict[str, Any]]:
    root = processed_root or default_processed_root()
    quality_path = root / satellite_dataset_id / "quality" / "dataset_quality.json"
    series_path = root / satellite_dataset_id / "timeseries" / "ndvi_timeseries.json"
    if not quality_path.is_file():
        return []
    payload = read_json(quality_path)
    series_by_id: dict[str, dict[str, Any]] = {}
    if series_path.is_file():
        for item in (read_json(series_path).get("observations") or []):
            scene_id = item.get("scene_id")
            if scene_id:
                series_by_id[str(scene_id)] = item
    eligible = []
    for scene in payload.get("scenes") or []:
        scene_id = scene.get("scene_id")
        quality = str(scene.get("quality_status") or scene.get("scene_quality_status") or "")
        calibration = str(scene.get("calibration_status") or "")
        if not scene_id:
            continue
        if quality in exclude_scene_quality or quality not in quality_statuses:
            continue
        if calibration_statuses and calibration not in calibration_statuses:
            continue
        series = series_by_id.get(str(scene_id)) or {}
        acquisition_date = parse_utc_date(
            scene.get("acquisition_date") or series.get("date") or series.get("datetime")
        )
        timestamp = parse_utc(
            scene.get("acquisition_datetime")
            or series.get("datetime")
            or (acquisition_date.isoformat() + "T00:00:00Z" if acquisition_date else None)
        )
        if acquisition_date is None:
            continue
        eligible.append({
            "scene_id": scene_id,
            "acquisition_date": acquisition_date,
            "acquisition_timestamp": timestamp,
            "ndvi_mean": _maybe_float(scene.get("ndvi_mean") if scene.get("ndvi_mean") is not None else series.get("mean")),
            "ndvi_median": _maybe_float(scene.get("ndvi_median") if scene.get("ndvi_median") is not None else series.get("median")),
            "ndvi_std": _maybe_float(
                scene.get("ndvi_standard_deviation")
                if scene.get("ndvi_standard_deviation") is not None
                else series.get("standard_deviation")
            ),
            "ndvi_p10": _maybe_float(scene.get("ndvi_p10")),
            "ndvi_p90": _maybe_float(scene.get("ndvi_p90")),
            "valid_pixel_fraction": _maybe_float(scene.get("valid_ndvi_pct")),
            "calibration_status": calibration,
            "quality_status": quality,
        })
    eligible.sort(key=lambda item: (item["acquisition_date"], str(item["scene_id"])))
    return eligible


def satellite_features_for_issue(
    issue_date: date,
    observations: list[dict[str, Any]],
    *,
    max_age_days: int,
    assumption: str = "acquisition_time_only_research",
) -> dict[str, Any]:
    payload = empty_satellite_features()
    payload["satellite_availability_assumption"] = assumption
    payload["satellite_operational_availability_verified"] = False
    cutoff = issue_datetime_utc(issue_date)
    eligible = []
    for item in observations:
        timestamp: datetime | None = item.get("acquisition_timestamp")
        acquired: date = item["acquisition_date"]
        if timestamp is not None:
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            if timestamp >= cutoff:
                continue
        elif acquired >= issue_date:
            # Date-only timestamps are not proven available at D 00:00 UTC.
            continue
        eligible.append(item)
    if not eligible:
        return payload
    latest = eligible[-1]
    acquired = latest["acquisition_date"]
    age = (issue_date - acquired).days
    payload.update({
        "satellite_available": age <= max_age_days,
        "satellite_stale": age > max_age_days,
        "satellite_missing": False,
        "satellite_scene_id": latest["scene_id"],
        "satellite_acquisition_date_utc": acquired.isoformat(),
        "satellite_acquisition_timestamp_utc": (
            iso_z(latest["acquisition_timestamp"]) if latest.get("acquisition_timestamp") else None
        ),
        "satellite_age_days": age,
        "satellite_calibration_status": latest.get("calibration_status"),
        "satellite_scene_quality_status": latest.get("quality_status"),
        "satellite_valid_pixel_fraction": latest.get("valid_pixel_fraction"),
    })
    if age > max_age_days:
        payload["satellite_available"] = False
        return payload
    payload.update({
        "ndvi_last_valid_mean": latest.get("ndvi_mean"),
        "ndvi_last_valid_median": latest.get("ndvi_median"),
        "ndvi_last_valid_std": latest.get("ndvi_std"),
        "ndvi_last_valid_p10": latest.get("ndvi_p10"),
        "ndvi_last_valid_p90": latest.get("ndvi_p90"),
    })
    return payload


def satellite_by_issue_date(
    issue_dates: list[date],
    observations: list[dict[str, Any]],
    *,
    max_age_days: int,
    assumption: str,
) -> dict[date, dict[str, Any]]:
    return {
        issue_date: satellite_features_for_issue(
            issue_date, observations, max_age_days=max_age_days, assumption=assumption,
        )
        for issue_date in issue_dates
    }
