"""Pydantic schemas for the weather analysis API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WeatherDatasetSummary(BaseModel):
    dataset_id: str
    period_start: str | None = None
    period_end: str | None = None
    day_count: int = 0
    complete_days: int = 0
    has_daily: bool = False
    quality_status: str | None = None


class WeatherDatasetListResponse(BaseModel):
    datasets: list[WeatherDatasetSummary]


class WeatherDatasetDetailResponse(BaseModel):
    dataset_id: str
    bbox: list[float] | None = None
    period: dict | None = None
    timezone: str = "UTC"
    source: dict | None = None
    spatial: dict | None = None
    variables: list[str] = Field(default_factory=list)
    day_count: int = 0
    complete_days: int = 0
    quality_status: str | None = None


class DailyWeatherRow(BaseModel):
    date_utc: str | None = None
    aoi_id: str | None = None
    temperature_mean_c: float | None = None
    temperature_min_c: float | None = None
    temperature_max_c: float | None = None
    dewpoint_mean_c: float | None = None
    relative_humidity_mean_pct: float | None = None
    precipitation_total_mm: float | None = None
    wind_speed_mean_ms: float | None = None
    evaporation_total_mm: float | None = None
    hourly_records_expected: int | None = None
    hourly_records_available: int | None = None
    boundary_00utc_available: bool | None = None
    quality_status: str | None = None
    observation_kind: str | None = None
    source_dataset: str | None = None
    source_grid_id: str | None = None


class DailyWeatherResponse(BaseModel):
    dataset_id: str
    total: int
    offset: int
    limit: int
    records: list[DailyWeatherRow]


class WeatherSummaryResponse(BaseModel):
    dataset_id: str
    start_date: str | None = None
    end_date: str | None = None
    day_count: int = 0
    complete_days: int = 0
    temperature_mean_c: float | None = None
    temperature_min_c: float | None = None
    temperature_max_c: float | None = None
    precipitation_total_mm: float | None = None
    relative_humidity_mean_pct: float | None = None
    wind_speed_mean_ms: float | None = None
    evaporation_total_mm: float | None = None


class MonthlyWeatherRow(BaseModel):
    month: str
    day_count: int = 0
    complete_days: int = 0
    missing_days: int = 0
    availability: str | None = None
    temperature_mean_c: float | None = None
    temperature_min_c: float | None = None
    temperature_max_c: float | None = None
    precipitation_total_mm: float | None = None
    evaporation_total_mm: float | None = None
    relative_humidity_mean_pct: float | None = None
    wind_speed_mean_ms: float | None = None


class MonthlyWeatherResponse(BaseModel):
    dataset_id: str
    months: list[MonthlyWeatherRow] = Field(default_factory=list)


class WeatherQualityResponse(BaseModel):
    dataset_id: str
    status: str | None = None
    source_integrity: str | None = None
    observation_validity: str | None = None
    period_completeness: str | None = None
    integration_readiness: str | None = None
    daily: dict[str, Any] = Field(default_factory=dict)
    hourly: dict[str, Any] = Field(default_factory=dict)
    accumulation: dict[str, Any] | None = None
    spatial: dict[str, Any] | None = None
    coverage: dict[str, Any] | None = None
    issues: list[dict[str, Any]] = Field(default_factory=list)


class SatelliteWeatherRow(BaseModel):
    scene_id: str | None = None
    observation_date_utc: str | None = None
    ndvi_mean: float | None = None
    precip_prev_7d_mm: float | None = None
    precip_prev_14d_mm: float | None = None
    precip_prev_30d_mm: float | None = None
    temp_mean_prev_7d_c: float | None = None
    temp_mean_prev_30d_c: float | None = None
    dry_days_prev_30d: int | None = None
    rh_mean_prev_7d_pct: float | None = None
    wind_mean_prev_7d_ms: float | None = None
    window_7d_complete: bool | None = None
    window_14d_complete: bool | None = None
    window_30d_complete: bool | None = None


class SatelliteWeatherResponse(BaseModel):
    dataset_id: str
    satellite_dataset_id: str | None = None
    weather_dataset_id: str | None = None
    observation_count: int = 0
    records: list[SatelliteWeatherRow] = Field(default_factory=list)
