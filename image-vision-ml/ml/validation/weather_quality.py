"""Quality checks for hourly ERA5-Land records and daily weather tables."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

import numpy as np

from ml.preprocessing.weather import ROUNDING_MM, _as_utc, _is_nan, _maybe_float


STATUS_VALID = "valid"
STATUS_WARNING = "warning"
STATUS_REJECTED = "rejected"
STATUS_REVIEW = "requires_review"
STATUS_MISSING = "missing"

PERIOD_COMPLETE = "complete"
PERIOD_INCOMPLETE = "incomplete"
READINESS_READY = "ready"
READINESS_LIMITED = "limited"
READINESS_NOT_READY = "not_ready"

# Plausible meteorological ranges used as warnings, not hard failures.
TEMPERATURE_WARN_C = (-80.0, 60.0)
DEWPOINT_WARN_C = (-90.0, 50.0)
WIND_WARN_MS = (0.0, 80.0)
PRECIP_WARN_MM = (0.0, 500.0)
RH_WARN_PCT = (0.0, 100.0)
EVAP_WARN_MM = (-20.0, 50.0)


def evaluate_hourly_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate raw hourly timestamps, units, and accumulation steps."""
    issues: list[dict[str, Any]] = []
    stamps = [_as_utc(item.get("timestamp_utc") or item.get("time")) for item in records]
    present = [stamp for stamp in stamps if stamp is not None]
    missing_stamps = len(stamps) - len(present)
    if missing_stamps:
        issues.append(_issue(STATUS_REJECTED, "missing_timestamps", missing_stamps))

    tz_naive = sum(1 for stamp in present if stamp.tzinfo is None)
    if tz_naive:
        issues.append(_issue(STATUS_REVIEW, "naive_timestamps", tz_naive))
    non_utc = sum(
        1
        for stamp in present
        if stamp.tzinfo is not None and stamp.utcoffset() != timezone.utc.utcoffset(stamp)
    )
    if non_utc:
        issues.append(_issue(STATUS_REVIEW, "non_utc_timestamps", non_utc))

    duplicates = len(present) - len(set(present))
    if duplicates:
        issues.append(_issue(STATUS_REJECTED, "duplicate_timestamps", duplicates))

    ordered = sorted(present)
    if ordered != present and not duplicates:
        issues.append(_issue(STATUS_WARNING, "timestamps_not_monotonic", 1))

    units = _unit_issues(records)
    issues.extend(units)
    accumulation = classify_accumulation_steps(records)
    issues.extend(accumulation["issues"])
    return {
        "hourly_records": len(records),
        "unique_timestamps": len(set(present)),
        "accumulation": accumulation["summary"],
        "issues": issues,
        "status": _worst(issues),
    }


def evaluate_daily_rows(
    rows: list[dict[str, Any]],
    *,
    require_complete_days: bool = True,
) -> dict[str, Any]:
    """Classify each UTC daily row and summarise dataset completeness."""
    evaluated = []
    for row in rows:
        item = dict(row)
        reasons: list[str] = []
        status = item.get("quality_status") or STATUS_VALID

        available = int(item.get("hourly_records_available") or 0)
        expected = int(item.get("hourly_records_expected") or 24)
        if available == 0:
            item["quality_status"] = STATUS_MISSING
            item["quality_reasons"] = ["missing_observations"]
            item["observation_kind"] = item.get("observation_kind") or "missing"
            evaluated.append(item)
            continue
        if available < expected:
            status = _raise_status(status, STATUS_WARNING)
            reasons.append("incomplete_hourly_coverage")

        if not item.get("boundary_00utc_available"):
            if item.get("precipitation_total_mm") is None:
                status = _raise_status(
                    status,
                    STATUS_REVIEW if require_complete_days else STATUS_WARNING,
                )
                reasons.append("missing_boundary_hour")
            else:
                status = _raise_status(status, STATUS_WARNING)
                reasons.append("daily_total_without_boundary")

        if item.get("source_grid_id") is None and not item.get("spatial"):
            status = _raise_status(status, STATUS_REVIEW)
            reasons.append("missing_spatial_provenance")

        precip = _maybe_float(item.get("precipitation_total_mm"))
        if precip is not None and precip < 0:
            if abs(precip) <= ROUNDING_MM:
                reasons.append("negative_precipitation_rounding")
                status = _raise_status(status, STATUS_WARNING)
            else:
                reasons.append("negative_precipitation")
                status = STATUS_REVIEW

        reasons.extend(_range_reasons(item))
        if any(reason.startswith("implausible_") for reason in reasons):
            status = _raise_status(status, STATUS_WARNING)

        item["quality_status"] = status
        item["quality_reasons"] = reasons
        if item.get("hourly_records_available") == item.get("hourly_records_expected") and item.get("boundary_00utc_available"):
            item["observation_kind"] = "complete"
        else:
            item["observation_kind"] = item.get("observation_kind") or "partial"
        evaluated.append(item)

    counts = Counter(item["quality_status"] for item in evaluated)
    complete = sum(
        1
        for item in evaluated
        if item.get("hourly_records_available") == item.get("hourly_records_expected")
        and item.get("boundary_00utc_available")
    )
    missing_days = sum(1 for item in evaluated if item.get("hourly_records_available") == 0)
    return {
        "days": evaluated,
        "day_count": len(evaluated),
        "complete_days": complete,
        "missing_days": missing_days,
        "incomplete_days": len(evaluated) - complete,
        "statuses": dict(counts),
        "status": _observation_validity(counts, len(evaluated)),
    }


