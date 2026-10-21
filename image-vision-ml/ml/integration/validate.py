"""Integrity checks for the satellite–weather observation table."""

from __future__ import annotations

from collections import Counter
from typing import Any

from ml.integration.features import DEFAULT_WINDOWS, INTEGRATION_VERSION
from ml.integration.satellite_weather import (
    _as_date,
    _index_weather,
    _usable_weather_record,
    historical_weather_features,
    prior_window_dates,
)
from ml.preprocessing.weather import _maybe_float


def validate_integrated_observations(
    rows: list[dict[str, Any]],
    *,
    weather_rows: list[dict[str, Any]] | None = None,
    windows: tuple[int, ...] = DEFAULT_WINDOWS,
    source_fingerprints: dict[str, Any] | None = None,
    previous_fingerprints: dict[str, Any] | None = None,
    dropped_duplicate_scene_ids: list[str] | None = None,
    dry_day_mm: float = 1.0,
) -> dict[str, Any]:
    """Return a quality report. Does not drop rows."""
    weather_by_date = _index_weather(weather_rows or [])
    issues: list[dict[str, Any]] = []
    seen_ids: list[str] = []
    for row in rows:
        scene_id = row.get("scene_id")
        if scene_id:
            seen_ids.append(str(scene_id))
        issues.extend(_validate_row(row, weather_by_date, windows, dry_day_mm))
    duplicates = [scene_id for scene_id, count in Counter(seen_ids).items() if count > 1]
    for scene_id in duplicates:
        issues.append({
            "code": "duplicate_scene_id",
            "severity": "error",
            "scene_id": scene_id,
            "message": "Integrated table contains more than one row for this scene_id.",
        })
    for scene_id in dropped_duplicate_scene_ids or []:
        issues.append({
            "code": "duplicate_scene_prevented",
            "severity": "warning",
            "scene_id": scene_id,
            "message": "A duplicate input scene_id was dropped; the first occurrence was kept.",
        })
    if previous_fingerprints and source_fingerprints:
        if previous_fingerprints != source_fingerprints:
            issues.append({
                "code": "source_inputs_changed",
                "severity": "info",
                "message": (
                    "Weather or satellite source fingerprints differ from the previous "
                    "integration. Features were recomputed."
                ),
            })
    summary = _summary(rows, windows)
    return {
        "integration_version": INTEGRATION_VERSION,
        "observation_count": len(rows),
        "duplicate_scene_ids": duplicates,
        "dropped_duplicate_scene_ids": list(dropped_duplicate_scene_ids or []),
        "issues": issues,
        **summary,
        "source_fingerprints": source_fingerprints or {},
    }


