"""Feature and target catalogs for the agricultural research dataset."""

from __future__ import annotations

from typing import Any

from ml.agricultural_ml.features import SOIL_SERIES, api_key
from ml.agricultural_ml.targets import DEPTH_LABELS, TARGET_FIELDS


def _item(**payload: Any) -> dict[str, Any]:
    payload.setdefault("missing_data_policy", "null unless every required complete UTC day is present")
    payload.setdefault("spatial_provenance", "ERA5-Land nearest grid cell to the study AOI")
    payload.setdefault("observation_cutoff", "completed UTC days D−N through D−1")
    payload.setdefault("validation_status", "implemented")
    return payload


def feature_catalog(config: dict[str, Any]) -> dict[str, Any]:
    windows = list(config.get("feature_windows_days") or [1, 3, 7, 14, 30])
    features = []
    for name, field in SOIL_SERIES:
        features.append(_item(
            feature_id=f"soil.{name}_prev1",
            column_name=f"{name}_prev1",
            input_source="daily_soil.csv",
            source_variable=field,
            formula=f"{field} on D−1",
            units="m3 m-3",
            temporal_window="D-1",
            implementation="ml.agricultural_ml.features.soil_history_features",
        ))
        features.append(_item(
            feature_id=f"soil.{name}_delta_prev1",
            column_name=f"{name}_delta_prev1",
            input_source="daily_soil.csv",
            source_variable=field,
            formula=f"{field}(D−1) − {field}(D−2)",
            units="m3 m-3",
            temporal_window="D-2 to D-1",
            implementation="ml.agricultural_ml.features.soil_history_features",
        ))
        for window in windows:
            features.append(_item(
                feature_id=f"soil.{name}_prev{window}d_mean",
                column_name=f"{name}_prev{window}d_mean",
                input_source="daily_soil.csv",
                source_variable=field,
                formula=f"(1/{window}) * sum_{{i=1..{window}}} {field}(D−i)",
                units="m3 m-3",
                temporal_window=f"D-{window} through D-1",
                implementation="ml.agricultural_ml.features.soil_history_features",
            ))
            if window in {3, 7, 14}:
                features.append(_item(
                    feature_id=f"soil.{name}_prev{window}d_slope",
                    column_name=f"{name}_prev{window}d_slope",
                    input_source="daily_soil.csv",
                    source_variable=field,
                    formula=f"({field}(D−1) − {field}(D−{window})) / ({window}−1)",
                    units="m3 m-3 day-1",
                    temporal_window=f"D-{window} through D-1",
                    implementation="ml.agricultural_ml.features.slope",
                ))
    for window in windows:
        features.append(_item(
            feature_id=f"weather.precip_prev_{window}d_mm",
            column_name=f"precip_prev_{window}d_mm",
            input_source="daily_weather.csv",
            source_variable="precipitation_total_mm",
            formula=f"sum_{{i=1..{window}}} P(D−i)",
            units="mm",
            temporal_window=f"D-{window} through D-1",
            implementation="ml.agricultural_ml.features.weather_history_features",
        ))
    for k in (config.get("api") or {}).get("k_factors") or [0.85, 0.90, 0.95]:
        key = api_key(float(k))
        features.append(_item(
            feature_id=f"weather.{key}",
            column_name=key,
            input_source="daily_weather.csv",
            source_variable="precipitation_total_mm",
            formula=f"API_t = P_t + {k} API_{{t-1}} evaluated at t=D−1",
            units="mm",
            temporal_window="end-of-day API on D-1",
            implementation="ml.preprocessing.wetness.antecedent_precipitation_index",
            documentation_reference="docs/features/weather/antecedent_precipitation_index.md",
        ))
    features.extend([
        _item(
            feature_id="weather.temp_prev1_c",
            column_name="temp_prev1_c",
            input_source="daily_weather.csv",
            source_variable="temperature_mean_c",
            formula="temperature_mean_c on D−1",
            units="degC",
            temporal_window="D-1",
            implementation="ml.agricultural_ml.features.weather_history_features",
        ),
        _item(
            feature_id="weather.temp_mean_prev_7d_c",
            column_name="temp_mean_prev_7d_c",
            input_source="daily_weather.csv",
            source_variable="temperature_mean_c",
            formula="(1/7) * sum_{i=1..7} temperature_mean_c(D−i)",
            units="degC",
            temporal_window="D-7 through D-1",
            implementation="ml.agricultural_ml.features.weather_history_features",
        ),
        _item(
            feature_id="weather.rh_prev1_pct",
            column_name="rh_prev1_pct",
            input_source="daily_weather.csv",
            source_variable="relative_humidity_mean_pct",
            formula="relative_humidity_mean_pct on D−1",
            units="percent",
            temporal_window="D-1",
            implementation="ml.agricultural_ml.features.weather_history_features",
        ),
        _item(
            feature_id="weather.evap_prev_7d_mm",
            column_name="evap_prev_7d_mm",
            input_source="daily_weather.csv",
            source_variable="evaporation_total_mm",
            formula="sum_{i=1..7} E(D−i); ERA5-Land evaporation, not crop ET",
            units="mm",
            temporal_window="D-7 through D-1",
            implementation="ml.agricultural_ml.features.weather_history_features",
        ),
        _item(
            feature_id="weather.consecutive_dry_days",
            column_name="consecutive_dry_days",
            input_source="daily_weather.csv",
            source_variable="precipitation_total_mm",
            formula="run of days with P < dry_day_mm ending on D−1",
            units="days",
            temporal_window="through D-1",
            implementation="ml.preprocessing.wetness.consecutive_dry_days",
        ),
        _item(
            feature_id="calendar.day_of_year_sin",
            column_name="day_of_year_sin",
            input_source="issue_date_utc",
            source_variable="calendar",
            formula="sin(2π (doy-1) / L) with L=365 or 366",
            units="dimensionless",
            temporal_window="known at issue time",
            observation_cutoff="not an observation",
            implementation="ml.agricultural_ml.time_semantics.calendar_features",
        ),
        _item(
            feature_id="calendar.day_of_year_cos",
            column_name="day_of_year_cos",
            input_source="issue_date_utc",
            source_variable="calendar",
            formula="cos(2π (doy-1) / L) with L=365 or 366",
            units="dimensionless",
            temporal_window="known at issue time",
            observation_cutoff="not an observation",
            implementation="ml.agricultural_ml.time_semantics.calendar_features",
        ),
        _item(
            feature_id="satellite.ndvi_last_valid_mean",
            column_name="ndvi_last_valid_mean",
            input_source="processed Sentinel-2 quality scenes",
            source_variable="ndvi_mean",
            formula="NDVI of the latest eligible scene with acquisition < issue cutoff and age ≤ max_age_days",
            units="NDVI",
            temporal_window="sparse, quality-gated",
            missing_data_policy="null when missing, stale, rejected, or calibration-review",
            spatial_provenance="10 m Sentinel-2 AOI, not the ERA5-Land cell",
            implementation="ml.agricultural_ml.satellite.satellite_features_for_issue",
        ),
    ])
    return {
        "dataset_id": config["dataset_id"],
        "feature_version": config.get("dataset_version"),
        "count": len(features),
        "features": features,
    }


def target_catalog(config: dict[str, Any]) -> dict[str, Any]:
    horizons = list((config.get("targets") or {}).get("horizons_days") or [1, 3, 7])
    targets = []
    for variable, field in TARGET_FIELDS.items():
        for horizon in horizons:
            targets.append({
                "target_id": f"target_{variable}_h{horizon}",
                "change_target_id": f"target_{variable}_delta_h{horizon}",
                "source_variable": field,
                "depth": DEPTH_LABELS[variable],
                "horizon_days": horizon,
                "formula_absolute": f"daily mean {field} on UTC date D+{horizon}",
                "formula_change": f"absolute_target − {field}(D−1)",
                "unit": "m3 m-3",
                "aggregation": "daily_mean_of_complete_utc_day",
                "target_kind": "daily_mean_state",
                "target_source_kind": "modeled_reanalysis",
                "is_ground_truth": False,
                "target_period": f"[D+{horizon} 00:00 UTC, D+{horizon}+1 00:00 UTC)",
            })
    return {
        "dataset_id": config["dataset_id"],
        "count": len(targets),
        "targets": targets,
    }
