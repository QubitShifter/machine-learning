"""Leakage-safe soil-moisture targets for horizons 1, 3 and 7 days."""

from __future__ import annotations

from datetime import date
from typing import Any

from ml.agricultural_ml.features import index_by_date, soil_day_complete
from ml.agricultural_ml.time_semantics import (
    iso_z,
    last_observation_date,
    parse_utc_date,
    target_date,
    target_period,
)
from ml.preprocessing.soil import SOIL_LAYERS
from ml.preprocessing.weather import _maybe_float


TARGET_FIELDS = {
    "swvl1": "swvl1_mean",
    "swvl2": "swvl2_mean",
    "swvl3": "swvl3_mean",
    "swvl4": "swvl4_mean",
    "theta_root_zone_0_100": "theta_root_zone_0_100",
}

DEPTH_LABELS = {
    "swvl1": "0-7 cm",
    "swvl2": "7-28 cm",
    "swvl3": "28-100 cm",
    "swvl4": "100-289 cm",
    "theta_root_zone_0_100": "0-100 cm weighted profile",
}


def build_targets(
    *,
    issue_dates: list[date],
    soil_rows: list[dict[str, Any]],
    config: dict[str, Any],
    period_end: date,
) -> list[dict[str, Any]]:
    soil_by_date = index_by_date(soil_rows)
    variables = list((config.get("targets") or {}).get("variables") or TARGET_FIELDS)
    horizons = [int(item) for item in (config.get("targets") or {}).get("horizons_days") or (1, 3, 7)]
    sources = config.get("sources") or {}
    rows: list[dict[str, Any]] = []
    for issue_date in issue_dates:
        baseline_date = last_observation_date(issue_date)
        baseline_row = soil_by_date.get(baseline_date)
        for horizon in horizons:
            stamp = target_date(issue_date, horizon)
            period_start, period_end_exclusive = target_period(issue_date, horizon)
            target_row = soil_by_date.get(stamp)
            missing_reason = None
            if stamp > period_end:
                missing_reason = "future_target_outside_dataset_period"
            elif target_row is None:
                missing_reason = "future_target_outside_dataset_period"
            elif not soil_day_complete(target_row):
                missing_reason = "incomplete_target_day"
            for variable in variables:
                field = TARGET_FIELDS[variable]
                absolute = None if missing_reason else _maybe_float(target_row.get(field) if target_row else None)
                if absolute is None and missing_reason is None:
                    missing_reason_local = "missing_target_value"
                else:
                    missing_reason_local = missing_reason
                baseline = _maybe_float(baseline_row.get(field) if soil_day_complete(baseline_row) else None)
                delta = None if absolute is None or baseline is None else float(absolute) - float(baseline)
                layer = SOIL_LAYERS.get(variable) or {}
                rows.append({
                    "dataset_id": config["dataset_id"],
                    "issue_row_key": f"{config['dataset_id']}:{issue_date.isoformat()}",
                    "issue_date_utc": issue_date.isoformat(),
                    "issue_time_utc": f"{issue_date.isoformat()}T00:00:00Z",
                    "last_observation_date_utc": baseline_date.isoformat(),
                    "horizon_days": horizon,
                    "target_variable": variable,
                    "target_field": field,
                    "target_date_utc": stamp.isoformat(),
                    "target_period_start_utc": iso_z(period_start),
                    "target_period_end_utc": iso_z(period_end_exclusive),
                    "target_aggregation": "daily_mean_of_complete_utc_day",
                    "target_kind": "daily_mean_state",
                    "unit": "m3 m-3",
                    "depth_label": DEPTH_LABELS.get(variable),
                    "depth_top_m": layer.get("depth_top_m"),
                    "depth_bottom_m": layer.get("depth_bottom_m"),
                    "absolute_target": absolute,
                    "change_target": delta,
                    "change_baseline_date_utc": baseline_date.isoformat(),
                    "change_baseline_value": baseline,
                    "persistence_prediction": baseline,
                    "missing_reason": missing_reason_local,
                    "target_available": absolute is not None,
                    "source_dataset_id": sources.get("soil_dataset_id"),
                    "source_variable": field,
                    "target_source_kind": "modeled_reanalysis",
                    "is_ground_truth": False,
                    "is_measured_soil_moisture": False,
                    "source_quality_status": None if not target_row else target_row.get("quality_status"),
                    "observation_kind": None if not target_row else target_row.get("observation_kind"),
                })
    return rows


def wide_targets(target_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """One dict per issue_row_key with wide target_* columns."""
    wide: dict[str, dict[str, Any]] = {}
    for row in target_rows:
        key = str(row["issue_row_key"])
        item = wide.setdefault(key, {"issue_row_key": key, "issue_date_utc": row["issue_date_utc"]})
        variable = row["target_variable"]
        horizon = int(row["horizon_days"])
        item[f"target_{variable}_h{horizon}"] = row["absolute_target"]
        item[f"target_{variable}_delta_h{horizon}"] = row["change_target"]
        item[f"target_{variable}_h{horizon}_date"] = row["target_date_utc"]
        item[f"target_{variable}_h{horizon}_missing_reason"] = row["missing_reason"]
    return wide
