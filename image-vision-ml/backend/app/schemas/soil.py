"""Pydantic schemas for modeled soil-moisture and source-registry APIs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SoilDatasetSummary(BaseModel):
    dataset_id: str
    period_start: str | None = None
    period_end: str | None = None
    day_count: int = 0
    complete_days: int = 0
    has_daily: bool = False
    quality_status: str | None = None
    observation_kind: str | None = None
    is_ground_truth: bool = False


class SoilDatasetListResponse(BaseModel):
    datasets: list[SoilDatasetSummary]


class SoilDatasetDetailResponse(BaseModel):
    dataset_id: str
    bbox: list[float] | None = None
    period: dict | None = None
    timezone: str = "UTC"
    source: dict | None = None
    spatial: dict | None = None
    variables: list[str] = Field(default_factory=list)
    layers: dict[str, Any] | None = None
    day_count: int = 0
    complete_days: int = 0
    quality_status: str | None = None
    observation_kind: str | None = None
    is_ground_truth: bool = False
    is_measured_soil_moisture: bool = False
    suitable_for_modeling: bool = False
    unit: str = "m3 m-3"


class DailySoilRow(BaseModel):
    date_utc: str | None = None
    aoi_id: str | None = None
    unit: str | None = None
    observation_kind: str | None = None
    is_ground_truth: bool | None = False
    is_measured_soil_moisture: bool | None = False
    swvl1_mean: float | None = None
    swvl2_mean: float | None = None
    swvl3_mean: float | None = None
    swvl4_mean: float | None = None
    theta_root_zone_0_100: float | None = None
    theta_root_zone_anomaly: float | None = None
    plant_available_water_fraction: float | None = None
    hourly_records_expected: int | None = None
    hourly_records_available: int | None = None
    complete_day: bool | None = None
    quality_status: str | None = None
    source_dataset: str | None = None
    source_grid_id: str | None = None


class DailySoilResponse(BaseModel):
    dataset_id: str
    unit: str = "m3 m-3"
    observation_kind: str = "modeled_volumetric_soil_moisture"
    is_ground_truth: bool = False
    total: int
    offset: int
    limit: int
    records: list[DailySoilRow]


class SoilQualityResponse(BaseModel):
    dataset_id: str
    status: str | None = None
    observation_kind: str | None = None
    is_ground_truth: bool = False
    is_measured_soil_moisture: bool = False
    suitable_for_modeling: bool = False
    source_integrity: str | None = None
    observation_validity: str | None = None
    period_completeness: str | None = None
    modeled_soil_readiness: str | None = None
    modeled_soil_readiness_reason: str | None = None
    daily: dict[str, Any] = Field(default_factory=dict)
    hourly: dict[str, Any] = Field(default_factory=dict)
    spatial: dict[str, Any] | None = None
    grid_comparison: dict[str, Any] | None = None
    coverage: dict[str, Any] | None = None
    issues: list[dict[str, Any]] = Field(default_factory=list)
    quality_notes: list[str] = Field(default_factory=list)


class SourceRegistryResponse(BaseModel):
    title: str | None = None
    verified_at_utc: str | None = None
    counts: dict[str, Any] = Field(default_factory=dict)
    sources: list[dict[str, Any]] = Field(default_factory=list)


class WetnessRow(BaseModel):
    model_config = ConfigDict(extra="allow")
    date_utc: str | None = None
    precipitation_total_mm: float | None = None
    api_k085_mm: float | None = None
    api_k090_mm: float | None = None
    api_k095_mm: float | None = None
    consecutive_dry_days: int | None = None
    days_since_rain: int | None = None
    precip_prev_7d_mm: float | None = None
    precip_prev_14d_mm: float | None = None
    precip_prev_30d_mm: float | None = None
    precip_trailing_7d_end_of_day_mm: float | None = None
    precip_trailing_14d_end_of_day_mm: float | None = None
    precip_trailing_30d_end_of_day_mm: float | None = None
    precip_minus_evap_7d_mm: float | None = None
    precip_minus_evap_30d_mm: float | None = None
    temperature_mean_c: float | None = None
    relative_humidity_mean_pct: float | None = None
    wind_speed_mean_ms: float | None = None
    evaporation_total_mm: float | None = None
    rainfall_history_kind: str | None = None
    wetness_proxy_kind: str | None = None
    is_measured_soil_moisture: bool | None = False
    water_balance_status: str | None = None
    quality_status: str | None = None
    observation_kind: str | None = None
    complete_day: bool | None = None
    hourly_records_available: int | None = None
    hourly_records_expected: int | None = None
    boundary_00utc_available: bool | None = None


class WetnessResponse(BaseModel):
    weather_dataset_id: str
    total: int
    offset: int
    limit: int
    observation_kinds: list[str] = Field(default_factory=list)
    is_measured_soil_moisture: bool = False
    records: list[WetnessRow]
    unit_precipitation: str = "mm"
    includes_forecasts: bool = False


class MonthlySoilRow(BaseModel):
    month: str
    day_count: int = 0
    complete_days: int = 0
    missing_days: int = 0
    availability: str | None = None
    swvl1_mean: float | None = None
    swvl2_mean: float | None = None
    swvl3_mean: float | None = None
    swvl4_mean: float | None = None
    theta_root_zone_0_100_mean: float | None = None
    theta_root_zone_0_100_min: float | None = None
    theta_root_zone_0_100_max: float | None = None
    aggregation: str = "monthly_mean_of_complete_days"
    unit: str = "m3 m-3"
    observation_kind: str = "modeled_volumetric_soil_moisture"


class MonthlySoilResponse(BaseModel):
    dataset_id: str
    unit: str = "m3 m-3"
    observation_kind: str = "modeled_volumetric_soil_moisture"
    is_ground_truth: bool = False
    aggregation: str = "monthly_mean_of_complete_days"
    months: list[MonthlySoilRow]


class CombinedSoilWeatherRow(BaseModel):
    model_config = ConfigDict(extra="allow")
    date_utc: str | None = None
    precipitation_total_mm: float | None = None
    evaporation_total_mm: float | None = None
    api_k090_mm: float | None = None
    consecutive_dry_days: int | None = None
    precip_minus_evap_7d_mm: float | None = None
    swvl1_mean: float | None = None
    swvl2_mean: float | None = None
    swvl3_mean: float | None = None
    swvl4_mean: float | None = None
    theta_root_zone_0_100: float | None = None
    soil_present: bool = False
    weather_present: bool = False
    wetness_present: bool = False
    complete_day_soil: bool | None = None
    quality_status_soil: str | None = None
    quality_status_weather: str | None = None
    observation_kind_soil: str | None = None
    observation_kind_weather: str | None = None
    is_forecast: bool = False
    source_grid_id: str | None = None


class CombinedSoilWeatherResponse(BaseModel):
    soil_dataset_id: str
    weather_dataset_id: str
    unit_soil: str = "m3 m-3"
    unit_precipitation: str = "mm"
    observation_kind_soil: str = "modeled_volumetric_soil_moisture"
    is_ground_truth: bool = False
    is_measured_soil_moisture: bool = False
    spatial: dict[str, Any] | None = None
    lagged_correlation_status: str = "prepared_not_interpreted"
    total: int
    offset: int
    limit: int
    records: list[CombinedSoilWeatherRow]
