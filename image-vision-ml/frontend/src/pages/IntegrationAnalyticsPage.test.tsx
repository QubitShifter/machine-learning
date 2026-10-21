import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { jsonResponse, renderApp } from "@/test/render";
import type { IntegrationObservation } from "@/types/integration";

vi.mock("@/components/maps/AoiMap", () => ({
  AoiMap: () => <div data-testid="aoi-map">AOI map</div>,
}));
vi.mock("@/components/maps/SatelliteMap", () => ({
  SatelliteMap: () => <div data-testid="satellite-map" />,
}));
vi.mock("@/components/charts/SeriesChart", () => ({
  SeriesChart: () => <div data-testid="series-chart" />,
}));

function observation(partial: Partial<IntegrationObservation> & { scene_id: string; observation_date_utc: string }): IntegrationObservation {
  return {
    satellite_dataset_id: "plovdiv_2023_2025",
    weather_dataset_id: "plovdiv_weather_2023_2025",
    acquisition_timestamp_utc: `${partial.observation_date_utc}T09:18:47Z`,
    acquisition_time_precision: "utc_datetime",
    aoi_id: "plovdiv_test",
    ndvi_mean: 0.4,
    ndvi_minimum: 0.1,
    ndvi_maximum: 0.8,
    ndvi_median: 0.42,
    valid_ndvi_pct: 97,
    cloud_shadow_fraction_pct: 0,
    source_crs: "EPSG:32635",
    pixel_resolution_m: 10,
    satellite_quality_status: "valid",
    quality_status: "valid",
    precip_prev_7d_mm: null,
    precip_prev_14d_mm: null,
    precip_prev_30d_mm: null,
    temp_mean_prev_7d_c: null,
    temp_mean_prev_30d_c: null,
    dry_days_prev_30d: null,
    rh_mean_prev_7d_pct: null,
    wind_mean_prev_7d_ms: null,
    evap_prev_7d_mm: null,
    evap_prev_30d_mm: null,
    window_7d_complete: false,
    window_14d_complete: false,
    window_30d_complete: false,
    window_7d_expected_days: 7,
    window_14d_expected_days: 14,
    window_30d_expected_days: 30,
    window_7d_observed_days: 0,
    window_14d_observed_days: 0,
    window_30d_observed_days: 0,
    window_7d_missing_days: 7,
    window_14d_missing_days: 14,
    window_30d_missing_days: 30,
    window_7d_start_utc: null,
    window_7d_end_utc: null,
    window_14d_start_utc: null,
    window_14d_end_utc: null,
    window_30d_start_utc: null,
    window_30d_end_utc: null,
    source_grid_id: "42.1,24.7",
    weather_grid_longitude: 24.7,
    weather_grid_latitude: 42.1,
    weather_grid_distance_km: 4.85,
    weather_grid_method: "nearest_grid_cell",
    satellite_observation_valid: true,
    weather_observation_valid: true,
    weather_feature_window_complete: false,
    integrated_observation_complete: false,
    suitable_for_modeling: false,
    quality_warnings: [],
    integration_version: "3.2.0",
    satellite_processing_version: "1.1.0",
    ...partial,
  };
}

const completeWindows = {
  window_7d_complete: true,
  window_14d_complete: true,
  window_30d_complete: true,
  window_7d_observed_days: 7,
  window_14d_observed_days: 14,
  window_30d_observed_days: 30,
  window_7d_missing_days: 0,
  window_14d_missing_days: 0,
  window_30d_missing_days: 0,
  weather_feature_window_complete: true,
  integrated_observation_complete: true,
};

