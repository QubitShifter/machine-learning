export interface SatelliteDatasetSummary {
  dataset_id: string;
  period_start: string | null;
  period_end: string | null;
  scene_count: number;
  processed_count: number;
  has_timeseries: boolean;
}

export interface SatelliteDatasetDetail {
  dataset_id: string;
  bbox: number[] | null;
  period: { start?: string; end?: string } | null;
  collection: string | null;
  processing_version: string | null;
  target_grid: {
    crs?: string;
    width?: number;
    height?: number;
    resolution?: number[];
    bounds?: number[];
  } | null;
  scene_count: number;
  processed_count: number;
  statuses: Record<string, number>;
}

export interface SatelliteSceneRecord {
  scene_id: string;
  acquisition_date: string | null;
  status: string | null;
  platform: string | null;
  cloud_cover: number | null;
  aoi_coverage: number | null;
  valid_percentage: number | null;
  overlay_ready: boolean;
}

export interface MapOverlayMetadata {
  scene_id: string;
  overlay_available: boolean;
  supported_modes: string[];
  unavailable_reason: string | null;
  native_crs: string | null;
  native_width: number | null;
  native_height: number | null;
  native_pixel_size_m: number[] | null;
  native_bounds: {
    crs?: string;
    west?: number;
    south?: number;
    east?: number;
    north?: number;
    coordinate_order?: string;
  } | null;
  rendered_crs: string | null;
  rendered_width: number | null;
  rendered_height: number | null;
  rendered_resolution_m: number[] | null;
  rendered_downsampled: boolean;
  geographic_extent: {
    crs?: string;
    west?: number;
    south?: number;
    east?: number;
    north?: number;
  } | null;
  maplibre_coordinates: number[][] | null;
  valid_mask_policy: string | null;
  render_version: string | null;
  cache_id: string | null;
  ndvi_color_scale: Array<{ value: number; color_rgb: number[] }>;
  scl_legend?: Array<{ code: number; name: string; color_rgb: number[]; transparent?: boolean }>;
  scl_provenance?: {
    source?: string;
    native_resolution_m?: number;
    target_grid_resolution_m?: number;
    alignment?: string;
    resampling_forbidden?: string;
    native_20m_mixed_with_10m_counts?: boolean;
    overlay_policy?: string;
  } | null;
  quality_limitations: string[];
}

export interface PixelInspect {
  scene_id: string;
  acquisition_date: string | null;
  longitude: number;
  latitude: number;
  crs: string;
  coverage_state: string;
  inside_raster: boolean;
  valid: boolean;
  row: number | null;
  col: number | null;
  sampling: string;
  red_b04: number | null;
  green_b03: number | null;
  blue_b02: number | null;
  nir_b08: number | null;
  ndvi: number | null;
  scl_class: number | null;
  scl_class_name: string | null;
  valid_mask: boolean | null;
  exclusion_reason: string | null;
  calibration_status: string | null;
  scene_quality_status: string | null;
  missing_reasons: Record<string, string>;
  message: string | null;
  source: string;
  estimated_from_display_rgb: boolean;
}

export interface AoiArea {
  aoi_id: string;
  name: string;
  status: string;
  bbox: number[];
  satellite_dataset_id?: string | null;
  weather_dataset_id?: string | null;
  soil_dataset_id?: string | null;
  mutable?: boolean;
  downloads_allowed?: boolean;
  notes?: string | null;
  geometry?: {
    area_km2?: number;
    approximate_10m_pixels?: number;
    approximate_era5_cells?: number;
    sentinel2_note?: string;
    weather_note?: string;
  } | null;
}

export interface AoiDraft {
  draft_id: string;
  name: string | null;
  status: string;
  created_at: string;
  geometry: {
    type: string;
    bbox: number[];
    coordinates: number[][];
    area_km2?: number;
    approximate_10m_pixels?: number;
    approximate_era5_cells?: number;
  };
  downloads_started: boolean;
  operational: boolean;
  note?: string | null;
}

export interface AoiRegistry {
  version: string | null;
  operational_count: number;
  areas: AoiArea[];
  drafts: AoiDraft[];
  note: string | null;
}

export interface NdviSample {
  scene_id: string;
  longitude: number;
  latitude: number;
  crs: string;
  inside_raster: boolean;
  valid: boolean;
  ndvi: number | null;
  sampling: string;
  message: string | null;
}

export interface TimeseriesObservation {
  scene_id: string | null;
  date: string | null;
  mean: number | null;
  median: number | null;
  valid_percentage: number | null;
}

