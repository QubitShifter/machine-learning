import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { jsonResponse, renderApp } from "@/test/render";

vi.mock("@/components/maps/AoiMap", () => ({
  AoiMap: () => <div data-testid="aoi-map">AOI map</div>,
}));

vi.mock("@/components/maps/SatelliteMap", () => ({
  SatelliteMap: (props: {
    mode: string;
    opacity: number;
    overlayAvailable: boolean;
    overlayUrl?: string | null;
    overlayError?: string | null;
    isLoading?: boolean;
    onInspect?: (longitude: number, latitude: number) => void;
    onDraftGeometry?: (geometry: { type: string; bbox: number[]; coordinates: number[][] }) => void;
  }) => (
    <div
      data-testid="satellite-map"
      data-mode={props.mode}
      data-opacity={String(props.opacity)}
      data-available={String(props.overlayAvailable)}
      data-url={props.overlayUrl ?? ""}
      data-error={props.overlayError ?? ""}
      data-loading={String(Boolean(props.isLoading))}
    >
      <button type="button" data-testid="map-inspect" onClick={() => props.onInspect?.(24.66, 42.06)}>
        inspect
      </button>
      <button type="button" data-testid="map-inspect-alt" onClick={() => props.onInspect?.(24.67, 42.07)}>
        inspect-alt
      </button>
      <button
        type="button"
        data-testid="map-draft"
        onClick={() => props.onDraftGeometry?.({
          type: "bbox",
          bbox: [24.65, 42.05, 24.67, 42.07],
          coordinates: [[24.65, 42.05], [24.67, 42.05], [24.67, 42.07], [24.65, 42.07], [24.65, 42.05]],
        })}
      >
        draft
      </button>
    </div>
  ),
}));

vi.mock("@/components/charts/HistogramChart", () => ({
  HistogramChart: ({
    series,
  }: {
    series: Array<{ key: string; visible: boolean }>;
  }) => (
    <div data-testid="histogram-chart">
      {series.filter((item) => item.visible).map((item) => item.key).join(",")}
    </div>
  ),
}));

vi.mock("@/components/charts/DualAxisChart", () => ({
  DualAxisChart: () => <div data-testid="dual-axis-chart" />,
}));

vi.mock("@/components/charts/SeriesChart", () => ({
  SeriesChart: ({
    data,
    onPointClick,
  }: {
    data: Array<{ id?: string; selected?: boolean }>;
    onPointClick?: (id: string) => void;
  }) => (
    <div data-testid="series-chart">
      {data.map((item, index) => (
        <button
          key={item.id ?? `point-${index}`}
          type="button"
          data-selected={String(Boolean(item.selected))}
          onClick={() => item.id && onPointClick?.(item.id)}
        >
          {item.id}
        </button>
      ))}
    </div>
  ),
}));

const satelliteDatasets = {
  datasets: [
    {
      dataset_id: "plovdiv_2023_2025",
      period_start: "2023-01-01",
      period_end: "2025-12-31",
      scene_count: 9,
      processed_count: 9,
      has_timeseries: true,
    },
  ],
};

const weatherDatasets = {
  datasets: [
    {
      dataset_id: "plovdiv_weather_2023_2025",
      period_start: "2023-01-01",
      period_end: "2025-12-31",
      day_count: 1096,
      complete_days: 12,
      has_daily: true,
      quality_status: "valid",
    },
  ],
};

const soilDatasets = {
  datasets: [
    {
      dataset_id: "plovdiv_soil_2023_2025",
      period_start: "2023-01-01",
      period_end: "2023-01-31",
      day_count: 31,
      complete_days: 31,
      has_daily: true,
      quality_status: "valid",
      observation_kind: "modeled_volumetric_soil_moisture",
      is_ground_truth: false,
    },
  ],
};

function soilMonthlyFixture() {
  const january: Record<string, number> = {
    "2023": 0.3029981553682717,
    "2024": 0.3123924058483493,
    "2025": 0.3734779265619093,
  };
  const months = [];
  for (const year of ["2023", "2024", "2025"]) {
    for (let month = 1; month <= 12; month += 1) {
      const stamp = `${year}-${String(month).padStart(2, "0")}`;
      const days = new Date(Date.UTC(Number(year), month, 0)).getUTCDate();
      months.push({
        month: stamp,
        day_count: days,
        complete_days: days,
        missing_days: 0,
        availability: "complete",
        swvl1_mean: 0.3,
        swvl2_mean: 0.28,
        swvl3_mean: 0.25,
        swvl4_mean: 0.22,
        theta_root_zone_0_100_mean: month === 1 ? january[year] : 0.31,
        theta_root_zone_0_100_min: 0.28,
        theta_root_zone_0_100_max: 0.33,
        aggregation: "monthly_mean_of_complete_days",
        unit: "m3 m-3",
        observation_kind: "modeled_volumetric_soil_moisture",
      });
    }
  }
  return months;
}