const records: IntegrationObservation[] = [
  observation({
    scene_id: "S2A_35TLG_20230326_0_L2A",
    observation_date_utc: "2023-03-26",
    ndvi_mean: 0.425,
    precip_prev_7d_mm: 10.591,
    precip_prev_14d_mm: 18.27,
    precip_prev_30d_mm: 36.216,
    temp_mean_prev_7d_c: 8.1,
    temp_mean_prev_30d_c: 6.2,
    rh_mean_prev_7d_pct: 70,
    wind_mean_prev_7d_ms: 1.8,
    evap_prev_7d_mm: 4.1,
    evap_prev_30d_mm: 18.2,
    dry_days_prev_30d: 22,
    window_7d_start_utc: "2023-03-19",
    window_7d_end_utc: "2023-03-25",
    window_14d_start_utc: "2023-03-12",
    window_14d_end_utc: "2023-03-25",
    window_30d_start_utc: "2023-02-24",
    window_30d_end_utc: "2023-03-25",
    ...completeWindows,
  }),
  observation({
    scene_id: "S2B_35TLG_20240227_0_L2A",
    observation_date_utc: "2024-02-27",
    ndvi_mean: 0.365,
    precip_prev_7d_mm: 2.878,
    precip_prev_14d_mm: 9.3,
    precip_prev_30d_mm: 15.692,
    temp_mean_prev_7d_c: 4.2,
    ...completeWindows,
  }),
  observation({
    scene_id: "S2C_35TLG_20250424_0_L2A",
    observation_date_utc: "2025-04-24",
    ndvi_mean: 0.593,
    precip_prev_7d_mm: 7.561,
    precip_prev_14d_mm: 18.52,
    precip_prev_30d_mm: null,
    temp_mean_prev_7d_c: 12.4,
    window_7d_complete: true,
    window_14d_complete: true,
    window_30d_complete: false,
    window_7d_observed_days: 7,
    window_14d_observed_days: 14,
    window_30d_observed_days: 23,
    window_30d_missing_days: 7,
    window_7d_start_utc: "2025-04-17",
    window_7d_end_utc: "2025-04-23",
    window_30d_start_utc: "2025-03-25",
    window_30d_end_utc: "2025-04-23",
  }),
  observation({
    scene_id: "S2A_35TLG_20250718_1_L2A",
    observation_date_utc: "2025-07-18",
    ndvi_mean: 0.58,
    quality_warnings: ["missing_weather_window_7d"],
  }),
  observation({
    scene_id: "S2B_35TLG_20230722_0_L2A",
    observation_date_utc: "2023-07-22",
    ndvi_mean: 0.595,
    precip_prev_7d_mm: 0,
    precip_prev_14d_mm: 0,
    precip_prev_30d_mm: 0,
    temp_mean_prev_7d_c: 24.1,
    ...completeWindows,
  }),
  observation({
    scene_id: "S2B_35TKG_20230222_0_L2A",
    observation_date_utc: "2023-02-22",
    ndvi_mean: 0.408,
    precip_prev_7d_mm: 0.012,
    precip_prev_14d_mm: 0.65,
    precip_prev_30d_mm: 42.7,
    temp_mean_prev_7d_c: null,
    temp_mean_prev_30d_c: null,
    ...completeWindows,
  }),
  observation({
    scene_id: "S2A_34TGM_20240412_0_L2A",
    observation_date_utc: "2024-04-12",
    ndvi_mean: 0.67,
  }),
  observation({
    scene_id: "S2B_34TGM_20240412_1_L2A",
    observation_date_utc: "2024-04-12",
    ndvi_mean: 0.61,
  }),
];

const listing = {
  datasets: [{
    dataset_id: "plovdiv_2023_2025",
    satellite_dataset_id: "plovdiv_2023_2025",
    weather_dataset_id: "plovdiv_weather_2023_2025",
    observation_count: records.length,
    integrated_observation_complete_count: 4,
    weather_feature_window_complete_count: 4,
    suitable_for_modeling_count: 0,
    integration_version: "3.2.0",
    updated_at: "2026-10-21T06:04:54Z",
  }],
};

const detail = {
  dataset_id: "plovdiv_2023_2025",
  satellite_dataset_id: "plovdiv_2023_2025",
  weather_dataset_id: "plovdiv_weather_2023_2025",
  observation_count: records.length,
  weather_feature_window_complete_count: 4,
  integrated_observation_complete_count: 4,
  suitable_for_modeling_count: 0,
  integration_version: "3.2.0",
  window_rule: "For an acquisition on UTC day D, preceding weather features use completed UTC days D−N through D−1. Weather from acquisition day D is excluded.",
  weather_integration_readiness: "limited",
  satellite_supervised_soil_forecasting: "not_ready",
  updated_at: "2026-10-21T06:04:54Z",
};

function requestUrl(input: RequestInfo | URL): string {
  if (typeof input === "string") return input;
  if (input instanceof URL) return input.toString();
  return input.url;
}