def _validate_row(
    row: dict[str, Any],
    weather_by_date: dict[str, dict[str, Any]],
    windows: tuple[int, ...],
    dry_day_mm: float,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    scene_id = row.get("scene_id")
    obs_date = _as_date(row.get("observation_date_utc") or row.get("acquisition_timestamp_utc"))
    if not row.get("scene_id"):
        issues.append(_issue("missing_scene_id", "error", scene_id, "Scene identifier is missing."))
    if obs_date is None:
        issues.append(_issue(
            "missing_acquisition_timestamp",
            "error",
            scene_id,
            "Satellite acquisition timestamp/date is missing.",
        ))
        return issues
    if row.get("weather_feature_window_complete") and not row.get("source_grid_id"):
        if row.get("weather_grid_latitude") is None or row.get("weather_grid_longitude") is None:
            issues.append(_issue(
                "invalid_weather_grid_provenance",
                "error",
                scene_id,
                "Complete weather features lack a native ERA5-Land grid coordinate.",
            ))
    ndvi = _maybe_float(row.get("ndvi_mean"))
    ndvi_min = _maybe_float(row.get("ndvi_minimum"))
    ndvi_max = _maybe_float(row.get("ndvi_maximum"))
    if ndvi is not None and (ndvi < -1.0 or ndvi > 1.0):
        issues.append(_issue("invalid_ndvi_mean", "error", scene_id, "NDVI mean is outside [-1, 1]."))
    if ndvi_min is not None and ndvi_max is not None and ndvi_min - ndvi_max > 1e-9:
        issues.append(_issue("invalid_ndvi_range", "error", scene_id, "NDVI minimum exceeds maximum."))
    if ndvi is not None and ndvi_min is not None and ndvi_max is not None:
        if ndvi < ndvi_min - 1e-6 or ndvi > ndvi_max + 1e-6:
            issues.append(_issue(
                "invalid_ndvi_statistics",
                "error",
                scene_id,
                "NDVI mean is outside the reported min/max range.",
            ))
    status = row.get("satellite_quality_status") or row.get("quality_status")
    if row.get("satellite_observation_valid") and status not in {"valid", "warning"}:
        issues.append(_issue(
            "incompatible_source_quality",
            "error",
            scene_id,
            "Satellite observation is marked valid with an incompatible quality status.",
        ))
    precip = _maybe_float(row.get("precip_prev_7d_mm"))
    if precip is not None and precip < 0:
        issues.append(_issue("unit_mismatch_precipitation", "error", scene_id, "Precipitation total is negative."))
    rh = _maybe_float(row.get("rh_mean_prev_7d_pct"))
    if rh is not None and (rh < 0 or rh > 100):
        issues.append(_issue("unit_mismatch_humidity", "error", scene_id, "Relative humidity is outside 0–100 %."))
    wind = _maybe_float(row.get("wind_mean_prev_7d_ms"))
    if wind is not None and wind < 0:
        issues.append(_issue("unit_mismatch_wind", "error", scene_id, "Wind speed is negative."))
    issues.extend(_validate_windows(row, weather_by_date, windows, dry_day_mm, obs_date, scene_id))
    return issues


def _validate_windows(
    row: dict[str, Any],
    weather_by_date: dict[str, dict[str, Any]],
    windows: tuple[int, ...],
    dry_day_mm: float,
    obs_date,
    scene_id: str | None,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    recomputed = historical_weather_features(
        weather_by_date,
        obs_date,
        dry_day_mm=dry_day_mm,
        windows=windows,
    )
    for window in windows:
        expected = prior_window_dates(obs_date, window)
        start = row.get(f"window_{window}d_start_utc")
        end = row.get(f"window_{window}d_end_utc")
        if expected:
            if start and start != expected[0].isoformat():
                issues.append(_issue(
                    "incorrect_window_start",
                    "error",
                    scene_id,
                    f"{window}-day window start {start} != {expected[0].isoformat()}.",
                ))
            if end and end != expected[-1].isoformat():
                issues.append(_issue(
                    "incorrect_window_end",
                    "error",
                    scene_id,
                    f"{window}-day window end {end} != {expected[-1].isoformat()}.",
                ))
            if end and end >= obs_date.isoformat():
                issues.append(_issue(
                    "future_temporal_leakage",
                    "error",
                    scene_id,
                    f"{window}-day window includes the acquisition date or later.",
                ))
        observed = int(row.get(f"window_{window}d_observed_days") or 0)
        expected_n = int(row.get(f"window_{window}d_expected_days") or window)
        if observed < expected_n:
            issues.append(_issue(
                "missing_historical_weather_days",
                "warning",
                scene_id,
                f"{window}-day window has {observed}/{expected_n} observed days.",
            ))
        stored = _maybe_float(row.get(f"precip_prev_{window}d_mm"))
        expected_precip = _maybe_float(recomputed.get(f"precip_prev_{window}d_mm"))
        if stored is None and expected_precip is not None:
            issues.append(_issue(
                "reprocessing_inconsistency",
                "error",
                scene_id,
                f"{window}-day precipitation does not match a fresh computation.",
            ))
        elif stored is not None and expected_precip is None:
            issues.append(_issue(
                "reprocessing_inconsistency",
                "error",
                scene_id,
                f"{window}-day precipitation is present despite an incomplete window.",
            ))
        elif stored is not None and expected_precip is not None and abs(stored - expected_precip) > 1e-6:
            issues.append(_issue(
                "reprocessing_inconsistency",
                "error",
                scene_id,
                f"{window}-day precipitation {stored} != recomputed {expected_precip}.",
            ))
        if stored is not None:
            for day in expected:
                record = weather_by_date.get(day.isoformat())
                if not _usable_weather_record(record):
                    issues.append(_issue(
                        "future_or_missing_fill",
                        "error",
                        scene_id,
                        f"{window}-day precipitation used a non-complete day {day.isoformat()}.",
                    ))
                    break
            acquisition_record = weather_by_date.get(obs_date.isoformat())
            if acquisition_record and _maybe_float(acquisition_record.get("precipitation_total_mm")) is not None:
                # Presence of acquisition-day rain is allowed in the daily table;
                # it must not be required for the feature. Recompute already excludes D.
                pass
    return issues


def _summary(rows: list[dict[str, Any]], windows: tuple[int, ...]) -> dict[str, Any]:
    def _count(field: str) -> int:
        return sum(1 for row in rows if row.get(field))

    window_counts = {
        f"window_{window}d_complete_count": sum(
            1 for row in rows if row.get(f"window_{window}d_complete")
        )
        for window in windows
    }
    return {
        "satellite_observation_valid_count": _count("satellite_observation_valid"),
        "weather_observation_valid_count": _count("weather_observation_valid"),
        "weather_feature_window_complete_count": _count("weather_feature_window_complete"),
        "integrated_observation_complete_count": _count("integrated_observation_complete"),
        "suitable_for_modeling_count": _count("suitable_for_modeling"),
        **window_counts,
    }


def _issue(code: str, severity: str, scene_id: str | None, message: str) -> dict[str, Any]:
    return {
        "code": code,
        "severity": severity,
        "scene_id": scene_id,
        "message": message,
    }