export interface SceneQuality {
  scene_id: string | null;
  acquisition_date: string | null;
  satellite_platform: string | null;
  quality_status: string | null;
  scene_quality_status?: string | null;
  calibration_status?: string | null;
  scene_quality_reasons?: string[];
  reasons: string[];
  exclusion_counts?: Record<string, unknown> | null;
  geometric_footprint_overlap_pct: number | null;
  actual_aoi_coverage_pct: number | null;
  valid_ndvi_pct: number | null;
  ndvi_minimum: number | null;
  ndvi_mean: number | null;
  ndvi_maximum: number | null;
  ndvi_median: number | null;
  cloud_shadow_fraction_pct: number | null;
  valid_pixels: number | null;
  total_aoi_pixels: number | null;
  grid_aligned: boolean | null;
  calibration: Record<string, unknown> | null;
  missing_assets: string[];
}

export interface SatelliteQuality {
  dataset_id: string;
  dataset: {
    validated_scenes?: number;
    rejected_scenes?: number;
    requires_review_scenes?: number;
    downloaded_scenes?: number;
    processed_scenes?: number;
    [key: string]: unknown;
  };
  training_readiness: {
    overall?: string;
    historical_satellite_analysis?: string;
    supervised_soil_forecasting?: string;
    [key: string]: unknown;
  } | null;
  coverage?: {
    catalog_known?: boolean;
    months?: Array<{
      month: string;
      discovered_candidate_scenes: number | null;
      ingested_scenes: number;
      validated_observations: number;
      requires_review: number;
      rejected: number;
      coverage_status: string;
      available_acquisition_dates?: string[];
    }>;
    summary?: Record<string, unknown>;
  } | null;
  calibration_audit?: {
    unresolved_scene_ids?: string[];
    calibration_consistency?: boolean;
    scenes?: Array<Record<string, unknown>>;
  } | null;
  task_readiness?: TaskReadinessReport | null;
  scene_count: number;
}

export interface TaskReadinessAssessment {
  task: string;
  status: string;
  reasons: string[];
  warnings: string[];
  blocking_conditions?: string[];
  metrics?: Record<string, unknown>;
  explanation?: string;
  recommended_next_steps?: string[];
}

export interface TaskReadinessReport {
  tasks?: TaskReadinessAssessment[];
  by_task?: Record<string, TaskReadinessAssessment>;
  thresholds?: Record<string, unknown>;
  threshold_justification?: string;
  suitable_for_modeling_meaning?: string;
}

export interface WeatherDatasetSummary {
  dataset_id: string;
  period_start: string | null;
  period_end: string | null;
  day_count: number;
  complete_days: number;
  has_daily: boolean;
  quality_status: string | null;
}

export interface WeatherDatasetDetail {
  dataset_id: string;
  bbox: number[] | null;
  period: { start?: string; end?: string } | null;
  timezone: string;
  source: Record<string, unknown> | null;
  spatial: {
    method?: string;
    source_longitude?: number;
    source_latitude?: number;
    distance_km?: number;
    native_resolution_deg?: number;
    query_longitude?: number;
    query_latitude?: number;
    [key: string]: unknown;
  } | null;
  variables: string[];
  day_count: number;
  complete_days: number;
  quality_status: string | null;
}

export interface DailyWeatherRow {
  date_utc: string | null;
  aoi_id: string | null;
  temperature_mean_c: number | null;
  temperature_min_c: number | null;
  temperature_max_c: number | null;
  dewpoint_mean_c: number | null;
  relative_humidity_mean_pct: number | null;
  precipitation_total_mm: number | null;
  wind_speed_mean_ms: number | null;
  evaporation_total_mm: number | null;
  hourly_records_expected: number | null;
  hourly_records_available: number | null;
  boundary_00utc_available: boolean | null;
  quality_status: string | null;
  observation_kind: string | null;
  source_dataset: string | null;
  source_grid_id: string | null;
}

export interface WeatherSummary {
  dataset_id: string;
  start_date: string | null;
  end_date: string | null;
  day_count: number;
  complete_days: number;
  temperature_mean_c: number | null;
  temperature_min_c: number | null;
  temperature_max_c: number | null;
  precipitation_total_mm: number | null;
  relative_humidity_mean_pct: number | null;
  wind_speed_mean_ms: number | null;
  evaporation_total_mm: number | null;
}

export interface MonthlyWeatherRow {
  month: string;
  day_count: number;
  complete_days: number;
  missing_days: number;
  availability: string | null;
  temperature_mean_c: number | null;
  temperature_min_c: number | null;
  temperature_max_c: number | null;
  precipitation_total_mm: number | null;
  evaporation_total_mm: number | null;
  relative_humidity_mean_pct: number | null;
  wind_speed_mean_ms: number | null;
}