function mockApi(options?: { fail?: boolean; empty?: boolean; records?: IntegrationObservation[] }) {
  const rows = options?.empty ? [] : (options?.records ?? records);
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL) => {
      const url = requestUrl(input);
      if (options?.fail) return jsonResponse({ detail: "backend unavailable" }, 500);
      if (url.endsWith("/api/v1/satellite/datasets")) {
        return jsonResponse({ datasets: [{ dataset_id: "plovdiv_2023_2025", scene_count: 9, processed_count: 9, has_timeseries: true }] });
      }
      if (url.endsWith("/scenes")) {
        return jsonResponse({
          scenes: rows.filter((row) => row.scene_id).map((row) => ({
            scene_id: row.scene_id,
            acquisition_date: row.observation_date_utc,
            status: "processed",
            overlay_ready: true,
            platform: "sentinel-2a",
          })),
        });
      }
      if (url.includes("/map/metadata")) {
        return jsonResponse({
          scene_id: "S2A_35TLG_20230326_0_L2A",
          overlay_available: true,
          supported_modes: ["ndvi", "rgb"],
          ndvi_color_scale: [],
        });
      }
      if (url.includes("/timeseries/ndvi")) {
        return jsonResponse({ observations: rows.map((row) => ({ scene_id: row.scene_id, date: row.observation_date_utc, mean: row.ndvi_mean })) });
      }
      if (url.includes("/api/v1/satellite/") && url.endsWith("/quality")) {
        return jsonResponse({ dataset_id: "plovdiv_2023_2025", dataset: {}, training_readiness: {}, scene_count: rows.length });
      }
      if (url.match(/\/api\/v1\/satellite\/datasets\/[^/]+$/)) {
        return jsonResponse({ dataset_id: "plovdiv_2023_2025", bbox: [24.65, 42.05, 24.68, 42.08], scene_count: 9, processed_count: 9, statuses: {}, collection: "sentinel-2-l2a" });
      }
      if (url.endsWith("/api/v1/weather/datasets")) {
        return jsonResponse({ datasets: [{ dataset_id: "plovdiv_weather_2023_2025", day_count: 1, complete_days: 1, has_daily: true }] });
      }
      if (url.includes("/api/v1/weather/datasets/") && url.endsWith("/quality")) {
        return jsonResponse({ dataset_id: "wx", period_completeness: "incomplete", integration_readiness: "limited", daily: {}, hourly: {}, issues: [] });
      }
      if (url.endsWith("/api/v1/integration/datasets")) {
        return jsonResponse(options?.empty ? { datasets: [] } : listing);
      }
      if (url.includes("/observations")) {
        return jsonResponse({ dataset_id: "plovdiv_2023_2025", total: rows.length, offset: 0, limit: 2000, records: rows });
      }
      if (url.endsWith("/quality") && url.includes("integration")) {
        return jsonResponse({
          dataset_id: "plovdiv_2023_2025",
          observation_count: rows.length,
          weather_feature_window_complete_count: 4,
          integrated_observation_complete_count: 4,
          suitable_for_modeling_count: 0,
          satellite_observation_valid_count: rows.length,
          weather_observation_valid_count: rows.length,
          issues: [],
        });
      }
      if (url.endsWith("/features")) {
        return jsonResponse({
          dataset_id: "plovdiv_2023_2025",
          window_rule: detail.window_rule,
          features: [
            { id: "precip_prev_7d_mm", name: "Prior 7-day precipitation total", unit: "mm" },
            { id: "precip_prev_30d_mm", name: "Prior 30-day precipitation total", unit: "mm" },
          ],
        });
      }
      if (url.match(/\/api\/v1\/integration\/datasets\/[^/?]+$/)) {
        return jsonResponse(detail);
      }
      return jsonResponse({ detail: "not found" }, 404);
    }),
  );
}

