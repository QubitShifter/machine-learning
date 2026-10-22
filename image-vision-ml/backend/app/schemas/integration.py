"""Pydantic schemas for the satellite–weather integration API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class IntegrationDatasetSummary(BaseModel):
    dataset_id: str
    satellite_dataset_id: str | None = None
    weather_dataset_id: str | None = None
    observation_count: int = 0
    integrated_observation_complete_count: int = 0
    weather_feature_window_complete_count: int = 0
    suitable_for_modeling_count: int = 0
    integration_version: str | None = None
    updated_at: str | None = None


class IntegrationDatasetListResponse(BaseModel):
    datasets: list[IntegrationDatasetSummary]


class IntegrationDatasetDetailResponse(BaseModel):
    dataset_id: str
    satellite_dataset_id: str | None = None
    weather_dataset_id: str | None = None
    aoi_id: str | None = None
    timezone: str = "UTC"
    integration_version: str | None = None
    leakage_policy: str | None = None
    same_day_weather: str | None = None
    window_rule: str | None = None
    observation_count: int = 0
    satellite_observation_valid_count: int | None = None
    weather_feature_window_complete_count: int | None = None
    integrated_observation_complete_count: int | None = None
    suitable_for_modeling_count: int | None = None
    weather_integration_readiness: str | None = None
    satellite_supervised_soil_forecasting: str | None = None
    dry_day_precipitation_mm: float | None = None
    windows_days: list[int] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None
    sources_changed: bool | None = None


class IntegrationObservation(BaseModel):
    satellite_dataset_id: str | None = None
    weather_dataset_id: str | None = None
    scene_id: str | None = None
    acquisition_timestamp_utc: str | None = None
    acquisition_time_precision: str | None = None
    observation_date_utc: str | None = None
    aoi_id: str | None = None
    ndvi_mean: float | None = None
    ndvi_minimum: float | None = None
    ndvi_maximum: float | None = None
    ndvi_median: float | None = None
    valid_ndvi_pct: float | None = None
    cloud_shadow_fraction_pct: float | None = None
    source_crs: str | None = None
    pixel_resolution_m: float | None = None
    satellite_quality_status: str | None = None
    quality_status: str | None = None
    precip_prev_7d_mm: float | None = None
    precip_prev_14d_mm: float | None = None
    precip_prev_30d_mm: float | None = None
    temp_mean_prev_7d_c: float | None = None
    temp_mean_prev_30d_c: float | None = None
    dry_days_prev_30d: int | None = None
    rh_mean_prev_7d_pct: float | None = None
    wind_mean_prev_7d_ms: float | None = None
    evap_prev_7d_mm: float | None = None
    evap_prev_30d_mm: float | None = None
    window_7d_complete: bool | None = None
    window_14d_complete: bool | None = None
    window_30d_complete: bool | None = None
    window_7d_expected_days: int | None = None
    window_14d_expected_days: int | None = None
    window_30d_expected_days: int | None = None
    window_7d_observed_days: int | None = None
    window_14d_observed_days: int | None = None
    window_30d_observed_days: int | None = None
    window_7d_missing_days: int | None = None
    window_14d_missing_days: int | None = None
    window_30d_missing_days: int | None = None
    window_7d_start_utc: str | None = None
    window_7d_end_utc: str | None = None
    window_14d_start_utc: str | None = None
    window_14d_end_utc: str | None = None
    window_30d_start_utc: str | None = None
    window_30d_end_utc: str | None = None
    source_grid_id: str | None = None
    weather_grid_longitude: float | None = None
    weather_grid_latitude: float | None = None
    weather_grid_distance_km: float | None = None
    weather_grid_method: str | None = None
    satellite_observation_valid: bool | None = None
    weather_observation_valid: bool | None = None
    weather_feature_window_complete: bool | None = None
    integrated_observation_complete: bool | None = None
    suitable_for_modeling: bool | None = None
    quality_warnings: list[str] = Field(default_factory=list)
    integration_version: str | None = None
    satellite_processing_version: str | None = None


class IntegrationObservationListResponse(BaseModel):
    dataset_id: str
    total: int
    offset: int
    limit: int
    records: list[IntegrationObservation] = Field(default_factory=list)


class IntegrationQualityResponse(BaseModel):
    dataset_id: str
    satellite_dataset_id: str | None = None
    weather_dataset_id: str | None = None
    integration_version: str | None = None
    leakage_policy: str | None = None
    same_day_weather: str | None = None
    window_rule: str | None = None
    observation_count: int = 0
    satellite_observation_valid_count: int = 0
    weather_observation_valid_count: int = 0
    weather_feature_window_complete_count: int = 0
    integrated_observation_complete_count: int = 0
    suitable_for_modeling_count: int = 0
    window_7d_complete_count: int | None = None
    window_14d_complete_count: int | None = None
    window_30d_complete_count: int | None = None
    weather_integration_readiness: str | None = None
    satellite_training_readiness: dict[str, Any] | None = None
    task_readiness: dict[str, Any] | None = None
    suitable_for_modeling_meaning: str | None = None
    weather_spatial: dict[str, Any] | None = None
    issues: list[dict[str, Any]] = Field(default_factory=list)
    sources_changed: bool | None = None
    created_at: str | None = None
    updated_at: str | None = None


class IntegrationFeatureCatalogResponse(BaseModel):
    dataset_id: str
    integration_version: str | None = None
    leakage_policy: str | None = None
    same_day_weather: str | None = None
    window_rule: str | None = None
    timezone: str = "UTC"
    dry_day_precipitation_mm: float | None = None
    windows_days: list[int] = Field(default_factory=list)
    quality_dimensions: list[str] = Field(default_factory=list)
    modeling_note: str | None = None
    features: list[dict[str, Any]] = Field(default_factory=list)
