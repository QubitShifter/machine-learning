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
  quality_limitations: string[];
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
  reasons: string[];
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
  scene_count: number;
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