describe("UI Phase 1.2 Combined Analytics", () => {
  beforeEach(() => mockApi());
  afterEach(() => vi.unstubAllGlobals());

  it("renders the integration route from the sidebar", async () => {
    renderApp("/");
    fireEvent.click(await screen.findByRole("link", { name: "Combined Analytics" }));
    expect(await screen.findByText("Satellite + Weather Analytics")).toBeInTheDocument();
    expect(screen.getByText(/exploratory observational analysis/i)).toBeInTheDocument();
    expect(screen.getByText("Coming later")).toBeInTheDocument();
  });

  it("loads API counts and a modeling-ready count of zero", async () => {
    renderApp("/integration");
    expect(await screen.findByText("Integrated observations")).toBeInTheDocument();
    expect(screen.getByText("3.2.0")).toBeInTheDocument();
    const modeling = screen.getByText("Modeling-ready observations").parentElement;
    expect(modeling).toHaveTextContent("0");
    expect(screen.getByText(/soil-moisture ground-truth labels are not available/i)).toBeInTheDocument();
  });

  it("shows API failure and retry", async () => {
    mockApi({ fail: true });
    renderApp("/integration");
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Retry" }).length).toBeGreaterThan(0);
  });

  it("shows an empty integration dataset", async () => {
    mockApi({ empty: true });
    renderApp("/integration");
    expect(await screen.findByText(/no integrated satellite–weather observations/i)).toBeInTheDocument();
  });

  it("defaults to the most recent complete weather window", async () => {
    renderApp("/integration");
    const select = await screen.findByLabelText("Integrated acquisition") as HTMLSelectElement;
    expect(select.value).toBe("S2B_35TLG_20240227_0_L2A");
  });

  it("selects a deep-linked scene", async () => {
    renderApp("/integration?scene=S2A_35TLG_20230326_0_L2A");
    const select = await screen.findByLabelText("Integrated acquisition") as HTMLSelectElement;
    expect(select.value).toBe("S2A_35TLG_20230326_0_L2A");
    expect(screen.getByTestId("precip-7d")).toHaveTextContent("10.591");
    expect(screen.getByTestId("precip-14d")).toHaveTextContent("18.27");
    expect(screen.getByTestId("precip-30d")).toHaveTextContent("36.216");
    expect(screen.getAllByText(/2023-03-26 09:18:47 UTC/).length).toBeGreaterThan(0);
  });

  it("explains an invalid scene ID and falls back safely", async () => {
    renderApp("/integration?scene=NOT_A_SCENE");
    expect(await screen.findByText(/not in the integrated table/i)).toBeInTheDocument();
    expect((screen.getByLabelText("Integrated acquisition") as HTMLSelectElement).value).toBe("S2B_35TLG_20240227_0_L2A");
  });

  it("shows a partial 30-day window as unavailable rather than zero", async () => {
    renderApp("/integration?scene=S2C_35TLG_20250424_0_L2A");
    const bar = await screen.findByTestId("precip-30d");
    expect(bar).toHaveAttribute("data-available", "false");
    expect(bar).toHaveTextContent("Unavailable");
    expect(bar).not.toHaveTextContent("0 mm");
    expect(screen.getByTestId("coverage-30d")).toHaveAttribute("data-coverage", "partial");
    expect(screen.getByTestId("coverage-30d")).toHaveTextContent("23/30");
    expect(screen.getByTestId("precip-7d")).toHaveAttribute("data-available", "true");
    expect(screen.getByTestId("precip-7d")).toHaveTextContent("7.561");
  });

  it("shows fully missing weather windows without fabricating rainfall", async () => {
    renderApp("/integration?scene=S2A_35TLG_20250718_1_L2A");
    expect(await screen.findByTestId("precip-7d")).toHaveAttribute("data-available", "false");
    expect(screen.getByTestId("precip-14d")).toHaveAttribute("data-available", "false");
    expect(screen.getByTestId("precip-30d")).toHaveAttribute("data-available", "false");
    expect(screen.getByTestId("coverage-7d")).toHaveAttribute("data-coverage", "missing");
    expect(screen.queryByText("65.367")).not.toBeInTheDocument();
  });

  it("does not sum nested precipitation windows", async () => {
    renderApp("/integration?scene=S2A_35TLG_20230326_0_L2A");
    expect(await screen.findByTestId("precip-7d")).toBeInTheDocument();
    expect(screen.queryByText("65.077")).not.toBeInTheDocument();
    expect(screen.getByText(/do not add the 7-, 14- and 30-day values/i)).toBeInTheDocument();
  });

  it("displays zero precipitation as 0, not missing", async () => {
    renderApp("/integration?scene=S2B_35TLG_20230722_0_L2A");
    const bar = await screen.findByTestId("precip-7d");
    expect(bar).toHaveAttribute("data-available", "true");
    expect(bar).toHaveTextContent("0");
    expect(bar).not.toHaveTextContent("Unavailable");
  });

  it("keeps temperature unavailable when precipitation windows are complete", async () => {
    renderApp("/integration?scene=S2B_35TKG_20230222_0_L2A");
    const temp = await screen.findByTestId("feature-temp_mean_prev_7d_c");
    expect(within(temp).getByText("Unavailable")).toBeInTheDocument();
    expect(screen.getByTestId("feature-precip_prev_7d_mm")).toHaveTextContent("0.012");
  });

  it("excludes null numeric pairs from the scatter and reports the count", async () => {
    renderApp("/integration");
    expect(await screen.findByTestId("scatter-pair-count")).toHaveTextContent("Plotted pairs: 5 of 8 observations");
    fireEvent.change(screen.getByLabelText("Weather feature"), { target: { value: "precip_prev_30d_mm" } });
    expect(screen.getByTestId("scatter-pair-count")).toHaveTextContent("Plotted pairs: 4 of 8 observations");
  });

  it("keeps distinct scenes that share an acquisition date", async () => {
    renderApp("/integration");
    await screen.findByLabelText("Integrated acquisition");
    expect(screen.getByRole("option", { name: /S2A_34TGM_20240412_0_L2A/ })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /S2B_34TGM_20240412_1_L2A/ })).toBeInTheDocument();
  });

  it("updates the selected scene from the table", async () => {
    renderApp("/integration");
    await screen.findByLabelText("Integrated acquisition");
    fireEvent.click(screen.getByText("S2A_35TLG_20230326_0_L2A"));
    await waitFor(() => {
      expect((screen.getByLabelText("Integrated acquisition") as HTMLSelectElement).value).toBe("S2A_35TLG_20230326_0_L2A");
    });
    expect(screen.getByRole("link", { name: "Open in Satellite Explorer" })).toHaveAttribute(
      "href",
      "/satellite?scene=S2A_35TLG_20230326_0_L2A",
    );
  });

  it("navigates from Satellite Explorer when an integration record exists", async () => {
    renderApp("/satellite?scene=S2A_35TLG_20230326_0_L2A");
    const link = await screen.findByRole("link", { name: "View weather context" });
    expect(link).toHaveAttribute("href", "/integration?scene=S2A_35TLG_20230326_0_L2A");
  });

  it("refreshes after integration dataset changes", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = requestUrl(input);
      if (url.endsWith("/api/v1/satellite/datasets")) {
        return jsonResponse({ datasets: [{ dataset_id: "plovdiv_2023_2025", scene_count: 1, processed_count: 1, has_timeseries: true }] });
      }
      if (url.endsWith("/api/v1/weather/datasets")) {
        return jsonResponse({ datasets: [{ dataset_id: "plovdiv_weather_2023_2025" }] });
      }
      if (url.includes("/weather/") && url.endsWith("/quality")) {
        return jsonResponse({ daily: {}, hourly: {}, issues: [] });
      }
      if (url.endsWith("/api/v1/integration/datasets") || url.match(/\/integration\/datasets\/[^/?]+$/)) {
        return jsonResponse({
          ...listing,
          datasets: listing.datasets,
          observation_count: fetchMock.mock.calls.length > 8 ? 9 : 8,
          weather_feature_window_complete_count: fetchMock.mock.calls.length > 8 ? 5 : 4,
          suitable_for_modeling_count: 0,
          integration_version: fetchMock.mock.calls.length > 8 ? "3.2.1" : "3.2.0",
        });
      }
      if (url.includes("/observations")) {
        const extra = fetchMock.mock.calls.some((call) => requestUrl(call[0] as RequestInfo | URL).includes("refresh") || fetchMock.mock.calls.length > 10);
        return jsonResponse({
          total: extra ? records.length + 1 : records.length,
          records: extra
            ? [...records, observation({ scene_id: "NEW_SCENE", observation_date_utc: "2025-08-01", ...completeWindows, precip_prev_7d_mm: 1 })]
            : records,
          offset: 0,
          limit: 2000,
          dataset_id: "plovdiv_2023_2025",
        });
      }
      if (url.endsWith("/quality")) {
        return jsonResponse({ suitable_for_modeling_count: 0, observation_count: 8, weather_feature_window_complete_count: 4, issues: [] });
      }
      if (url.endsWith("/features")) return jsonResponse({ features: [] });
      return jsonResponse({ detail: "not found" }, 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    renderApp("/integration");
    expect(await screen.findByText("3.2.0")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Refresh" }));
    await waitFor(() => {
      expect(fetchMock.mock.calls.length).toBeGreaterThan(6);
    });
  });
});
