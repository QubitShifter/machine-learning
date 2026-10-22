"""Issue-time and valid-time contracts for future agricultural forecasts.

This module defines leakage-safe data structures. It does not download ECMWF
Open Data and does not train models.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


FORECAST_CONTRACT_VERSION = "3.4.0"

MODE_OPERATIONAL = "operational_forecast_replay"
MODE_PERFECT_WEATHER = "retrospective_perfect_weather"
FORECAST_MODES = (MODE_OPERATIONAL, MODE_PERFECT_WEATHER)

SOURCE_KIND_REANALYSIS = "historical_reanalysis"
SOURCE_KIND_ARCHIVED_FORECAST = "archived_forecast"
SOURCE_KIND_LIVE_FORECAST = "live_forecast"

HORIZONS_DAYS = (1, 3, 7)

REQUIRED_FORECAST_FIELDS = (
    "forecast_issue_time_utc",
    "forecast_valid_time_utc",
    "lead_time_hours",
    "provider",
    "forecast_model",
    "model_version",
    "variable",
    "unit",
    "source_grid",
    "retrieved_at_utc",
    "source_kind",
)


class ForecastContractError(ValueError):
    """A forecast record violates the leakage or provenance contract."""


def parse_utc(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def lead_time_hours(issue_time: datetime, valid_time: datetime) -> float:
    return (valid_time - issue_time).total_seconds() / 3600.0


def validate_forecast_record(
    record: dict[str, Any],
    *,
    prediction_cutoff_utc: str | datetime | None = None,
    evaluation_mode: str = MODE_OPERATIONAL,
) -> dict[str, Any]:
    """Return a normalized record or raise ForecastContractError."""
    if evaluation_mode not in FORECAST_MODES:
        raise ForecastContractError(
            f"evaluation_mode must be one of {FORECAST_MODES}."
        )
    missing = [field for field in REQUIRED_FORECAST_FIELDS if record.get(field) in (None, "")]
    if missing:
        raise ForecastContractError(f"Forecast record is missing fields: {missing}")

    issue = parse_utc(record.get("forecast_issue_time_utc"))
    valid = parse_utc(record.get("forecast_valid_time_utc"))
    if issue is None or valid is None:
        raise ForecastContractError("forecast issue and valid times must be UTC timestamps.")
    if valid < issue:
        raise ForecastContractError("forecast_valid_time_utc precedes forecast_issue_time_utc.")

    declared_lead = record.get("lead_time_hours")
    computed = lead_time_hours(issue, valid)
    if declared_lead is not None and abs(float(declared_lead) - computed) > 1e-6:
        raise ForecastContractError(
            "lead_time_hours does not match valid time minus issue time."
        )

    source_kind = str(record.get("source_kind"))
    if source_kind == SOURCE_KIND_REANALYSIS and evaluation_mode == MODE_OPERATIONAL:
        raise ForecastContractError(
            "Historical reanalysis cannot masquerade as an archived operational forecast."
        )

    cutoff = parse_utc(prediction_cutoff_utc) if prediction_cutoff_utc is not None else issue
    if evaluation_mode == MODE_OPERATIONAL and issue > cutoff:
        raise ForecastContractError(
            "Forecast issue time is after the allowed prediction cutoff."
        )

    observed = parse_utc(record.get("observed_valid_time_utc"))
    if evaluation_mode == MODE_OPERATIONAL and observed is not None and observed > issue:
        raise ForecastContractError(
            "Future observed weather cannot leak into an operational forecast feature."
        )

    available = parse_utc(record.get("available_at_utc"))
    return {
        **record,
        "forecast_issue_time_utc": issue.isoformat().replace("+00:00", "Z"),
        "forecast_valid_time_utc": valid.isoformat().replace("+00:00", "Z"),
        "lead_time_hours": computed if declared_lead is None else float(declared_lead),
        "available_at_utc": None if available is None else available.isoformat().replace("+00:00", "Z"),
        "evaluation_mode": evaluation_mode,
        "oracle_weather_used": evaluation_mode == MODE_PERFECT_WEATHER,
        "contract_version": FORECAST_CONTRACT_VERSION,
    }


def empty_forecast_archive_note() -> dict[str, Any]:
    return {
        "status": "not_ingested",
        "source": "ecmwf_open_data",
        "official_url": "https://www.ecmwf.int/en/forecasts/datasets/open-data",
        "limitation": (
            "ECMWF Open Data has short rolling retention. A complete 2023-2025 "
            "historical forecast archive is not assumed to be available from that endpoint."
        ),
        "live_download_executed": False,
    }


PREDICTION_TARGETS = {
    "surface_soil_moisture": {
        "horizon_days": HORIZONS_DAYS,
        "allowed_kinds": (
            "direct_observation",
            "remote_sensing_estimate",
            "reanalysis_model_output",
            "derived_scientific_indicator",
            "ml_prediction",
        ),
        "default_kind": "reanalysis_model_output",
        "ground_truth_allowed": False,
        "notes": "ERA5-Land swvl1 is modeled, not a field probe.",
    },
    "root_zone_soil_moisture": {
        "horizon_days": HORIZONS_DAYS,
        "allowed_kinds": (
            "direct_observation",
            "reanalysis_model_output",
            "derived_scientific_indicator",
            "ml_prediction",
        ),
        "default_kind": "reanalysis_model_output",
        "ground_truth_allowed": False,
        "notes": "0-100 cm profile mean is a derived modeled indicator.",
    },
    "soil_drying_wetting_tendency": {
        "horizon_days": HORIZONS_DAYS,
        "allowed_kinds": ("derived_scientific_indicator", "ml_prediction"),
        "default_kind": "derived_scientific_indicator",
        "ground_truth_allowed": False,
    },
    "soil_moisture_anomaly": {
        "horizon_days": HORIZONS_DAYS,
        "allowed_kinds": ("derived_scientific_indicator", "ml_prediction"),
        "default_kind": "derived_scientific_indicator",
        "ground_truth_allowed": False,
    },
    "water_deficit": {
        "horizon_days": HORIZONS_DAYS,
        "allowed_kinds": ("derived_scientific_indicator", "ml_prediction"),
        "default_kind": "derived_scientific_indicator",
        "ground_truth_allowed": False,
        "notes": "Requires field capacity and wilting point; currently not_estimated.",
    },
    "vegetation_ndvi": {
        "horizon_days": HORIZONS_DAYS,
        "allowed_kinds": ("remote_sensing_estimate", "ml_prediction"),
        "default_kind": "remote_sensing_estimate",
        "ground_truth_allowed": False,
    },
    "agricultural_drought": {
        "horizon_days": HORIZONS_DAYS,
        "allowed_kinds": ("derived_scientific_indicator", "ml_prediction"),
        "default_kind": "derived_scientific_indicator",
        "ground_truth_allowed": False,
    },
    "crop_water_stress": {
        "horizon_days": HORIZONS_DAYS,
        "allowed_kinds": ("derived_scientific_indicator", "ml_prediction"),
        "default_kind": "derived_scientific_indicator",
        "ground_truth_allowed": False,
    },
    "irrigation_related_outcome": {
        "horizon_days": HORIZONS_DAYS,
        "allowed_kinds": ("direct_observation", "ml_prediction"),
        "default_kind": "direct_observation",
        "ground_truth_allowed": False,
        "notes": "Irrigation is unknown and must not be assumed zero.",
    },
}


def target_contract(target_id: str) -> dict[str, Any]:
    if target_id not in PREDICTION_TARGETS:
        raise ForecastContractError(f"Unknown prediction target: {target_id}")
    payload = dict(PREDICTION_TARGETS[target_id])
    payload["target_id"] = target_id
    payload["alignment"] = (
        "hat_theta_{t+h} is the state at UTC date t+h, not a trailing h-day mean, "
        "unless a target document explicitly defines an average."
    )
    return payload
