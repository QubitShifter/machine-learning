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
  }) => (
    <div
      data-testid="satellite-map"
      data-mode={props.mode}
      data-opacity={String(props.opacity)}
      data-available={String(props.overlayAvailable)}
      data-url={props.overlayUrl ?? ""}
      data-error={props.overlayError ?? ""}
      data-loading={String(Boolean(props.isLoading))}
    />
  ),
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
  supported_modes: ["ndvi", "rgb"],
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
    fireEvent.click(screen.getByRole("link", { name: "Data Quality" }));
    expect(await screen.findByText("Quality dimensions")).toBeInTheDocument();
    expect(screen.getByText("Coming later")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Predictions/ })).not.toBeInTheDocument();
  });

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
});