export interface WeatherQuality {
  dataset_id: string;
  status: string | null;
  source_integrity: string | null;
  observation_validity: string | null;
  period_completeness: string | null;
  integration_readiness: string | null;
  daily: {
    day_count?: number;
    complete_days?: number;
    missing_days?: number;
    incomplete_days?: number;
    completeness_pct?: number | null;
    statuses?: Record<string, number>;
  };
  hourly: {
    hourly_records?: number;
    unique_timestamps?: number;
    expected_boundary_overlaps?: number;
    status?: string;
    accumulation?: Record<string, unknown>;
    [key: string]: unknown;
  };
  accumulation: Record<string, unknown> | null;
  spatial: Record<string, unknown> | null;
  coverage: {
    expected_months?: string[];
    downloaded_months?: string[];
    missing_months?: string[];
    month_availability?: Record<string, string>;
    expected_days?: number;
    processed_start?: string;
    processed_end?: string;
  } | null;
  issues: Array<{
    severity?: string;
    code?: string;
    count?: number;
    [key: string]: unknown;
  }>;
}

export interface SoilDatasetSummary {
  dataset_id: string;
  period_start: string | null;
  period_end: string | null;
  day_count: number;
  complete_days: number;
  has_daily: boolean;
  quality_status: string | null;
  observation_kind: string | null;
  is_ground_truth: boolean;
}

export interface SoilQuality {
  dataset_id: string;
  status: string | null;
  observation_kind: string | null;
  is_ground_truth: boolean;
  is_measured_soil_moisture: boolean;
  suitable_for_modeling: boolean;
  source_integrity: string | null;
  observation_validity: string | null;
  period_completeness: string | null;
  modeled_soil_readiness: string | null;
  modeled_soil_readiness_reason: string | null;
  daily: {
    day_count?: number;
    complete_days?: number;
    missing_days?: number;
    completeness_pct?: number | null;
  };
  spatial: Record<string, unknown> | null;
  grid_comparison: {
    same_grid_cell?: boolean | null;
    [key: string]: unknown;
  } | null;
  coverage: {
    downloaded_months?: string[];
    missing_months?: string[];
    expected_days?: number;
  } | null;
  issues: Array<{ severity?: string; code?: string; count?: number }>;
  quality_notes: string[];
}

export interface HistogramBin {
  index: number;
  edge_left: number;
  edge_right: number;
  center: number;
  count: number;
  percent_of_valid: number | null;
  percent_of_total: number | null;
}

export interface HistogramStatistics {
  count: number;
  mean: number | null;
  median: number | null;
  standard_deviation: number | null;
  minimum: number | null;
  maximum: number | null;
  p10: number | null;
  p90: number | null;
  p99?: number | null;
}

export interface HistogramSeries {
  unit?: string;
  band?: string;
  domain: number[];
  bins: number;
  binning?: string;
  histogram: HistogramBin[];
  counts?: number[];
  in_range_count?: number;
  out_of_range_count?: number;
  nonfinite_unmasked_count?: number;
  masked_or_nodata_count: number;
  total_pixels: number;
  valid_pixel_count: number;
  valid_percentage: number | null;
  histogrammed_count?: number;
  masked_count?: number;
  nonfinite_count?: number;
  out_of_domain_count?: number;
  pixel_conservation_ok?: boolean;
  clamped?: boolean;
  masked_treated_as_zero?: boolean;
  statistics: HistogramStatistics;
  calibration?: {
    scale?: number;
    offset?: number;
    source?: string;
    [key: string]: unknown;
  } | null;
  is_display_rgb?: boolean;
}

export interface SclClassRow {
  code: number;
  name: string;
  count: number;
  percent: number | null;
}

export interface SclGroupRow {
  group: string;
  codes: number[];
  count: number;
  percent: number | null;
}

export interface SceneHistograms {
  dataset_id: string | null;
  scene_id: string | null;
  histogram_version: string | null;
  pixel_exclusion_version?: string | null;
  processing_version: string | null;
  acquisition_date: string | null;
  scene_quality_status: string | null;
  calibration_status: string | null;
  scientific_use: string | null;
  warnings: string[];
  ndvi: HistogramSeries;
  reflectance: {
    unit?: string;
    is_display_rgb?: boolean;
    note?: string;
    available: boolean;
    channels: Record<string, HistogramSeries>;
    band_count_agreement?: {
      total_pixels_match?: boolean;
      in_range_spread?: number;
      forced_equal?: boolean;
      note?: string;
      in_range_by_channel?: Record<string, number>;
    };
  };
  scl: {
    grid: string;
    native_20m_mixed: boolean;
    source?: string;
    total_pixels: number;
    classes: SclClassRow[];
    groups: SclGroupRow[];
    pixel_conservation_ok?: boolean;
  } | null;
  source?: Record<string, unknown> | null;
  cached?: boolean;
}