const histograms = {
  dataset_id: "plovdiv_2023_2025",
  scene_id: "S2B_35TLG_20250916_1_L2A",
  histogram_version: "3.5.0",
  processing_version: "1.1.0",
  acquisition_date: "2025-09-16",
  scene_quality_status: "valid",
  calibration_status: "verified",
  scientific_use: "validated_or_unknown",
  warnings: [],
  ndvi: {
    unit: "NDVI",
    domain: [-1, 1],
    bins: 45,
    histogram: [
      { index: 20, edge_left: 0.0, edge_right: 0.044, center: 0.022, count: 80, percent_of_valid: 80, percent_of_total: 72 },
    ],
    statistics: { count: 100, mean: 0.41, median: 0.4, standard_deviation: 0.12, minimum: 0.1, maximum: 0.8, p10: 0.2, p90: 0.7, p99: 0.78 },
    valid_pixel_count: 100,
    masked_or_nodata_count: 10,
    out_of_range_count: 0,
    total_pixels: 110,
    valid_percentage: 90.9,
    pixel_conservation_ok: true,
    clamped: false,
    masked_treated_as_zero: false,
  },
  reflectance: {
    available: true,
    is_display_rgb: false,
    channels: {
      red: {
        band: "B04",
        unit: "surface_reflectance",
        domain: [0, 1],
        histogram: [
          { index: 2, edge_left: 0.04, edge_right: 0.06, center: 0.05, count: 90, percent_of_valid: 90, percent_of_total: 81 },
          { index: 20, edge_left: 0.40, edge_right: 0.42, center: 0.41, count: 10, percent_of_valid: 10, percent_of_total: 9 },
        ],
        statistics: { count: 100, mean: 0.12, median: 0.11, standard_deviation: 0.03, minimum: 0.05, maximum: 0.3, p10: 0.07, p90: 0.2, p99: 0.22 },
        valid_pixel_count: 100,
        histogrammed_count: 100,
        masked_or_nodata_count: 10,
        masked_count: 10,
        nonfinite_unmasked_count: 0,
        nonfinite_count: 0,
        out_of_range_count: 0,
        out_of_domain_count: 0,
        pixel_conservation_ok: true,
        total_pixels: 110,
        calibration: { scale: 0.0001, offset: 0.0, source: "earthsearch" },
      },
      green: {
        band: "B03",
        histogram: [],
        statistics: { count: 100, mean: 0.1, median: 0.1, standard_deviation: 0.02, minimum: 0.04, maximum: 0.2, p10: 0.06, p90: 0.15, p99: 0.18 },
        valid_pixel_count: 100,
        masked_or_nodata_count: 10,
        total_pixels: 110,
      },
      blue: {
        band: "B02",
        histogram: [],
        statistics: { count: 100, mean: 0.08, median: 0.08, standard_deviation: 0.02, minimum: 0.03, maximum: 0.18, p10: 0.05, p90: 0.12, p99: 0.16 },
        valid_pixel_count: 100,
        masked_or_nodata_count: 10,
        total_pixels: 110,
      },
    },
  },
  scl: {
    grid: "target_10m_aoi",
    native_20m_mixed: false,
    total_pixels: 110,
    classes: [
      { code: 4, name: "Vegetation", count: 40, percent: 36.4 },
      { code: 5, name: "Bare soil", count: 60, percent: 54.5 },
    ],
    groups: [
      { group: "vegetation", codes: [4], count: 40, percent: 36.4 },
      { group: "bare_soil", codes: [5], count: 60, percent: 54.5 },
      { group: "snow_ice", codes: [11], count: 0, percent: 0 },
      { group: "cloud_and_shadow", codes: [3, 8, 9, 10], count: 0, percent: 0 },
      { group: "water", codes: [6], count: 0, percent: 0 },
      { group: "other", codes: [0, 1, 2, 7], count: 10, percent: 9.1 },
    ],
  },
};

const weatherQuality = {
  dataset_id: "plovdiv_weather_2023_2025",
  status: "valid",
  source_integrity: "valid",
  observation_validity: "valid",
  period_completeness: "incomplete",
  integration_readiness: "limited",
  daily: { day_count: 1096, complete_days: 12, missing_days: 1084, completeness_pct: 1.09 },
  hourly: {
    unique_timestamps: 300,
    expected_boundary_overlaps: 1,
    accumulation: { unexpected_resets: 0, negative_steps: 0, forecast_cycle_resets: 10 },
  },
  accumulation: { unexpected_resets: 0, negative_steps: 0, forecast_cycle_resets: 10 },
  spatial: { source_longitude: 24.7, source_latitude: 42.1, distance_km: 4.8, native_resolution_deg: 0.1 },
  coverage: {
    downloaded_months: ["2023-01"],
    missing_months: ["2023-02"],
    expected_days: 1096,
    month_availability: { "2023-01": "downloaded", "2023-02": "missing_source" },
  },
  issues: [],
};

const monthly = {
  months: [
    {
      month: "2023-01",
      day_count: 31,
      complete_days: 31,
      missing_days: 0,
      availability: "downloaded",
      temperature_mean_c: 3.9,
      precipitation_total_mm: 12.4,
      relative_humidity_mean_pct: 80,
      wind_speed_mean_ms: 1.2,
      evaporation_total_mm: 5.1,
    },
    {
      month: "2023-02",
      day_count: 28,
      complete_days: 0,
      missing_days: 28,
      availability: "missing_source",
      temperature_mean_c: null,
      precipitation_total_mm: null,
      relative_humidity_mean_pct: null,
      wind_speed_mean_ms: null,
      evaporation_total_mm: null,
    },
  ],
};

const scenes = {
  scenes: [
    {
      scene_id: "S2B_35TLG_20250916_1_L2A",
      acquisition_date: "2025-09-16",
      status: "processed",
      platform: "sentinel-2b",
      overlay_ready: true,
      cloud_cover: 1.2,
      aoi_coverage: 100,
      valid_percentage: 96,
    },
    {
      scene_id: "S2A_35TLG_20250718_1_L2A",
      acquisition_date: "2025-07-18",
      status: "processed",
      platform: "sentinel-2a",
      overlay_ready: true,
      cloud_cover: 5.8,
    },
    {
      scene_id: "S2A_35TLG_CATALOG_1_L2A",
      acquisition_date: "2025-12-30",
      status: "discovered",
      platform: "sentinel-2a",
      overlay_ready: false,
    },
  ],
};

