"""Documented historical weather-feature definitions for satellite integration.

Window math lives in ``ml.integration.satellite_weather``. This module is the
canonical description of units, coverage rules, and provenance — not a second
implementation of the aggregations.
"""

from __future__ import annotations

from typing import Any


INTEGRATION_VERSION = "3.2.0"
LEAKAGE_POLICY = "previous_completed_utc_days_only"
SAME_DAY_POLICY = "excluded"
DRY_DAY_THRESHOLD_MM = 1.0
DEFAULT_WINDOWS = (7, 14, 30)

WINDOW_RULE = (
    "For a Sentinel-2 acquisition whose UTC calendar date is D, a prior-N-day "
    "feature uses fully completed ERA5-Land UTC days D−N through D−1 inclusive. "
    "The acquisition day D is excluded, not truncated to hours before overpass. "
    "No same-day weather and no later weather enter the feature. Missing daily "
    "values stay missing; they are never replaced with zero. A window aggregate "
    "is emitted only when every expected day is a complete valid observation of "
    "that variable."
)


def feature_catalog(
    *,
    dry_day_mm: float = DRY_DAY_THRESHOLD_MM,
    windows: tuple[int, ...] = DEFAULT_WINDOWS,
) -> list[dict[str, Any]]:
    """Return JSON-serialisable feature definitions for the current contract."""
    window_list = list(windows)
    catalog = [
        _precip(7, "Prior 7-day precipitation total"),
        _precip(14, "Prior 14-day precipitation total"),
        _precip(30, "Prior 30-day precipitation total"),
        _mean_temp(7, "Prior 7-day mean temperature"),
        _mean_temp(30, "Prior 30-day mean temperature"),
        {
            "id": "dry_days_prev_30d",
            "name": "Prior 30-day dry-day count",
            "unit": "days",
            "window_days": 30,
            "window_definition": "UTC days D−30 … D−1",
            "calculation": (
                f"Count of window days with precipitation_total_mm < {dry_day_mm} mm. "
                "Requires the same complete 30-day precipitation window as precip_prev_30d_mm."
            ),
            "required_daily_observations": 30,
            "required_daily_field": "precipitation_total_mm",
            "missing_days": "If any window day is missing or incomplete, the count is null.",
            "minimum_coverage": "30 of 30 complete valid UTC days",
            "feature_validity": "Valid only when window_30d_complete is true.",
            "data_source": "ERA5-Land total_precipitation, daily UTC accumulation",
        },
        _mean_rh(7),
        _mean_wind(7),
        _evap(7, "Prior 7-day evaporation total"),
        _evap(30, "Prior 30-day evaporation total"),
        {
            "id": "ndvi_mean",
            "name": "Mean NDVI",
            "unit": "NDVI",
            "window_days": None,
            "window_definition": "Validated Sentinel-2 scene, SCL 4+5 land pixels",
            "calculation": "Mean of valid NDVI pixels inside the study AOI.",
            "required_daily_observations": None,
            "required_daily_field": None,
            "missing_days": "Not a weather feature.",
            "minimum_coverage": "Scene quality policy (valid NDVI percentage).",
            "feature_validity": "Valid when satellite_observation_valid is true.",
            "data_source": "Processed Sentinel-2 L2A NDVI raster",
        },
    ]
    return [
        item for item in catalog
        if item.get("window_days") is None or item["window_days"] in window_list
        or item["id"] == "ndvi_mean"
    ]


def feature_metadata(
    *,
    dry_day_mm: float = DRY_DAY_THRESHOLD_MM,
    windows: tuple[int, ...] = DEFAULT_WINDOWS,
) -> dict[str, Any]:
    return {
        "integration_version": INTEGRATION_VERSION,
        "leakage_policy": LEAKAGE_POLICY,
        "same_day_weather": SAME_DAY_POLICY,
        "window_rule": WINDOW_RULE,
        "timezone": "UTC",
        "dry_day_precipitation_mm": dry_day_mm,
        "windows_days": list(windows),
        "features": feature_catalog(dry_day_mm=dry_day_mm, windows=windows),
        "quality_dimensions": [
            "satellite_observation_valid",
            "weather_observation_valid",
            "weather_feature_window_complete",
            "integrated_observation_complete",
            "suitable_for_modeling",
        ],
        "modeling_note": (
            "suitable_for_modeling is true only when the satellite observation is "
            "valid, weather-grid provenance is valid, every historical weather "
            "window is complete, weather integration_readiness is ready, and "
            "satellite supervised-soil-forecasting readiness is ready. A complete "
            "window on a sparse NDVI archive is not sufficient for supervised "
            "soil-moisture training."
        ),
    }


