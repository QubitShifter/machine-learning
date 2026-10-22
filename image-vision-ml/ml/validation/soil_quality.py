"""Quality checks for instantaneous ERA5-Land soil-water records."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from ml.preprocessing.soil import (
    EXPECTED_HOURS,
    OBSERVATION_KIND,
    SOIL_LAYERS,
    THETA_INVALID_HIGH,
    THETA_INVALID_LOW,
    physical_flags,
)
from ml.preprocessing.weather import _as_utc, _maybe_float
from ml.validation.weather_quality import (
    PERIOD_COMPLETE,
    PERIOD_INCOMPLETE,
    READINESS_LIMITED,
    READINESS_NOT_READY,
    READINESS_READY,
    STATUS_MISSING,
    STATUS_REJECTED,
    STATUS_REVIEW,
    STATUS_VALID,
    STATUS_WARNING,
    _issue,
    _worst,
    raise_status,
    spatial_selection_issue,
)


def evaluate_hourly_soil(records: list[dict[str, Any]]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    stamps = [_as_utc(item.get("timestamp_utc") or item.get("time")) for item in records]
    present = [stamp for stamp in stamps if stamp is not None]
    if len(stamps) - len(present):
        issues.append(_issue(STATUS_REJECTED, "missing_timestamps", len(stamps) - len(present)))
    duplicates = len(present) - len(set(present))
    if duplicates:
        issues.append(_issue(STATUS_REJECTED, "duplicate_timestamps", duplicates))
    missing_layers = {key: 0 for key in SOIL_LAYERS}
    physical: list[str] = []
    for record in records:
        for key in SOIL_LAYERS:
            value = _maybe_float(record.get(key))
            if value is None:
                missing_layers[key] += 1
                continue
            physical.extend(physical_flags(value))
    for key, count in missing_layers.items():
        if count:
            issues.append(_issue(STATUS_REVIEW, f"missing_{key}", count))
    flag_counts = Counter(physical)
    for code, count in sorted(flag_counts.items()):
        issues.append(_issue(STATUS_REVIEW, code, count))
    return {
        "hourly_records": len(records),
        "unique_timestamps": len(set(present)),
        "missing_layer_hours": missing_layers,
        "physical_flag_counts": dict(flag_counts),
        "accumulation_rule": "not_applicable_instantaneous_state",
        "issues": issues,
        "status": _worst(issues),
    }


def evaluate_daily_soil(
    rows: list[dict[str, Any]],
    *,
    require_complete_days: bool = True,
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    complete = 0
    missing = 0
    review = 0
    for item in rows:
        status = str(item.get("quality_status") or STATUS_MISSING)
        available = int(item.get("hourly_records_available") or 0)
        if item.get("complete_day") and status == STATUS_VALID:
            complete += 1
        elif available == 0:
            missing += 1
        else:
            review += 1
        if require_complete_days and available and available != EXPECTED_HOURS:
            issues.append(_issue(STATUS_REVIEW, "incomplete_hourly_coverage", 1))
        if item.get("is_ground_truth") or item.get("is_measured_soil_moisture"):
            issues.append(_issue(STATUS_REJECTED, "modeled_soil_mislabeled_as_measured", 1))
        if item.get("observation_kind") not in {None, OBSERVATION_KIND}:
            issues.append(_issue(STATUS_REVIEW, "unexpected_observation_kind", 1))
        flags = item.get("quality_flags") or []
        if isinstance(flags, str):
            flags = [part for part in flags.split(";") if part]
        for flag in flags:
            if flag in {"negative_volumetric_soil_water", "volumetric_soil_water_exceeds_unity"}:
                issues.append(_issue(STATUS_REVIEW, flag, 1))
    day_count = len(rows)
    completeness = None if not day_count else 100.0 * complete / day_count
    status = _worst(issues)
    if missing and status == STATUS_VALID:
        status = STATUS_WARNING
    return {
        "days": rows,
        "day_count": day_count,
        "complete_days": complete,
        "missing_days": missing,
        "review_days": review,
        "completeness_pct": completeness,
        "require_complete_days": require_complete_days,
        "theta_bounds": {"min": THETA_INVALID_LOW, "max": THETA_INVALID_HIGH},
        "issues": issues,
        "status": status,
    }


def build_soil_quality_report(
    *,
    dataset_id: str,
    config: dict[str, Any],
    hourly: dict[str, Any],
    daily: dict[str, Any],
    spatial: dict[str, Any] | None,
    coverage: dict[str, Any],
    extra_issues: list[dict[str, Any]] | None = None,
    weather_spatial: dict[str, Any] | None = None,
    grid_comparison: dict[str, Any] | None = None,
) -> dict[str, Any]:
    issues = list(hourly.get("issues") or []) + list(daily.get("issues") or [])
    issues.extend(extra_issues or [])
    status = _worst(issues) if issues else daily.get("status") or hourly.get("status") or STATUS_VALID
    expected = int(coverage.get("expected_days") or 0)
    complete = int(daily.get("complete_days") or 0)
    downloaded = list(coverage.get("downloaded_months") or [])
    expected_months = list(coverage.get("expected_months") or [])
    period = PERIOD_COMPLETE if downloaded == expected_months and expected and complete == expected else PERIOD_INCOMPLETE
    if period == PERIOD_COMPLETE and status in {STATUS_VALID, STATUS_WARNING}:
        readiness = READINESS_LIMITED
        readiness_reason = (
            "Modeled ERA5-Land soil water is complete for the processed period. "
            "It is not independently measured ground truth and does not make "
            "suitable_for_modeling true."
        )
    elif complete:
        readiness = READINESS_LIMITED
        readiness_reason = "Partial modeled soil-water archive; exploratory use only."
    else:
        readiness = READINESS_NOT_READY
        readiness_reason = "No complete modeled soil-water days are available."
    return {
        "dataset_id": dataset_id,
        "status": status,
        "observation_kind": OBSERVATION_KIND,
        "is_ground_truth": False,
        "is_measured_soil_moisture": False,
        "suitable_for_modeling": False,
        "source_integrity": hourly.get("status"),
        "observation_validity": daily.get("status"),
        "period_completeness": period,
        "integration_readiness": READINESS_NOT_READY,
        "modeled_soil_readiness": readiness,
        "modeled_soil_readiness_reason": readiness_reason,
        "hourly": {key: value for key, value in hourly.items() if key != "issues"},
        "daily": {key: value for key, value in daily.items() if key != "days"},
        "spatial": spatial,
        "weather_spatial": weather_spatial,
        "grid_comparison": grid_comparison,
        "coverage": coverage,
        "variables": list(config.get("variables") or []),
        "layers": config.get("layers"),
        "issues": issues,
        "source": config.get("source"),
        "quality_notes": [
            "Volumetric soil water is an instantaneous modeled state (m3 m-3).",
            "Daily means require 24 valid hourly samples; missing hours are never zero-filled.",
            "The 0-100 cm profile mean excludes layer 4 (100-289 cm).",
            "ERA5-Land soil water is not in-situ ground truth.",
        ],
    }
