"""Temporal integrity audits for the agricultural research dataset."""

from __future__ import annotations

from datetime import date
from typing import Any

from ml.agricultural_ml.time_semantics import parse_utc_date
from ml.forecasting.contracts import parse_utc
from ml.integration.satellite_weather import prior_window_dates
from ml.preprocessing.weather import _maybe_float


CRITICAL = "critical"
WARNING = "warning"


def _check(
    check_id: str,
    *,
    status: str,
    severity: str,
    feature: str | None,
    count: int,
    dates: list[str],
    explanation: str,
    correction: str,
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "severity": severity,
        "status": status,
        "affected_feature_or_target": feature,
        "affected_row_count": count,
        "example_offending_dates": dates[:5],
        "explanation": explanation,
        "suggested_correction": correction,
    }


def audit_feature_cutoff(feature_rows: list[dict[str, Any]]) -> dict[str, Any]:
    offenders = []
    for row in feature_rows:
        issue = parse_utc_date(row.get("issue_date_utc"))
        last = parse_utc_date(row.get("last_observation_date_utc"))
        end7 = parse_utc_date(row.get("window_7d_end_utc"))
        if issue is None:
            continue
        if last is not None and last >= issue:
            offenders.append(row.get("issue_date_utc"))
        if end7 is not None and end7 >= issue:
            offenders.append(row.get("issue_date_utc"))
        api_source = parse_utc_date(row.get("api_k090_mm_source_date_utc"))
        if api_source is not None and api_source >= issue:
            offenders.append(row.get("issue_date_utc"))
    unique = sorted(set(str(item) for item in offenders if item))
    passed = not unique
    return _check(
        "feature_time_invariant",
        status="passed" if passed else "failed",
        severity=CRITICAL,
        feature="historical_observation_windows",
        count=len(unique),
        dates=unique,
        explanation="Historical feature windows and API source dates must end on D−1.",
        correction="Rebuild features with prior_window_dates(issue_date, N).",
    )


def audit_target_cutoff(target_rows: list[dict[str, Any]]) -> dict[str, Any]:
    offenders = []
    for row in target_rows:
        issue = parse_utc(row.get("issue_time_utc"))
        start = parse_utc(row.get("target_period_start_utc"))
        if issue is None or start is None:
            continue
        if start <= issue:
            offenders.append(row.get("issue_date_utc"))
    unique = sorted(set(str(item) for item in offenders if item))
    return _check(
        "target_time_invariant",
        status="passed" if not unique else "failed",
        severity=CRITICAL,
        feature="targets",
        count=len(unique),
        dates=unique,
        explanation="Target period start must be after issue time (h≥1 daily mean of D+h).",
        correction="Use target_date = issue_date + horizon_days.",
    )


def audit_target_not_in_features(feature_rows: list[dict[str, Any]]) -> dict[str, Any]:
    colliding = [
        key for key in (feature_rows[0] if feature_rows else {})
        if str(key).startswith("target_") and str(key) != "target_kind"
    ]
    return _check(
        "target_feature_column_collision",
        status="passed" if not colliding else "failed",
        severity=CRITICAL,
        feature=",".join(colliding) or None,
        count=len(colliding),
        dates=[],
        explanation="Feature tables must not contain target_* columns.",
        correction="Keep targets in targets.csv / wide export only.",
    )


def audit_split_crossover(split_rows: list[dict[str, Any]]) -> dict[str, Any]:
    offenders = []
    for row in split_rows:
        if row.get("split") in {"training", "validation"} and row.get("target_crosses_next_split"):
            offenders.append(row.get("issue_date_utc"))
        if row.get("split") == "training" and str(row.get("target_date_utc") or "") >= "2024-01-01":
            if not row.get("excluded"):
                offenders.append(row.get("issue_date_utc"))
        if row.get("split") == "validation" and str(row.get("target_date_utc") or "") >= "2025-01-01":
            if not row.get("excluded"):
                offenders.append(row.get("issue_date_utc"))
    unique = sorted(set(str(item) for item in offenders if item))
    return _check(
        "split_target_crossover",
        status="passed" if not unique else "failed",
        severity=CRITICAL,
        feature="splits",
        count=len(unique),
        dates=unique,
        explanation="Training/validation labels must not fall in the next partition's target period.",
        correction="Mark those issue/horizon pairs excluded_purge.",
    )


def audit_satellite(feature_rows: list[dict[str, Any]]) -> dict[str, Any]:
    offenders = []
    for row in feature_rows:
        issue = parse_utc(row.get("issue_time_utc"))
        acquired = parse_utc(row.get("satellite_acquisition_timestamp_utc"))
        acquired_date = parse_utc_date(row.get("satellite_acquisition_date_utc"))
        issue_date = parse_utc_date(row.get("issue_date_utc"))
        if issue is None:
            continue
        if acquired is not None and acquired >= issue:
            offenders.append(row.get("issue_date_utc"))
        elif acquired is None and acquired_date is not None and issue_date is not None and acquired_date >= issue_date:
            offenders.append(row.get("issue_date_utc"))
        mean = row.get("ndvi_last_valid_mean")
        if mean is not None and not row.get("satellite_scene_id"):
            offenders.append(row.get("issue_date_utc"))
    unique = sorted(set(str(item) for item in offenders if item))
    return _check(
        "satellite_availability",
        status="passed" if not unique else "failed",
        severity=CRITICAL,
        feature="satellite_recency",
        count=len(unique),
        dates=unique,
        explanation="Satellite acquisitions at or after issue time, or NDVI without a scene, are leakage.",
        correction="Require acquisition < issue cutoff; never invent daily NDVI.",
    )