const mapMetadata = {
  scene_id: "S2B_35TLG_20250916_1_L2A",
  overlay_available: true,
  supported_modes: ["ndvi", "rgb", "scl"],
  scl_legend: [
    { code: 4, name: "Vegetation", color_rgb: [0, 160, 0] },
    { code: 5, name: "Bare soil", color_rgb: [255, 230, 90] },
  ],
  scl_provenance: {
    native_resolution_m: 20,
    target_grid_resolution_m: 10,
    alignment: "nearest_neighbor",
    resampling_forbidden: "bilinear",
    native_20m_mixed_with_10m_counts: false,
  },
  cache_id: "abc123",
  ndvi_color_scale: [
    { value: -1, color_rgb: [139, 0, 0] },
    { value: 0, color_rgb: [245, 245, 245] },
    { value: 1, color_rgb: [0, 68, 27] },
  ],
  geographic_extent: { west: 24.65, south: 42.05, east: 24.68, north: 42.08 },
  maplibre_coordinates: [[24.65, 42.08], [24.68, 42.08], [24.68, 42.05], [24.65, 42.05]],
};

function requestUrl(input: RequestInfo | URL): string {
  if (typeof input === "string") return input;
  if (input instanceof URL) return input.toString();
  return input.url;
}

function mockApi(overrides: Record<string, unknown> = {}) {
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL) => {
      const url = requestUrl(input);
      if (url.endsWith("/api/v1/satellite/datasets") && !url.includes("plovdiv")) {
        return jsonResponse(overrides.satelliteDatasets ?? satelliteDatasets);
      }
      if (url.includes("/histograms")) {
        if (url.includes("CATALOG")) {
          return jsonResponse({ detail: "Processed NDVI raster or valid mask is not available for histograms." }, 404);
        }
        return jsonResponse(overrides.histograms ?? histograms);
      }
      if (url.includes("/map/pixel")) {
        const parsed = new URL(url, "http://localhost");
        const longitude = Number(parsed.searchParams.get("longitude"));
        const latitude = Number(parsed.searchParams.get("latitude"));
        if (longitude === 0) {
          return jsonResponse({
            scene_id: "S2B_35TLG_20250916_1_L2A",
            acquisition_date: "2025-09-16",
            longitude,
            latitude,
            crs: "EPSG:4326",
            coverage_state: "out_of_coverage",
            inside_raster: false,
            valid: false,
            row: null,
            col: null,
            sampling: "nearest_10m_target_grid",
            red_b04: null,
            green_b03: null,
            blue_b02: null,
            nir_b08: null,
            ndvi: null,
            scl_class: null,
            scl_class_name: null,
            valid_mask: null,
            exclusion_reason: null,
            calibration_status: "verified",
            scene_quality_status: "valid",
            missing_reasons: { coverage: "out_of_coverage" },
            message: "Clicked location is outside the processed raster footprint.",
            source: "processed_rasters",
            estimated_from_display_rgb: false,
          });
        }
        return jsonResponse(overrides.pixel ?? {
          scene_id: "S2B_35TLG_20250916_1_L2A",
          acquisition_date: "2025-09-16",
          longitude,
          latitude,
          crs: "EPSG:4326",
          coverage_state: "inside",
          inside_raster: true,
          valid: true,
          row: longitude === 24.67 ? 20 : 12,
          col: longitude === 24.67 ? 40 : 34,
          sampling: "nearest_10m_target_grid",
          red_b04: 0.12,
          green_b03: 0.10,
          blue_b02: 0.08,
          nir_b08: 0.40,
          ndvi: longitude === 24.67 ? 0.61 : 0.54,
          scl_class: 4,
          scl_class_name: "Vegetation",
          valid_mask: true,
          exclusion_reason: null,
          calibration_status: "verified",
          scene_quality_status: "valid",
          missing_reasons: {},
          message: null,
          source: "processed_rasters",
          estimated_from_display_rgb: false,
        });
      }
      if (url.endsWith("/api/v1/aoi/areas")) {
        return jsonResponse(overrides.aoi ?? {
          version: "3.5.0",
          operational_count: 1,
          note: "Draft geometries are proposals only.",
          areas: [{
            aoi_id: "plovdiv_test",
            name: "Plovdiv study AOI",
            status: "operational",
            bbox: [24.65, 42.05, 24.68, 42.08],
            satellite_dataset_id: "plovdiv_2023_2025",
            geometry: { area_km2: 8.3, approximate_10m_pixels: 87978 },
          }],
          drafts: [],
        });
      }
      if (url.endsWith("/api/v1/aoi/drafts")) {
        return jsonResponse({
          draft_id: "draft-1",
          name: "Proposed study area",
          status: "draft",
          created_at: "2026-10-22T13:00:00Z",
          geometry: { type: "bbox", bbox: [24.65, 42.05, 24.67, 42.07], coordinates: [] },
          downloads_started: false,
          operational: false,
          note: "Draft study area only.",
        });
      }
      if (url.includes("/map/metadata")) {
        if (url.includes("CATALOG")) {
          return jsonResponse({
            scene_id: "S2A_35TLG_CATALOG_1_L2A",
            overlay_available: false,
            supported_modes: [],
            unavailable_reason: "Processed NDVI raster or valid mask is missing.",
            ndvi_color_scale: [],
          });
        }
        const sceneId = url.includes("20250718") ? "S2A_35TLG_20250718_1_L2A" : "S2B_35TLG_20250916_1_L2A";
        return jsonResponse({ ...mapMetadata, scene_id: sceneId });
      }
      if (url.includes("/api/v1/satellite/datasets/plovdiv_2023_2025/scenes/") && url.includes("/quality")) {
        return jsonResponse({
          scene_id: "S2B_35TLG_20250916_1_L2A",
          acquisition_date: "2025-09-16",
          satellite_platform: "sentinel-2b",
          quality_status: "valid",
          ndvi_mean: 0.41,
          ndvi_minimum: 0.1,
          ndvi_maximum: 0.8,
          valid_ndvi_pct: 96,
        });
      }
      if (url.endsWith("/scenes")) return jsonResponse(overrides.scenes ?? scenes);
      if (url.endsWith("/timeseries/ndvi")) {
        return jsonResponse({
          observations: [
            { scene_id: "S2B_35TLG_20250916_1_L2A", date: "2025-09-16", mean: 0.41 },
            { scene_id: "S2A_35TLG_20250718_1_L2A", date: "2025-07-18", mean: 0.58 },
          ],
        });
      }
      if (url.endsWith("/quality") && url.includes("satellite")) {
        return jsonResponse({
          dataset_id: "plovdiv_2023_2025",
          dataset: { validated_scenes: 8 },
          training_readiness: { supervised_soil_forecasting: "not_ready" },
          scene_count: 9,
        });
      }
      if (url.match(/\/api\/v1\/satellite\/datasets\/[^/]+$/)) {
        return jsonResponse({
          dataset_id: "plovdiv_2023_2025",
          bbox: [24.65, 42.05, 24.68, 42.08],
          collection: "sentinel-2-l2a",
          scene_count: 9,
          processed_count: 9,
          statuses: { processed: 9 },
          target_grid: { crs: "EPSG:32635", resolution: [10, 10] },
        });
      }
      if (url.endsWith("/api/v1/integration/datasets")) {
        return jsonResponse({
          datasets: [{
            dataset_id: "plovdiv_2023_2025",
            satellite_dataset_id: "plovdiv_2023_2025",
            weather_dataset_id: "plovdiv_weather_2023_2025",
            observation_count: 1,
            weather_feature_window_complete_count: 0,
            integrated_observation_complete_count: 0,
            suitable_for_modeling_count: 0,
            integration_version: "3.2.0",
            updated_at: "2026-10-21T06:04:54Z",
          }],
        });
      }
      if (url.includes("/api/v1/integration/datasets/") && url.includes("/observations")) {
        return jsonResponse({
          dataset_id: "plovdiv_2023_2025",
          total: 1,
          offset: 0,
          limit: 2000,
          records: [{
            scene_id: "S2A_35TLG_20250718_1_L2A",
            observation_date_utc: "2025-07-18",
            acquisition_timestamp_utc: "2025-07-18T09:29:03Z",
            ndvi_mean: 0.58,
            precip_prev_7d_mm: null,
            precip_prev_14d_mm: null,
            precip_prev_30d_mm: null,
            window_7d_complete: false,
            window_14d_complete: false,
            window_30d_complete: false,
            window_7d_observed_days: 0,
            window_14d_observed_days: 0,
            window_30d_observed_days: 0,
            window_7d_expected_days: 7,
            window_14d_expected_days: 14,
            window_30d_expected_days: 30,
            weather_feature_window_complete: false,
            satellite_observation_valid: true,
            suitable_for_modeling: false,
            quality_warnings: [],
          }],
        });
      }
      if (url.includes("/api/v1/integration/datasets/") && url.endsWith("/quality")) {
        return jsonResponse({
          dataset_id: "plovdiv_2023_2025",
          observation_count: 1,
          weather_feature_window_complete_count: 0,
          suitable_for_modeling_count: 0,
          issues: [],
        });
      }
      if (url.includes("/api/v1/integration/datasets/") && url.endsWith("/features")) {
        return jsonResponse({ dataset_id: "plovdiv_2023_2025", features: [], window_rule: "UTC D-N through D-1" });
      }
      if (url.match(/\/api\/v1\/integration\/datasets\/[^/?]+$/)) {
        return jsonResponse({
          dataset_id: "plovdiv_2023_2025",
          observation_count: 1,
          suitable_for_modeling_count: 0,
          weather_feature_window_complete_count: 0,
          integration_version: "3.2.0",
          weather_integration_readiness: "limited",
          satellite_supervised_soil_forecasting: "not_ready",
        });
      }
      if (url.endsWith("/api/v1/weather/datasets")) {
        return jsonResponse(overrides.weatherDatasets ?? weatherDatasets);
      }
      if (url.includes("/api/v1/soil/wetness/")) {
        return jsonResponse({
          total: 1,
          records: [{
            date_utc: "2023-01-01",
            precipitation_total_mm: 1.5,
            api_k085_mm: 1.4,
            api_k090_mm: 1.5,
            api_k095_mm: 1.6,
            consecutive_dry_days: 0,
            precip_trailing_7d_end_of_day_mm: null,
            precip_minus_evap_7d_mm: null,
            observation_kind: "era5_land_reanalysis",
          }],
        });
      }
      if (url.includes("/api/v1/soil/combined/")) {
        return jsonResponse({
          soil_dataset_id: "plovdiv_soil_2023_2025",
          weather_dataset_id: "plovdiv_weather_2023_2025",
          unit_soil: "m3 m-3",
          unit_precipitation: "mm",
          observation_kind_soil: "modeled_volumetric_soil_moisture",
          is_ground_truth: false,
          lagged_correlation_status: "prepared_not_interpreted",
          total: 2,
          records: [
            {
              date_utc: "2023-01-01",
              precipitation_total_mm: 1.5,
              api_k090_mm: 1.5,
              swvl1_mean: 0.3,
              theta_root_zone_0_100: 0.26,
              soil_present: true,
              weather_present: true,
              wetness_present: true,
              is_forecast: false,
            },
            {
              date_utc: "2023-01-02",
              precipitation_total_mm: null,
              swvl1_mean: null,
              theta_root_zone_0_100: null,
              soil_present: false,
              weather_present: true,
              wetness_present: false,
              is_forecast: false,
            },
          ],
        });
      }
      if (url.includes("/api/v1/soil/datasets/") && url.endsWith("/monthly")) {
        return jsonResponse({
          aggregation: "monthly_mean_of_complete_days",
          observation_kind: "modeled_volumetric_soil_moisture",
          months: soilMonthlyFixture(),
        });
      }
      if (url.includes("/api/v1/soil/datasets/") && url.includes("/daily")) {
        return jsonResponse({
          total: 2,
          records: [
            {
              date_utc: "2023-01-01",
              swvl1_mean: 0.3,
              swvl2_mean: 0.28,
              swvl3_mean: 0.25,
              swvl4_mean: 0.22,
              theta_root_zone_0_100: 0.26,
              complete_day: true,
              quality_status: "valid",
              observation_kind: "modeled_volumetric_soil_moisture",
              unit: "m3 m-3",
            },
            {
              date_utc: "2023-01-02",
              swvl1_mean: null,
              theta_root_zone_0_100: null,
              complete_day: false,
              quality_status: "missing",
            },
          ],
        });
      }
      if (url.includes("/api/v1/soil/datasets/") && url.endsWith("/quality")) {
        return jsonResponse({
          dataset_id: "plovdiv_soil_2023_2025",
          status: "valid",
          observation_kind: "modeled_volumetric_soil_moisture",
          is_ground_truth: false,
          is_measured_soil_moisture: false,
          suitable_for_modeling: false,
          daily: { complete_days: 31, day_count: 31 },
          spatial: { source_longitude: 24.7, source_latitude: 42.1, distance_km: 4.85, native_resolution_deg: 0.1 },
        });
      }
      if (url.match(/\/api\/v1\/soil\/datasets\/[^/?]+$/)) {
        return jsonResponse({
          dataset_id: "plovdiv_soil_2023_2025",
          bbox: [24.65, 42.05, 24.68, 42.08],
          timezone: "UTC",
          spatial: { source_longitude: 24.7, source_latitude: 42.1, distance_km: 4.85, native_resolution_deg: 0.1 },
          observation_kind: "modeled_volumetric_soil_moisture",
          is_ground_truth: false,
          unit: "m3 m-3",
        });
      }
      if (url.endsWith("/api/v1/soil/datasets")) {
        return jsonResponse(overrides.soilDatasets ?? soilDatasets);
      }
      if (url.includes("/api/v1/ml/experiments")) {
        if (url.includes("/runs")) {
          return jsonResponse({
            experiment_id: "none",
            total: 0,
            limit: 200,
            runs: [],
            live_training: false,
            note: "Read-only training-run index. GET does not train models.",
          });
        }
        return jsonResponse(overrides.mlExperiments ?? []);
      }
      if (url.includes("/api/v1/ml/")) {
        return jsonResponse({
          available: true,
          label: "Research dataset — no trained model yet.",
          dataset_id: "plovdiv_agricultural_ml_2023_2025",
          period_start: "2023-01-01",
          period_end: "2025-12-31",
          feature_row_count: 1096,
          feature_catalog_count: 40,
          target_row_count: 16440,
          horizons_days: [1, 3, 7],
          leakage_status: "passed",
          historical_research_readiness: "limited",
          operational_forecast_readiness: "not_ready",
          independent_ground_truth_readiness: "not_ready",
          suitable_for_modeling: false,
          trained_model_present: false,
          eligible_satellite_scenes: 15,
        });
      }
      if (url.endsWith("/quality")) return jsonResponse(overrides.weatherQuality ?? weatherQuality);
      if (url.endsWith("/monthly")) return jsonResponse(overrides.monthly ?? monthly);
      if (url.includes("/summary")) {
        return jsonResponse({
          complete_days: 2,
          day_count: 31,
          temperature_mean_c: 4,
          precipitation_total_mm: 2,
          relative_humidity_mean_pct: 70,
          wind_speed_mean_ms: 1,
          evaporation_total_mm: 1,
        });
      }
      if (url.includes("/daily")) {
        return jsonResponse({
          total: 2,
          records: [
            {
              date_utc: "2023-01-01",
              temperature_mean_c: 2,
              precipitation_total_mm: 1.5,
              quality_status: "valid",
              hourly_records_available: 24,
              hourly_records_expected: 24,
              boundary_00utc_available: true,
            },
            {
              date_utc: "2023-01-02",
              temperature_mean_c: null,
              precipitation_total_mm: null,
              quality_status: "missing",
              hourly_records_available: 0,
              observation_kind: "missing",
            },
          ],
        });
      }
      if (url.match(/\/api\/v1\/weather\/datasets\/[^/?]+$/)) {
        return jsonResponse({
          dataset_id: "plovdiv_weather_2023_2025",
          bbox: [24.65, 42.05, 24.68, 42.08],
          timezone: "UTC",
          spatial: { source_longitude: 24.7, source_latitude: 42.1, distance_km: 4.8, native_resolution_deg: 0.1 },
        });
      }
      return jsonResponse({ detail: "not found" }, 404);
    }),
  );
}