export interface SoilDatasetDetail {
  dataset_id: string;
  bbox: number[] | null;
  period: { start?: string; end?: string } | null;
  timezone: string;
  source: Record<string, unknown> | null;
  spatial: {
    method?: string;
    source_longitude?: number;
    source_latitude?: number;
    distance_km?: number;
    native_resolution_deg?: number;
    [key: string]: unknown;
  } | null;
  variables: string[];
  day_count: number;
  complete_days: number;
  quality_status: string | null;
  observation_kind: string | null;
  is_ground_truth: boolean;
  is_measured_soil_moisture: boolean;
  suitable_for_modeling: boolean;
  unit: string;
}

export interface DailySoilRow {
  date_utc: string | null;
  unit: string | null;
  observation_kind: string | null;
  is_ground_truth?: boolean | null;
  is_measured_soil_moisture?: boolean | null;
  swvl1_mean: number | null;
  swvl2_mean: number | null;
  swvl3_mean: number | null;
  swvl4_mean: number | null;
  theta_root_zone_0_100: number | null;
  complete_day: boolean | null;
  quality_status: string | null;
  source_dataset: string | null;
  source_grid_id: string | null;
}

export interface MonthlySoilRow {
  month: string;
  day_count: number;
  complete_days: number;
  missing_days: number;
  availability: string | null;
  swvl1_mean: number | null;
  swvl2_mean: number | null;
  swvl3_mean: number | null;
  swvl4_mean: number | null;
  theta_root_zone_0_100_mean: number | null;
  theta_root_zone_0_100_min?: number | null;
  theta_root_zone_0_100_max?: number | null;
  aggregation?: string;
  unit?: string;
  observation_kind?: string;
}

export interface WetnessRow {
  date_utc: string | null;
  precipitation_total_mm: number | null;
  api_k085_mm: number | null;
  api_k090_mm: number | null;
  api_k095_mm: number | null;
  consecutive_dry_days: number | null;
  days_since_rain: number | null;
  precip_prev_7d_mm: number | null;
  precip_prev_14d_mm: number | null;
  precip_prev_30d_mm: number | null;
  precip_trailing_7d_end_of_day_mm: number | null;
  precip_trailing_14d_end_of_day_mm: number | null;
  precip_trailing_30d_end_of_day_mm: number | null;
  precip_minus_evap_7d_mm: number | null;
  precip_minus_evap_30d_mm: number | null;
  temperature_mean_c: number | null;
  relative_humidity_mean_pct: number | null;
  wind_speed_mean_ms: number | null;
  evaporation_total_mm: number | null;
  rainfall_history_kind: string | null;
  wetness_proxy_kind: string | null;
  is_measured_soil_moisture?: boolean | null;
  water_balance_status: string | null;
  quality_status: string | null;
  observation_kind: string | null;
}

export interface CombinedSoilWeatherRow {
  date_utc: string | null;
  precipitation_total_mm: number | null;
  evaporation_total_mm: number | null;
  api_k090_mm: number | null;
  consecutive_dry_days: number | null;
  precip_minus_evap_7d_mm: number | null;
  swvl1_mean: number | null;
  swvl2_mean: number | null;
  swvl3_mean: number | null;
  swvl4_mean: number | null;
  theta_root_zone_0_100: number | null;
  soil_present: boolean;
  weather_present: boolean;
  wetness_present: boolean;
  complete_day_soil: boolean | null;
  quality_status_soil: string | null;
  quality_status_weather: string | null;
  observation_kind_soil: string | null;
  observation_kind_weather: string | null;
  is_forecast: boolean;
  source_grid_id?: string | null;
}

export interface CombinedSoilWeather {
  soil_dataset_id: string;
  weather_dataset_id: string;
  unit_soil: string;
  unit_precipitation: string;
  observation_kind_soil: string;
  is_ground_truth: boolean;
  is_measured_soil_moisture: boolean;
  spatial: Record<string, unknown> | null;
  lagged_correlation_status: string;
  total: number;
  offset?: number;
  limit?: number;
  records: CombinedSoilWeatherRow[];
}