def build_quality_report(
    *,
    dataset_id: str,
    config: dict[str, Any],
    hourly: dict[str, Any],
    daily: dict[str, Any],
    spatial: dict[str, Any] | None = None,
    variables: list[str] | None = None,
    coverage: dict[str, Any] | None = None,
    extra_issues: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    period = config.get("period") or {}
    expected_days = daily.get("day_count") or 0
    complete = daily.get("complete_days") or 0
    missing_days = daily.get("missing_days") or 0
    issues = list(hourly.get("issues") or [])
    issues.extend(extra_issues or [])
    source_integrity = hourly.get("status") or STATUS_VALID
    observation_validity = daily.get("status") or STATUS_VALID
    period_completeness = (
        PERIOD_COMPLETE if expected_days and complete >= expected_days else PERIOD_INCOMPLETE
    )
    if period_completeness == PERIOD_INCOMPLETE:
        issues.append({
            "severity": STATUS_WARNING,
            "code": "incomplete_historical_period",
            "count": expected_days - complete,
            "complete_days": complete,
            "expected_days": expected_days,
        })
    integrity_status = _worst(
        [{"severity": source_integrity}, {"severity": observation_validity}]
        + [item for item in issues if item.get("code") != "incomplete_historical_period"]
    )
    integration_readiness = _integration_readiness(
        source_integrity,
        observation_validity,
        period_completeness,
    )
    return {
        "dataset_id": dataset_id,
        "source_dataset": (config.get("source") or {}).get("dataset", "reanalysis-era5-land"),
        "period": period,
        "timezone": (config.get("time") or {}).get("timezone", "UTC"),
        "variables": list(variables or config.get("variables") or []),
        "spatial": spatial,
        "hourly": hourly,
        "accumulation": hourly.get("accumulation"),
        "coverage": coverage,
        "daily": {
            "day_count": expected_days,
            "complete_days": complete,
            "missing_days": missing_days,
            "incomplete_days": daily.get("incomplete_days") or (expected_days - complete),
            "statuses": daily.get("statuses") or {},
            "completeness_pct": (
                None if not expected_days else round(100.0 * complete / expected_days, 2)
            ),
        },
        "source_integrity": source_integrity,
        "observation_validity": observation_validity,
        "period_completeness": period_completeness,
        "integration_readiness": integration_readiness,
        "status": integrity_status,
        "issues": issues,
    }


def spatial_selection_issue(spatials: list[dict[str, Any]]) -> dict[str, Any] | None:
    cells = []
    for item in spatials:
        if not item:
            continue
        lat = item.get("source_latitude")
        lon = item.get("source_longitude")
        if lat is None or lon is None:
            continue
        cells.append((round(float(lat), 4), round(float(lon), 4)))
    unique = sorted(set(cells))
    if len(unique) > 1:
        return {
            "severity": STATUS_WARNING,
            "code": "inconsistent_spatial_selection",
            "count": len(unique),
            "cells": unique,
        }
    return None


def _unit_issues(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues = []
    kelvin_like = 0
    celsius_like = 0
    for item in records:
        temperature = _maybe_float(item.get("t2m"))
        if temperature is None:
            continue
        if temperature > 100:
            kelvin_like += 1
        elif temperature < 80:
            celsius_like += 1
    if kelvin_like and celsius_like:
        issues.append(_issue(STATUS_REVIEW, "mixed_temperature_units", kelvin_like))
    precip = [
        _maybe_float(item.get("tp"))
        for item in records
        if _maybe_float(item.get("tp")) is not None
    ]
    if precip and max(precip) > 2:
        issues.append(_issue(STATUS_REVIEW, "precipitation_not_in_metres", max(precip)))
    return issues


def classify_accumulation_steps(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Separate ERA5-Land 01 UTC forecast-cycle resets from anomalies.

    In the CDS hourly product, 00:00 UTC stores the previous UTC day's
    accumulated total and 01:00 UTC starts a new forecast accumulation.
    A drop at 01 UTC is therefore expected and is not a quality warning.
    Decreases at other hours, or significant negative values, remain
    reviewable anomalies.
    """
    ordered = sorted(
        (item for item in records if _as_utc(item.get("timestamp_utc"))),
        key=lambda item: _as_utc(item.get("timestamp_utc")),
    )
    previous = None
    previous_stamp = None
    forecast_cycle = 0
    unexpected = 0
    negatives = 0
    for item in ordered:
        current = _maybe_float(item.get("tp"))
        stamp = _as_utc(item.get("timestamp_utc"))
        if current is None:
            previous = None
            previous_stamp = None
            continue
        if previous is not None and current + ROUNDING_MM < previous:
            if current < -ROUNDING_MM:
                negatives += 1
            elif _is_forecast_cycle_reset(stamp, previous_stamp):
                forecast_cycle += 1
            else:
                unexpected += 1
        previous = current
        previous_stamp = stamp
    issues = []
    if unexpected:
        issues.append(_issue(STATUS_WARNING, "unexpected_accumulation_resets", unexpected))
    if negatives:
        issues.append(_issue(STATUS_REVIEW, "negative_accumulation_steps", negatives))
    return {
        "issues": issues,
        "summary": {
            "forecast_cycle_resets": forecast_cycle,
            "unexpected_resets": unexpected,
            "negative_steps": negatives,
            "interpretation": (
                "01 UTC decreases are ERA5-Land forecast-cycle starts, "
                "not missing rainfall. Daily totals use the next-day "
                "00:00 UTC accumulated value."
            ),
        },
    }


def _is_forecast_cycle_reset(
    stamp: datetime | None,
    previous_stamp: datetime | None,
) -> bool:
    if stamp is None or stamp.hour != 1:
        return False
    if previous_stamp is None:
        return True
    delta = stamp - previous_stamp
    return delta.total_seconds() == 3600 and previous_stamp.hour == 0


def _range_reasons(row: dict[str, Any]) -> list[str]:
    reasons = []
    checks = (
        ("temperature_mean_c", TEMPERATURE_WARN_C, "implausible_temperature"),
        ("dewpoint_mean_c", DEWPOINT_WARN_C, "implausible_dewpoint"),
        ("wind_speed_mean_ms", WIND_WARN_MS, "implausible_wind"),
        ("precipitation_total_mm", PRECIP_WARN_MM, "implausible_precipitation"),
        ("relative_humidity_mean_pct", RH_WARN_PCT, "implausible_humidity"),
        ("evaporation_total_mm", EVAP_WARN_MM, "implausible_evaporation"),
    )
    for field, (low, high), reason in checks:
        value = _maybe_float(row.get(field))
        if value is None:
            continue
        if value < low or value > high:
            reasons.append(reason)
    return reasons


def _issue(severity: str, code: str, count: Any) -> dict[str, Any]:
    return {"severity": severity, "code": code, "count": count}


def raise_status(current: str, incoming: str) -> str:
    return _raise_status(current, incoming)


def _raise_status(current: str, incoming: str) -> str:
    order = {
        STATUS_VALID: 0,
        STATUS_WARNING: 1,
        STATUS_REVIEW: 2,
        STATUS_REJECTED: 3,
    }
    if order.get(incoming, 0) > order.get(current, 0):
        return incoming
    return current


def _worst(issues: list[dict[str, Any]]) -> str:
    status = STATUS_VALID
    for item in issues:
        status = _raise_status(status, str(item.get("severity") or STATUS_VALID))
    return status


def _dataset_status(counts: Counter, total: int) -> str:
    return _observation_validity(counts, total)


def _observation_validity(counts: Counter, total: int) -> str:
    """Validity of days that have observations; missing days are coverage."""
    missing = counts.get(STATUS_MISSING, 0)
    observed = total - missing
    if not total:
        return STATUS_REJECTED
    if observed == 0:
        return STATUS_MISSING
    observed_rejected = counts.get(STATUS_REJECTED, 0)
    if observed_rejected == observed:
        return STATUS_REJECTED
    if counts.get(STATUS_REVIEW, 0):
        return STATUS_REVIEW
    if counts.get(STATUS_WARNING, 0) or observed_rejected:
        return STATUS_WARNING
    return STATUS_VALID


def _integration_readiness(
    source_integrity: str,
    observation_validity: str,
    period_completeness: str,
) -> str:
    blocking = {STATUS_REJECTED, STATUS_REVIEW}
    if source_integrity in blocking or observation_validity in blocking:
        return READINESS_NOT_READY
    if period_completeness != PERIOD_COMPLETE:
        return READINESS_LIMITED
    if source_integrity == STATUS_WARNING or observation_validity == STATUS_WARNING:
        return READINESS_LIMITED
    return READINESS_READY