describe("UI Phase 1.0", () => {
  beforeEach(() => {
    sessionStorage.clear();
    mockApi();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("navigates between implemented pages and keeps predictions disabled", async () => {
    renderApp("/");
    expect(await screen.findByRole("heading", { name: "Overview" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("link", { name: "Satellite Explorer" }));
    expect(await screen.findByText("Scene selector")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("link", { name: "Combined Analytics" }));
    expect(await screen.findByText("Satellite + Weather Analytics")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("link", { name: "Weather Analytics" }));
    expect(await screen.findByText("Time selection")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("link", { name: "Soil Analysis" }));
    expect(await screen.findByText("Historical Comparison")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("link", { name: "Data Quality" }));
    expect(await screen.findByText("Quality dimensions")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("link", { name: "ML Training Lab" }));
    expect(await screen.findByText("ML Training Laboratory")).toBeInTheDocument();
    expect(screen.getByText("Coming later")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Predictions/ })).not.toBeInTheDocument();
  }, 15000);

  it("loads live dataset counts on overview", async () => {
    renderApp("/");
    expect(await screen.findByText("Downloaded weather months")).toBeInTheDocument();
    expect(await screen.findByText("plovdiv_2023_2025")).toBeInTheDocument();
    expect(screen.queryByText("13")).not.toBeInTheDocument();
    expect(screen.queryByText("395")).not.toBeInTheDocument();
  });

  it("shows API errors with retry", async () => {
    mockApi({
      satelliteDatasets: undefined,
    });
    vi.stubGlobal("fetch", vi.fn(() => jsonResponse({ detail: "backend unavailable" }, 500)));
    renderApp("/");
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("renders empty satellite and weather states", async () => {
    mockApi({
      satelliteDatasets: { datasets: [] },
      weatherDatasets: { datasets: [] },
    });
    renderApp("/");
    await waitFor(() => {
      expect(screen.getByText(/No satellite dataset/)).toBeInTheDocument();
    });
  });

  it("keeps missing weather values as missing", async () => {
    renderApp("/weather");
    expect(await screen.findByText("Time selection")).toBeInTheDocument();
    expect(await screen.findByRole("option", { name: /2023-02 \(missing_source\)/ })).toBeInTheDocument();
    expect(screen.queryByText("null rainfall 0")).not.toBeInTheDocument();
  });

  it("shows month availability and the four quality dimensions", async () => {
    renderApp("/quality");
    expect(await screen.findByText("Source integrity")).toBeInTheDocument();
    expect(screen.getByText("Observation validity")).toBeInTheDocument();
    expect(screen.getByText("Period completeness")).toBeInTheDocument();
    expect(screen.getByText("Integration readiness")).toBeInTheDocument();
    expect(await screen.findByLabelText("2023-01 downloaded")).toBeInTheDocument();
    expect(screen.getByLabelText("2023-02 missing_source")).toBeInTheDocument();
    expect(await screen.findByText("Research dataset — no trained model yet.")).toBeInTheDocument();
    expect(screen.getByText("Agricultural ML research dataset")).toBeInTheDocument();
  });

  it("updates the satellite scene selector", async () => {
    renderApp("/satellite");
    const select = await screen.findByLabelText("Acquisition") as HTMLSelectElement;
    expect(select.value).toBe("S2B_35TLG_20250916_1_L2A");
    expect(select).toBeInTheDocument();
    expect(screen.getByTestId("satellite-map")).toBeInTheDocument();
    expect(screen.getByText("Historical NDVI")).toBeInTheDocument();
  });

  it("defaults to a validated overlay-ready scene and unique IDs", async () => {
    renderApp("/satellite");
    const select = await screen.findByLabelText("Acquisition") as HTMLSelectElement;
    expect(select.value).toBe("S2B_35TLG_20250916_1_L2A");
    expect(screen.getByRole("option", { name: /S2B_35TLG_20250916_1_L2A/ })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /S2A_35TLG_20250718_1_L2A/ })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /CATALOG/ })).not.toBeInTheDocument();
  });

  it("marks catalog-only scenes as overlay unavailable", async () => {
    renderApp("/satellite?catalog=1&scene=S2A_35TLG_CATALOG_1_L2A");
    expect(await screen.findByText(/overlay unavailable/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByTestId("satellite-map")).toHaveAttribute("data-available", "false");
    });
  });

  it("switches RGB/NDVI and opacity", async () => {
    renderApp("/satellite");
    expect(await screen.findByTestId("ndvi-legend")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: "rgb" }));
    await waitFor(() => {
      expect(screen.getByTestId("satellite-map")).toHaveAttribute("data-mode", "rgb");
    });
    expect(screen.queryByTestId("ndvi-legend")).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Overlay opacity"), { target: { value: "0.4" } });
    expect(screen.getByTestId("satellite-map")).toHaveAttribute("data-opacity", "0.4");
  });

  it("updates the selected scene from the timeline and URL", async () => {
    renderApp("/satellite?scene=S2A_35TLG_20250718_1_L2A");
    const select = await screen.findByLabelText("Acquisition") as HTMLSelectElement;
    expect(select.value).toBe("S2A_35TLG_20250718_1_L2A");
    const timeline = screen.getByTestId("series-chart");
    fireEvent.click(timeline.querySelector("button") as HTMLButtonElement);
    await waitFor(() => {
      expect((screen.getByLabelText("Acquisition") as HTMLSelectElement).value).toBe("S2B_35TLG_20250916_1_L2A");
    });
    expect(timeline.querySelector('[data-selected="true"]')?.textContent).toBe("S2B_35TLG_20250916_1_L2A");
  });

  it("shows recent validated scenes on overview", async () => {
    renderApp("/");
    expect(await screen.findByText("Recent satellite scenes")).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: "2025-09-16" })).toHaveAttribute(
      "href",
      "/satellite?scene=S2B_35TLG_20250916_1_L2A",
    );
    expect(screen.queryByText("2025-12-30")).not.toBeInTheDocument();
  });

  it("keeps Predictions disabled for keyboard navigation", async () => {
    renderApp("/");
    expect(await screen.findByText("Coming later")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Overview" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Predictions/ })).not.toBeInTheDocument();
  });

  it("filters weather by selected year", async () => {
    renderApp("/weather");
    const year = await screen.findByLabelText("Year");
    fireEvent.change(year, { target: { value: "2024" } });
    await waitFor(() => {
      expect((year as HTMLSelectElement).value).toBe("2024");
    });
  });

  it("shows NDVI histogram metrics from the selected scene", async () => {
    renderApp("/satellite");
    expect(await screen.findByText("NDVI histogram")).toBeInTheDocument();
    expect((await screen.findAllByTestId("histogram-chart")).length).toBeGreaterThan(0);
    expect(screen.getByText("Scene classification (10 m target grid)")).toBeInTheDocument();
    expect(screen.getByText(/masked pixels excluded/i)).toBeInTheDocument();
  });

  it("defaults RGB histograms to auto-zoom and can restore the full [0, 1] range", async () => {
    renderApp("/satellite");
    expect(await screen.findByText("Auto Zoom")).toBeInTheDocument();
    expect(screen.getByTestId("reflectance-axis-range").textContent).toMatch(/0\.000 to 0\.253/);
    expect(screen.getByTestId("viewport-outside").textContent).toMatch(/10\.0%/);
    fireEvent.click(screen.getByRole("tab", { name: "Full Range" }));
    expect(screen.getByTestId("reflectance-axis-range").textContent).toMatch(/0\.000 to 1\.000/);
    expect(screen.queryByTestId("viewport-outside")).not.toBeInTheDocument();
  });

  it("toggles reflectance channels and shows per-band pixel accounting", async () => {
    renderApp("/satellite");
    expect(await screen.findByText("RGB surface reflectance")).toBeInTheDocument();
    const green = screen.getByLabelText("Green B03") as HTMLInputElement;
    expect(green.checked).toBe(true);
    fireEvent.click(green);
    expect(green.checked).toBe(false);
    expect(screen.getByTestId("channel-accounting-Red B04").textContent).toMatch(/total 110/);
    expect(screen.getByTestId("channel-accounting-Red B04").textContent).toMatch(/histogrammed 100/);
    expect(screen.getByTestId("channel-accounting-Red B04").textContent).toMatch(/conservation ok/);
  });

  it("selects SCL overlay mode with a categorical legend", async () => {
    renderApp("/satellite");
    const scl = await screen.findByRole("tab", { name: "scl" });
    fireEvent.click(scl);
    expect(await screen.findByTestId("scl-legend")).toBeInTheDocument();
    expect(screen.getByTestId("satellite-map")).toHaveAttribute("data-mode", "scl");
    expect(screen.getByText(/Native 20 m SCL aligned/)).toBeInTheDocument();
  });

  it("uses a split map/inspector workspace with the pixel inspector first", async () => {
    renderApp("/satellite");
    const workspace = await screen.findByTestId("satellite-workspace");
    const inspector = await screen.findByTestId("satellite-inspector");
    expect(workspace.className).toMatch(/satellite-workspace/);
    expect(inspector.className).toMatch(/satellite-inspector-panel/);
    expect(inspector.textContent?.indexOf("Pixel inspector") ?? -1).toBeLessThan(
      inspector.textContent?.indexOf("Scene information") ?? 0,
    );
    expect(screen.getByTestId("satellite-map")).toBeInTheDocument();
  });

  it("inspects a georeferenced pixel from processed rasters", async () => {
    const scrollTo = vi.spyOn(window, "scrollTo");
    renderApp("/satellite");
    expect(await screen.findByText("NDVI histogram")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("map-inspect"));
    const panel = await screen.findByTestId("pixel-inspector");
    expect(panel.textContent).toMatch(/24\.660000°E/);
    await waitFor(() => {
      expect(panel.textContent).toMatch(/row 12, col 34/);
    });
    expect(panel.textContent).toMatch(/Red B04/);
    expect(panel.textContent).toMatch(/0\.5400|0\.54/);
    expect(panel.textContent).toMatch(/Vegetation/);
    expect(panel.textContent).toMatch(/Not estimated from displayed RGB/);
    expect(scrollTo).not.toHaveBeenCalled();
    scrollTo.mockRestore();
  });

  it("updates the inspector on a second click without resetting map mode", async () => {
    renderApp("/satellite");
    expect(await screen.findByText("NDVI histogram")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("map-inspect"));
    expect(await screen.findByText(/row 12, col 34/)).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("map-inspect-alt"));
    expect(await screen.findByText(/row 20, col 40/)).toBeInTheDocument();
    expect(screen.getByText(/0\.6100|0\.61/)).toBeInTheDocument();
    expect(screen.getByTestId("satellite-map")).toHaveAttribute("data-mode", "ndvi");
  });

  it("clears the selected pixel when the scene changes", async () => {
    renderApp("/satellite");
    expect(await screen.findByText("NDVI histogram")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("map-inspect"));
    expect(await screen.findByText(/row 12, col 34/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Acquisition"), {
      target: { value: "S2A_35TLG_20250718_1_L2A" },
    });
    expect(await screen.findByTestId("pixel-inspector-empty")).toBeInTheDocument();
    expect(screen.queryByTestId("pixel-inspector")).not.toBeInTheDocument();
  });

  it("expands and collapses scene information and the classification legend", async () => {
    renderApp("/satellite");
    const sceneToggle = await screen.findByRole("button", { name: /Scene information/i });
    expect(sceneToggle).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(sceneToggle);
    expect(sceneToggle).toHaveAttribute("aria-expanded", "true");
    expect(await screen.findByRole("heading", { name: "Acquisition", level: 3 })).toBeInTheDocument();
    const legendToggle = screen.getByRole("button", { name: /NDVI color scale/i });
    expect(legendToggle).toHaveAttribute("aria-expanded", "true");
    fireEvent.click(legendToggle);
    expect(legendToggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByTestId("ndvi-legend")).not.toBeInTheDocument();
  });

  it("can hide the inspector without removing map mode controls", async () => {
    renderApp("/satellite");
    expect(await screen.findByTestId("satellite-inspector")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Hide inspector" }));
    expect(screen.queryByTestId("satellite-inspector")).not.toBeInTheDocument();
    expect(screen.getByTestId("satellite-workspace").className).toMatch(/is-inspector-collapsed/);
    expect(screen.getByRole("tab", { name: "ndvi" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Show inspector" }));
    expect(screen.getByTestId("satellite-inspector")).toBeInTheDocument();
  });

  it("keeps inspector section toggles keyboard-accessible", async () => {
    renderApp("/satellite");
    const pixelToggle = await screen.findByRole("button", { name: /Pixel inspector/i });
    expect(pixelToggle.tagName).toBe("BUTTON");
    expect(pixelToggle).toHaveAttribute("aria-controls", "pixel-inspector-panel");
    pixelToggle.focus();
    expect(pixelToggle).toHaveFocus();
    fireEvent.click(pixelToggle);
    expect(pixelToggle).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(pixelToggle);
    expect(pixelToggle).toHaveAttribute("aria-expanded", "true");
  });

  it("lists the operational Plovdiv AOI without starting downloads", async () => {
    renderApp("/aoi");
    expect(await screen.findByText("Plovdiv study AOI")).toBeInTheDocument();
    expect(screen.getByText(/does not download imagery/i)).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("map-draft"));
    expect(await screen.findByTestId("draft-aoi-summary")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Save draft proposal" }));
    expect(await screen.findByText(/No satellite or soil download was started/i)).toBeInTheDocument();
  });

  it("warns when a rejected scene histogram is shown", async () => {
    mockApi({
      histograms: {
        ...histograms,
        scene_quality_status: "rejected",
        scientific_use: "rejected_or_review",
        calibration_status: "verified",
        warnings: ["Scene quality is not validated. Distributions are shown for inspection and must not be treated as validated agricultural science."],
      },
    });
    renderApp("/satellite");
    expect(await screen.findByText(/not validated science/i)).toBeInTheDocument();
    expect(screen.getByText(/Calibration status/)).toBeInTheDocument();
  });

  it("renders soil depth, layer selection, and dual-axis rainfall chart", async () => {
    renderApp("/soil");
    expect(await screen.findByText("Historical Comparison")).toBeInTheDocument();
    expect(await screen.findByTestId("soil-depth-chart")).toBeInTheDocument();
    const layer = await screen.findByLabelText("Soil layer") as HTMLSelectElement;
    fireEvent.change(layer, { target: { value: "theta_root_zone_0_100" } });
    expect(layer.value).toBe("theta_root_zone_0_100");
    expect(screen.getByTestId("dual-axis-chart")).toBeInTheDocument();
    expect(screen.getByText(/modeled reanalysis/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: "monthly" }));
    expect(screen.getByText("Monthly depth profile (mean of complete days)")).toBeInTheDocument();
    expect(screen.getByText("Historical Soil Moisture — Year-over-Year Comparison")).toBeInTheDocument();
    expect(screen.getByTestId("soil-yoy-chart")).toBeInTheDocument();
    expect(screen.getByTestId("soil-yoy-delta-value").textContent).toMatch(/0\.0705 m³\/m³/);
    expect(screen.getByTestId("soil-yoy-provenance").textContent).toMatch(/not independently measured field soil moisture/);
  });

  it("keeps historical comparison first and independent of detailed soil analysis", async () => {
    renderApp("/soil");
    const historical = await screen.findByTestId("soil-historical-workspace");
    const detailed = await screen.findByTestId("soil-detailed-workspace");
    expect(historical.compareDocumentPosition(detailed) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(await screen.findByTestId("soil-yoy-chart")).toBeInTheDocument();
    expect(screen.getByTestId("soil-detail-controls")).toBeInTheDocument();
    expect(screen.getByText("Detailed Soil Analysis")).toBeInTheDocument();
    expect(screen.getByText("Compare seasonal soil-water behavior across available years.")).toBeInTheDocument();
    expect(screen.getByText("Inspect soil moisture at individual depths over a selected period.")).toBeInTheDocument();

    const detailYear = screen.getByLabelText("Detailed year") as HTMLSelectElement;
    expect(detailYear.value).toBe("2025");
    expect(screen.getByLabelText("2023")).toBeChecked();
    expect(screen.getByLabelText("2024")).toBeChecked();
    expect(screen.getByLabelText("2025")).toBeChecked();

    fireEvent.click(screen.getByLabelText("2024"));
    expect(screen.getByLabelText("2024")).not.toBeChecked();
    expect(detailYear.value).toBe("2025");
    expect(screen.getByTestId("soil-yoy-delta-value").textContent).toMatch(/0\.0705 m³\/m³/);

    fireEvent.change(detailYear, { target: { value: "2023" } });
    expect(detailYear.value).toBe("2023");
    expect(screen.getByLabelText("2024")).not.toBeChecked();
    expect(screen.getByLabelText("2023")).toBeChecked();
    expect(screen.getByLabelText("2025")).toBeChecked();

    fireEvent.change(screen.getByLabelText("Detailed month"), { target: { value: "2023-06" } });
    expect((screen.getByLabelText("Detailed month") as HTMLSelectElement).value).toBe("2023-06");
    expect(screen.getByTestId("soil-yoy-delta-value").textContent).toMatch(/0\.0705 m³\/m³/);
    expect(screen.getByLabelText("Comparison month")).toHaveDisplayValue("January");

    fireEvent.click(screen.getByRole("button", { name: "Explore this year 2024" }));
    expect((screen.getByLabelText("Detailed year") as HTMLSelectElement).value).toBe("2024");
    expect((screen.getByLabelText("Detailed month") as HTMLSelectElement).value).toBe("");
    expect(screen.getByLabelText("2024")).not.toBeChecked();
    expect(await screen.findByTestId("soil-depth-chart")).toBeInTheDocument();
    expect(await screen.findByTestId("dual-axis-chart")).toBeInTheDocument();
  });

  it("shows wetness proxies without treating them as soil moisture", async () => {
    renderApp("/weather");
    expect(await screen.findByText("Rainfall history and wetness proxies")).toBeInTheDocument();
    expect(await screen.findByText(/not volumetric soil moisture/i)).toBeInTheDocument();
    expect(screen.getByText("API k=0.85 / 0.90 / 0.95")).toBeInTheDocument();
  });
});