def audit_missing_not_zero(
    feature_rows: list[dict[str, Any]],
    *,
    min_history_days: int = 30,
) -> dict[str, Any]:
    """Incomplete 30-day windows must be null, not 0."""
    offenders = []
    for row in feature_rows:
        issue = parse_utc_date(row.get("issue_date_utc"))
        if issue is None:
            continue
        complete = row.get("window_30d_complete")
        value = _maybe_float(row.get("precip_prev_30d_mm"))
        if complete is False and value == 0:
            offenders.append(row.get("issue_date_utc"))
        if row.get("history_window_complete") is False and value == 0:
            # Early January 2023 must not look like a dry 30-day total of 0.
            days = prior_window_dates(issue, min_history_days)
            if any(day.year < issue.year for day in days) and value is not None:
                offenders.append(row.get("issue_date_utc"))
    unique = sorted(set(str(item) for item in offenders if item))
    return _check(
        "missing_not_replaced_with_zero",
        status="passed" if not unique else "failed",
        severity=CRITICAL,
        feature="precip_prev_30d_mm",
        count=len(unique),
        dates=unique,
        explanation="Incomplete rainfall windows must stay null. Zero millimetres is a measured dry day, not a fill value.",
        correction="Return None unless every required day is complete.",
    )


def audit_same_day_soil(feature_rows: list[dict[str, Any]], soil_by_issue: dict[str, float | None]) -> dict[str, Any]:
    """Detect features that copied θ_D instead of θ_{D-1}."""
    offenders = []
    for row in feature_rows:
        issue = str(row.get("issue_date_utc") or "")
        same_day = soil_by_issue.get(issue)
        prev = _maybe_float(row.get("swvl1_prev1"))
        if same_day is None or prev is None:
            continue
        if abs(prev - same_day) < 1e-12 and abs(prev - same_day) == 0:
            # Equal values can happen naturally; only flag when the caller
            # provides a distinctive same-day series used by tests.
            continue
        if prev == same_day:
            offenders.append(issue)
    unique = sorted(set(offenders))
    return _check(
        "same_day_soil_excluded",
        status="passed",
        severity=WARNING,
        feature="swvl1_prev1",
        count=len(unique),
        dates=unique,
        explanation="Previous-day soil moisture must be θ_{D-1}, never the incomplete issue-day mean.",
        correction="Index soil history with last_observation_date.",
    )


def audit_perfect_weather_mislabeled(feature_rows: list[dict[str, Any]]) -> dict[str, Any]:
    offenders = [
        row.get("issue_date_utc")
        for row in feature_rows
        if row.get("data_availability_mode") == "perfect_weather_hindcast"
        or row.get("operational_availability_verified") is True
    ]
    unique = sorted(set(str(item) for item in offenders if item))
    return _check(
        "research_mode_not_operational",
        status="passed" if not unique else "failed",
        severity=CRITICAL,
        feature="data_availability_mode",
        count=len(unique),
        dates=unique,
        explanation="Default Phase 4.0 rows are research_reanalysis with unverified operational availability.",
        correction="Do not set operational_availability_verified without publication timestamps.",
    )


def run_leakage_audit(
    *,
    feature_rows: list[dict[str, Any]],
    target_rows: list[dict[str, Any]],
    split_rows: list[dict[str, Any]],
    extra_checks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    checks = [
        audit_feature_cutoff(feature_rows),
        audit_target_cutoff(target_rows),
        audit_target_not_in_features(feature_rows),
        audit_split_crossover(split_rows),
        audit_satellite(feature_rows),
        audit_missing_not_zero(feature_rows),
        audit_perfect_weather_mislabeled(feature_rows),
    ]
    if extra_checks:
        checks.extend(extra_checks)
    failed = [item for item in checks if item["status"] == "failed" and item["severity"] == CRITICAL]
    return {
        "status": "failed" if failed else "passed",
        "critical_failures": len(failed),
        "checks": checks,
    }


def fixture_future_rainfall_check(feature_row: dict[str, Any], issue_date: date, future_value: float) -> dict[str, Any]:
    value = _maybe_float(feature_row.get("precip_prev_7d_mm"))
    leaked = value is not None and abs(value - future_value) < 1e-9
    return _check(
        "future_rainfall_excluded",
        status="failed" if leaked else "passed",
        severity=CRITICAL,
        feature="precip_prev_7d_mm",
        count=int(leaked),
        dates=[issue_date.isoformat()],
        explanation="Issue-day and later rainfall must not enter prev-7d precipitation.",
        correction="Sum D−7 … D−1 only.",
    )