def _precip(window: int, name: str) -> dict[str, Any]:
    return {
        "id": f"precip_prev_{window}d_mm",
        "name": name,
        "unit": "mm",
        "window_days": window,
        "window_definition": f"UTC days D−{window} … D−1",
        "calculation": "Sum of daily precipitation_total_mm over the window.",
        "required_daily_observations": window,
        "required_daily_field": "precipitation_total_mm",
        "missing_days": "Any missing or incomplete day yields a null total. Days are not filled with 0 mm.",
        "minimum_coverage": f"{window} of {window} complete valid UTC days",
        "feature_validity": f"Valid only when window_{window}d_complete is true.",
        "data_source": "ERA5-Land total_precipitation, daily UTC accumulation",
    }


def _mean_temp(window: int, name: str) -> dict[str, Any]:
    return {
        "id": f"temp_mean_prev_{window}d_c",
        "name": name,
        "unit": "°C",
        "window_days": window,
        "window_definition": f"UTC days D−{window} … D−1",
        "calculation": "Arithmetic mean of daily temperature_mean_c over the window.",
        "required_daily_observations": window,
        "required_daily_field": "temperature_mean_c",
        "missing_days": "Any missing temperature day yields a null mean.",
        "minimum_coverage": f"{window} of {window} complete valid UTC days",
        "feature_validity": (
            f"Temperature may be null even when window_{window}d_complete is true "
            "if precipitation coverage is complete but temperature is not."
        ),
        "data_source": "ERA5-Land 2m_temperature, daily UTC mean",
    }


def _mean_rh(window: int) -> dict[str, Any]:
    return {
        "id": "rh_mean_prev_7d_pct",
        "name": "Prior 7-day relative humidity mean",
        "unit": "%",
        "window_days": window,
        "window_definition": f"UTC days D−{window} … D−1",
        "calculation": "Arithmetic mean of daily relative_humidity_mean_pct.",
        "required_daily_observations": window,
        "required_daily_field": "relative_humidity_mean_pct",
        "missing_days": "Any missing humidity day yields a null mean.",
        "minimum_coverage": f"{window} of {window} complete valid UTC days",
        "feature_validity": "Valid only when all seven humidity observations are present.",
        "data_source": "ERA5-Land, derived from 2 m temperature and dewpoint",
    }


def _mean_wind(window: int) -> dict[str, Any]:
    return {
        "id": "wind_mean_prev_7d_ms",
        "name": "Prior 7-day wind-speed mean",
        "unit": "m/s",
        "window_days": window,
        "window_definition": f"UTC days D−{window} … D−1",
        "calculation": "Arithmetic mean of daily wind_speed_mean_ms.",
        "required_daily_observations": window,
        "required_daily_field": "wind_speed_mean_ms",
        "missing_days": "Any missing wind day yields a null mean.",
        "minimum_coverage": f"{window} of {window} complete valid UTC days",
        "feature_validity": "Valid only when all seven wind observations are present.",
        "data_source": "ERA5-Land 10 m u/v wind components, daily mean speed",
    }


def _evap(window: int, name: str) -> dict[str, Any]:
    return {
        "id": f"evap_prev_{window}d_mm",
        "name": name,
        "unit": "mm",
        "window_days": window,
        "window_definition": f"UTC days D−{window} … D−1",
        "calculation": (
            "Sum of daily evaporation_total_mm over the window. ERA5-Land "
            "total_evaporation is stored as positive-upward millimetres after the "
            "documented sign conversion. Included as a water-balance historical "
            "aggregate using the same complete-window rule as precipitation."
        ),
        "required_daily_observations": window,
        "required_daily_field": "evaporation_total_mm",
        "missing_days": "Any missing evaporation day yields a null total.",
        "minimum_coverage": f"{window} of {window} complete valid UTC days",
        "feature_validity": (
            "Independent of the precipitation completeness flag; null unless every "
            "window day has evaporation_total_mm."
        ),
        "data_source": "ERA5-Land total_evaporation, daily UTC accumulation, positive upward",
    }
