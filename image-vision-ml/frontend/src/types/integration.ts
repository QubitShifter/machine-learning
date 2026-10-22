import type { TaskReadinessReport } from "./api";

export interface IntegrationDatasetSummary {
  dataset_id: string;
  satellite_dataset_id: string | null;
  weather_dataset_id: string | null;
  observation_count: number;
  integrated_observation_complete_count: number;
  weather_feature_window_complete_count: number;
  suitable_for_modeling_count: number;
  integration_version: string | null;
  updated_at: string | null;
}

export interface IntegrationDatasetDetail {
  dataset_id: string;
  satellite_dataset_id: string | null;
  weather_dataset_id: string | null;
  aoi_id: string | null;
  timezone: string;
  integration_version: string | null;
  leakage_policy: string | null;
  same_day_weather: string | null;
  window_rule: string | null;
  observation_count: number;
  satellite_observation_valid_count: number | null;
  weather_feature_window_complete_count: number | null;
  integrated_observation_complete_count: number | null;
  suitable_for_modeling_count: number | null;
  weather_integration_readiness: string | null;
  satellite_supervised_soil_forecasting: string | null;
  dry_day_precipitation_mm: number | null;
  windows_days: number[];
  created_at: string | null;
  updated_at: string | null;
  sources_changed: boolean | null;
}

export interface IntegrationObservation {
  satellite_dataset_id: string | null;
  weather_dataset_id: string | null;
  scene_id: string | null;
  acquisition_timestamp_utc: string | null;
  acquisition_time_precision: string | null;
  observation_date_utc: string | null;
  aoi_id: string | null;
  ndvi_mean: number | null;
  ndvi_minimum: number | null;
  ndvi_maximum: number | null;
  ndvi_median: number | null;
  valid_ndvi_pct: number | null;
  cloud_shadow_fraction_pct: number | null;
  source_crs: string | null;
  pixel_resolution_m: number | null;
  satellite_quality_status: string | null;
  quality_status: string | null;
  precip_prev_7d_mm: number | null;
  precip_prev_14d_mm: number | null;
  precip_prev_30d_mm: number | null;
  temp_mean_prev_7d_c: number | null;
  temp_mean_prev_30d_c: number | null;
  dry_days_prev_30d: number | null;
  rh_mean_prev_7d_pct: number | null;
  wind_mean_prev_7d_ms: number | null;
  evap_prev_7d_mm: number | null;
  evap_prev_30d_mm: number | null;
  window_7d_complete: boolean | null;
  window_14d_complete: boolean | null;
  window_30d_complete: boolean | null;
  window_7d_expected_days: number | null;
  window_14d_expected_days: number | null;
  window_30d_expected_days: number | null;
  window_7d_observed_days: number | null;
  window_14d_observed_days: number | null;
  window_30d_observed_days: number | null;
  window_7d_missing_days: number | null;
  window_14d_missing_days: number | null;
  window_30d_missing_days: number | null;
  window_7d_start_utc: string | null;
  window_7d_end_utc: string | null;
  window_14d_start_utc: string | null;
  window_14d_end_utc: string | null;
  window_30d_start_utc: string | null;
  window_30d_end_utc: string | null;
  source_grid_id: string | null;
  weather_grid_longitude: number | null;
  weather_grid_latitude: number | null;
  weather_grid_distance_km: number | null;
  weather_grid_method: string | null;
  satellite_observation_valid: boolean | null;
  weather_observation_valid: boolean | null;
  weather_feature_window_complete: boolean | null;
  integrated_observation_complete: boolean | null;
  suitable_for_modeling: boolean | null;
  quality_warnings: string[];
  integration_version: string | null;
  satellite_processing_version: string | null;
}

export interface IntegrationObservationPage {
  dataset_id: string;
  total: number;
  offset: number;
  limit: number;
  records: IntegrationObservation[];
}

export interface IntegrationQuality {
  dataset_id: string;
  satellite_dataset_id: string | null;
  weather_dataset_id: string | null;
  integration_version: string | null;
  leakage_policy: string | null;
  same_day_weather: string | null;
  window_rule: string | null;
  observation_count: number;
  satellite_observation_valid_count: number;
  weather_observation_valid_count: number;
  weather_feature_window_complete_count: number;
  integrated_observation_complete_count: number;
  suitable_for_modeling_count: number;
  window_7d_complete_count: number | null;
  window_14d_complete_count: number | null;
  window_30d_complete_count: number | null;
  weather_integration_readiness: string | null;
  satellite_training_readiness: Record<string, unknown> | null;
  task_readiness?: TaskReadinessReport | null;
  suitable_for_modeling_meaning?: string | null;
  weather_spatial: Record<string, unknown> | null;
  issues: Array<Record<string, unknown>>;
  sources_changed: boolean | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface IntegrationFeatureDefinition {
  id: string;
  name?: string;
  unit?: string;
  window_days?: number | null;
  window_definition?: string;
  calculation?: string;
  required_daily_observations?: number | null;
  required_daily_field?: string | null;
  missing_days?: string;
  minimum_coverage?: string;
  feature_validity?: string;
  data_source?: string;
  [key: string]: unknown;
}

export interface IntegrationFeatureCatalog {
  dataset_id: string;
  integration_version: string | null;
  leakage_policy: string | null;
  same_day_weather: string | null;
  window_rule: string | null;
  timezone: string;
  dry_day_precipitation_mm: number | null;
  windows_days: number[];
  quality_dimensions: string[];
  modeling_note: string | null;
  features: IntegrationFeatureDefinition[];
}

export type WeatherWindowDays = 7 | 14 | 30;
export type CoverageKind = "complete" | "partial" | "missing";
export type ObservationFilter = "all" | "complete" | "incomplete";
