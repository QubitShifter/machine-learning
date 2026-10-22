import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { jsonResponse, renderApp } from "@/test/render";

const EXPERIMENT_ID = "plovdiv_soil_forecast_baselines_v1";

const listing = [
  {
    experiment_id: EXPERIMENT_ID,
    label: "Research experiment on ERA5-Land modeled soil moisture. Not operational.",
    frozen: true,
    test_evaluated: true,
    operational_forecast: false,
    suitable_for_modeling: false,
  },
];

const detail = {
  experiment_id: EXPERIMENT_ID,
  label: "Research experiment on ERA5-Land modeled soil moisture. Not operational.",
  frozen: true,
  test_evaluated: true,
  suitable_for_modeling: false,
  trained_model_present: true,
  operational_forecast: false,
  target_source_kind: "modeled_reanalysis",
  is_ground_truth: false,
  dataset_id: "plovdiv_agricultural_ml_2023_2025",
  dataset_version: "4.0.0",
  pipeline_version: "4.1.0",
  target_variable: "swvl1",
  depth_label: "0-7 cm",
  unit: "m3 m-3",
  horizons_days: [1, 3, 7],
  feature_sets: ["A", "B", "C"],
  primary_feature_set: "C",
  config_fingerprint: "bc94975fc52834290c85c3cd9f666b1569567ad2a625ece6ea7e7601deb926f8",
  frozen_at_utc: "2026-10-22T18:38:09Z",
  random_seed: 42,
  research_mode: "research_reanalysis",
  validation_comparison: [],
  final_test_metrics: [],
};

function count(split: string, horizon: number, n: number, purged = 0) {
  return { split, horizon_days: horizon, feature_set: "C", n, purged_or_missing: purged };
}

const dataset = {
  experiment_id: EXPERIMENT_ID,
  available: true,
  label: "Research experiment dataset statistics.",
  dataset_id: "plovdiv_agricultural_ml_2023_2025",
  dataset_version: "4.0.0",
  pipeline_version: "4.1.0",
  target_variable: "swvl1",
  depth_label: "0-7 cm",
  unit: "m3 m-3",
  horizons_days: [1, 3, 7],
  feature_sets: [
    { id: "A", name: "persistence", enabled: true, status: "available", columns: ["swvl1_prev1"] },
    { id: "B", name: "soil_calendar", enabled: true, status: "available", columns: ["swvl1_prev1"] },
    { id: "C", name: "soil_weather", enabled: true, status: "available", columns: ["swvl1_prev1", "precip_prev_7d_mm"] },
    { id: "D", name: "satellite", enabled: false, status: "not_trained", columns: [], reason: "synthesized midnight timestamps" },
  ],
  n_joined_rows: 3288,
  eligible_rows: 3255,
  counts: [
    count("training", 1, 350, 14),
    count("validation", 1, 365, 0),
    count("test", 1, 364, 0),
    count("training", 7, 348, 16),
    count("validation", 7, 359, 0),
    count("test", 7, 358, 0),
  ],
  missing_data_policy: "complete_case",
  satellite_features_enabled: false,
  chronological_splits: { training: "2023", validation: "2024", test: "2025" },
  suitable_for_modeling: false,
  is_ground_truth: false,
  target_source_kind: "modeled_reanalysis",
};

const features = {
  experiment_id: EXPERIMENT_ID,
  available: true,
  primary_feature_set: "C",
  satellite_excluded: true,
  satellite_reason: "synthesized midnight timestamps",
  predictive_feature_count: 12,
  records: [
    {
      feature_id: "soil.swvl1_prev1",
      column_name: "swvl1_prev1",
      scientific_meaning: "Latest available daily mean soil-water content",
      input_source: "daily_soil.csv",
      source_variable: "swvl1",
      units: "m3 m-3",
      temporal_window: "D-1",
      formula: "swvl1_mean on D-1",
      missing_data_policy: "complete_case",
      feature_sets: ["A", "B", "C"],
      used_by_primary: true,
      satellite: false,
    },
    {
      feature_id: "weather.precip_prev_7d_mm",
      column_name: "precip_prev_7d_mm",
      scientific_meaning: "Accumulated rainfall over the previous seven completed UTC days",
      input_source: "daily_weather.csv",
      source_variable: "precipitation_total_mm",
      units: "mm",
      temporal_window: "D-7..D-1",
      formula: "sum of precipitation_total_mm over D-7 to D-1",
      missing_data_policy: "complete_case",
      feature_sets: ["C"],
      used_by_primary: true,
      satellite: false,
    },
  ],
  note: "Feature metadata from the experiment catalog. Not fitted coefficients.",
};

const selected = [
  { model_id: "persistence", horizon_days: 1, feature_set: "A", n: 350 },
  { model_id: "seasonal", horizon_days: 1, feature_set: "A", n: 350 },
  { model_id: "ridge", horizon_days: 1, feature_set: "C", n: 350, alpha: 1.0, path: "ridge_h1_C.joblib" },
  { model_id: "gradient_boosting", horizon_days: 1, feature_set: "C", n: 350, max_depth: 3, learning_rate: 0.1, max_iter: 80 },
  { model_id: "persistence", horizon_days: 7, feature_set: "A", n: 348 },
  { model_id: "ridge", horizon_days: 7, feature_set: "C", n: 348, alpha: 10.0 },
  { model_id: "seasonal", horizon_days: 7, feature_set: "A", n: 348 },
  { model_id: "gradient_boosting", horizon_days: 7, feature_set: "C", n: 348 },
];

const training = {
  experiment_id: EXPERIMENT_ID,
  available: true,
  live_training: false,
  fitted_on: "training",
  validation_used_for_fitting: false,
  test_used_for_fitting: false,
  random_seed: 42,
  generated_at_utc: "2026-10-22T18:37:24Z",
  selected,
  trained_candidate_count: 12,
  telemetry: {
    available: false,
    format: "training_events.jsonl",
    reason: "Training history unavailable — this experiment recorded final metrics but not per-iteration telemetry.",
  },
  lifecycle: [
    { stage: "source_validated", label: "Source dataset validated", status: "completed", artifact: "experiment_config_snapshot.yaml" },
    { stage: "model_training", label: "Model training", status: "completed", artifact: "training_summary.json" },
    { stage: "final_test_evaluation", label: "Final test evaluation", status: "completed", artifact: "final_test_metrics.csv" },
  ],
  coefficients: [],
  seasonal_monthly_means: { "1": { monthly_means: { "1": 0.31 } } },
  suitable_for_modeling: false,
  note: "Read-only training artifacts. GET does not train models.",
};

function metric(modelId: string, horizon: number, mae: number, skill: number, n: number) {
  return {
    model_id: modelId,
    horizon_days: horizon,
    feature_set: "C",
    mae,
    rmse: mae * 1.2,
    bias: 0.001,
    r2: 0.4,
    skill_mae: skill,
    n,
  };
}

const validationMetrics = {
  experiment_id: EXPERIMENT_ID,
  partition: "validation",
  total: 4,
  records: [
    metric("persistence", 1, 0.0196, 0, 365),
    metric("ridge", 1, 0.0185, 0.056, 365),
    metric("seasonal", 1, 0.051, -1.6, 365),
    metric("gradient_boosting", 1, 0.019, 0.03, 365),
    metric("persistence", 7, 0.031, 0, 359),
    metric("ridge", 7, 0.0279, 0.101, 359),
    metric("seasonal", 7, 0.05, -0.6, 359),
    metric("gradient_boosting", 7, 0.03, 0.03, 359),
  ],
};

const testMetrics = {
  experiment_id: EXPERIMENT_ID,
  partition: "test",
  total: 4,
  records: [
    metric("persistence", 1, 0.0196, 0, 364),
    metric("ridge", 1, 0.0202, -0.03, 364),
    metric("seasonal", 1, 0.0516, -1.6, 364),
    metric("gradient_boosting", 1, 0.0214, -0.09, 364),
    metric("persistence", 7, 0.033, 0, 358),
    metric("ridge", 7, 0.032, 0.029, 358),
    metric("seasonal", 7, 0.052, -0.58, 358),
    metric("gradient_boosting", 7, 0.034, -0.03, 358),
  ],
};

const predictions = {
  experiment_id: EXPERIMENT_ID,
  partition: "validation",
  total: 2,
  offset: 0,
  limit: 2000,
  selected_only: true,
  label: "ERA5-Land modeled soil-moisture research predictions. Not field measurements.",
  records: [
    { issue_date_utc: "2024-01-02", model_id: "persistence", prediction: 0.2, observed_modeled_target: 0.21, horizon_days: 1, feature_set: "C" },
    { issue_date_utc: "2024-01-02", model_id: "ridge", prediction: 0.205, observed_modeled_target: 0.21, horizon_days: 1, feature_set: "C" },
  ],
};

const provenance = {
  experiment_id: EXPERIMENT_ID,
  available: true,
  pipeline_version: "4.1.0",
  dataset_id: "plovdiv_agricultural_ml_2023_2025",
  dataset_version: "4.0.0",
  config_fingerprint: "abc123",
  features_daily_sha256: "e7f6f074",
  frozen: true,
  frozen_at_utc: "2026-10-22T18:38:09Z",
  test_consulted: true,
  test_evaluated_at_utc: "2026-10-22T18:38:17Z",
  test_repeat: false,
  git_revision: "1d617c5",
  git_dirty: true,
  python_version: "3.14.4",
  package_versions: { "scikit-learn": "1.9.1" },
  random_seed: 42,
  research_mode: "research_reanalysis",
  operational_forecast: false,
  operational_availability_verified: false,
  is_ground_truth: false,
  is_measured_soil_moisture: false,
  suitable_for_modeling: false,
  target_source_kind: "modeled_reanalysis",
  training_events_format: "training_events.jsonl",
  training_events_present: false,
  label: "Research experiment on ERA5-Land modeled soil moisture. Not operational.",
};

function requestUrl(input: RequestInfo | URL): string {
  if (typeof input === "string") return input;
  if (input instanceof URL) return input.toString();
  return input.url;
}

const RUN_ID = "run_20261022T191500Z_aaa111";
const RUN_ID_B = "run_20261022T191600Z_bbb222";

const runList = {
  experiment_id: EXPERIMENT_ID,
  total: 2,
  limit: 200,
  live_training: false,
  note: "Read-only training-run index. GET does not train models.",
  runs: [
    {
      run_id: RUN_ID,
      experiment_id: EXPERIMENT_ID,
      algorithm: "ridge",
      horizon_days: 1,
      feature_set: "C",
      status: "completed",
      inferred_status: "completed",
      created_at_utc: "2026-10-22T19:15:00Z",
      start_at_utc: "2026-10-22T19:15:00Z",
      finish_at_utc: "2026-10-22T19:15:02Z",
      duration_ms: 1200,
      training_duration_ms: 80,
      training_sample_count: 46,
      validation_sample_count: 20,
      selected_feature_count: 7,
      validation_mae: 0.012,
      validation_rmse: 0.015,
      validation_skill_mae: 0.1,
      provenance_label: "telemetry_development_run",
      execution_mode: "research_development",
      is_frozen_phase_4_1_model: false,
      test_targets_accessed: false,
      suitable_for_modeling: false,
      research_mode: "research_reanalysis",
    },
    {
      run_id: RUN_ID_B,
      experiment_id: EXPERIMENT_ID,
      algorithm: "gradient_boosting",
      horizon_days: 1,
      feature_set: "C",
      status: "completed",
      inferred_status: "completed",
      created_at_utc: "2026-10-22T19:16:00Z",
      start_at_utc: "2026-10-22T19:16:00Z",
      finish_at_utc: "2026-10-22T19:16:03Z",
      duration_ms: 2100,
      training_duration_ms: 400,
      training_sample_count: 46,
      validation_sample_count: 20,
      selected_feature_count: 7,
      validation_mae: 0.013,
      validation_rmse: 0.016,
      validation_skill_mae: 0.05,
      provenance_label: "telemetry_development_run",
      execution_mode: "research_development",
      is_frozen_phase_4_1_model: false,
      test_targets_accessed: false,
      suitable_for_modeling: false,
      research_mode: "research_reanalysis",
    },
  ],
};

const runDetail = {
  experiment_id: EXPERIMENT_ID,
  run_id: RUN_ID,
  available: true,
  live_training: false,
  status: "completed",
  inferred_status: "completed",
  algorithm: "ridge",
  horizon_days: 1,
  feature_set: "C",
  target_variable: "swvl1",
  created_at_utc: "2026-10-22T19:15:00Z",
  start_at_utc: "2026-10-22T19:15:00Z",
  finish_at_utc: "2026-10-22T19:15:02Z",
  duration_ms: 1200,
  timings_ms: { model_fitting: 80, total_run: 1200 },
  hyperparameters: { alpha: 1.0, solver: "auto" },
  diagnostics: {
    optimizer: "ridge_auto",
    training_iterations: null,
    iteration_history_available: false,
    iteration_history_reason: "not_exposed_by_estimator",
    alpha: 1.0,
    solver: "auto",
    n_features: 7,
    intercept: 0.2,
    scaler: "StandardScaler",
    fitting_duration_ms: 80,
    coefficients: [{ feature: "swvl1_prev1", value: 0.11 }],
  },
  dataset_summary: {
    training_sample_count: 46,
    validation_sample_count: 20,
    selected_feature_count: 7,
  },
  training_summary: {},
  metrics: { validation: { mae: 0.012, rmse: 0.015, skill_mae: 0.1 } },
  artifacts: {},
  git_commit: "93f31ca",
  git_dirty: true,
  python_version: "3.14.4",
  provenance_label: "telemetry_development_run",
  execution_mode: "research_development",
  research_mode: "research_reanalysis",
  is_frozen_phase_4_1_model: false,
  test_targets_accessed: false,
  operational_forecast: false,
  operational_availability_verified: false,
  is_ground_truth: false,
  is_measured_soil_moisture: false,
  suitable_for_modeling: false,
  telemetry_validation_ok: true,
  event_count: 4,
  note: "Read-only telemetry run.",
};

const boostingDetail = {
  ...runDetail,
  run_id: RUN_ID_B,
  algorithm: "gradient_boosting",
  diagnostics: {
    n_iter_: 8,
    training_iterations: 8,
    max_iter: 8,
    learning_rate: 0.1,
    max_depth: 2,
    early_stopping: false,
    iteration_history_source: "staged_predict_after_fit",
    native_train_score_available: false,
    fitting_duration_ms: 40,
    termination: "reached_max_iter",
  },
  hyperparameters: { max_iter: 8, learning_rate: 0.1, max_depth: 2 },
};

const runEvents = {
  experiment_id: EXPERIMENT_ID,
  run_id: RUN_ID,
  total: 4,
  returned: 4,
  sequence_after: 0,
  limit: 2000,
  truncated_final_line: false,
  live_training: false,
  note: "Historical recorded events. This is not live monitoring.",
  events: [
    { sequence: 1, timestamp_utc: "2026-10-22T19:15:00Z", elapsed_ms: 0, event_type: "run_created", phase: "created" },
    { sequence: 2, timestamp_utc: "2026-10-22T19:15:01Z", elapsed_ms: 10, event_type: "training_started", phase: "fit", model: "ridge" },
    { sequence: 3, timestamp_utc: "2026-10-22T19:15:01Z", elapsed_ms: 20, event_type: "training_completed", phase: "fit", model: "ridge" },
    { sequence: 4, timestamp_utc: "2026-10-22T19:15:02Z", elapsed_ms: 30, event_type: "run_completed", phase: "completed" },
  ],
};

const boostingEvents = {
  ...runEvents,
  run_id: RUN_ID_B,
  events: [
    { sequence: 1, timestamp_utc: "2026-10-22T19:16:00Z", elapsed_ms: 0, event_type: "run_created", phase: "created" },
    { sequence: 2, timestamp_utc: "2026-10-22T19:16:01Z", elapsed_ms: 5, event_type: "training_metric", phase: "fit", iteration: 1, metric_name: "training_mse", metric_value: 0.002, metric_unit: "squared_m3_per_m3", dataset_partition: "train", details: { calculation_method: "staged_predict_after_fit" } },
    { sequence: 3, timestamp_utc: "2026-10-22T19:16:01Z", elapsed_ms: 8, event_type: "training_metric", phase: "fit", iteration: 2, metric_name: "training_mse", metric_value: 0.0015, metric_unit: "squared_m3_per_m3", dataset_partition: "train", details: { calculation_method: "staged_predict_after_fit" } },
    { sequence: 4, timestamp_utc: "2026-10-22T19:16:03Z", elapsed_ms: 40, event_type: "run_completed", phase: "completed" },
  ],
};

const runMetrics = {
  experiment_id: EXPERIMENT_ID,
  run_id: RUN_ID,
  records: [],
  history: [],
  training: { mae: 0.01 },
  validation: { mae: 0.012, rmse: 0.015, skill_mae: 0.1 },
  live_training: false,
  note: "Evaluation metrics and recorded history.",
};

function mockLabApi(overrides: Record<string, unknown> = {}) {
  const fetchMock = vi.fn((input: RequestInfo | URL) => {
    const url = requestUrl(input);
    if (url.includes("/api/v1/ml/experiments")) {
      if (url.endsWith("/api/v1/ml/experiments") || /\/api\/v1\/ml\/experiments\/?$/.test(url.split("?")[0])) {
        if (overrides.experimentsError) {
          return jsonResponse({ detail: "Experiment index failed." }, 500);
        }
        return jsonResponse(overrides.listing ?? listing);
      }
      if (url.includes("/runs")) {
        if (overrides.runsError) return jsonResponse({ detail: "Run index failed." }, 500);
        if (url.includes("/events")) {
          return jsonResponse(url.includes(RUN_ID_B) ? boostingEvents : (overrides.runEvents ?? runEvents));
        }
        if (url.includes("/metrics")) return jsonResponse(runMetrics);
        if (url.includes("/artifacts")) return jsonResponse({ experiment_id: EXPERIMENT_ID, run_id: RUN_ID, artifacts: [], live_training: false, note: "" });
        if (/\/runs\/[^/?]+/.test(url) && !/\/runs\/?(\?|$)/.test(url.split("?")[0])) {
          return jsonResponse(url.includes(RUN_ID_B) ? boostingDetail : (overrides.runDetail ?? runDetail));
        }
        return jsonResponse(overrides.runList ?? runList);
      }
      if (url.includes("/dataset")) return jsonResponse(overrides.dataset ?? dataset);
      if (url.includes("/features")) return jsonResponse(features);
      if (url.includes("/training")) return jsonResponse(overrides.training ?? training);
      if (url.includes("/provenance")) return jsonResponse(provenance);
      if (url.includes("/metrics")) {
        return jsonResponse(url.includes("partition=test") ? testMetrics : validationMetrics);
      }
      if (url.includes("/predictions")) return jsonResponse(predictions);
      return jsonResponse(overrides.detail ?? detail);
    }
    if (
      url.includes("/api/v1/satellite/datasets")
      || url.includes("/api/v1/weather/datasets")
      || url.includes("/api/v1/soil/datasets")
    ) {
      return jsonResponse({ datasets: [] });
    }
    return jsonResponse({ detail: `unmocked ${url}` }, 404);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("ML Training Laboratory", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads the experiment and sample counts on Overview", async () => {
    const fetchMock = mockLabApi();
    renderApp("/ml/training");
    expect(await screen.findByRole("heading", { name: "ML Training Laboratory" })).toBeInTheDocument();
    expect(await screen.findByText("Training samples")).toBeInTheDocument();
    expect(screen.getByText("Training samples").closest("div")).toHaveTextContent("350");
    expect(screen.getByText("Validation samples").closest("div")).toHaveTextContent("365");
    expect(screen.getByText("Test samples").closest("div")).toHaveTextContent("364");
    expect(screen.getByText("Validation MAE").closest("div")).toHaveTextContent("0.0196");
    expect(screen.getByText("suitable_for_modeling false")).toBeInTheDocument();
    const posted = (fetchMock.mock.calls as unknown as Array<[RequestInfo | URL, RequestInit?]>)
      .some(([, init]) => String(init?.method ?? "GET").toUpperCase() === "POST");
    expect(posted).toBe(false);
  });

  it("updates sample counts when the horizon changes", async () => {
    mockLabApi();
    renderApp("/ml/training");
    expect(await screen.findByText("Training samples")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Forecast horizon"), { target: { value: "7" } });
    await waitFor(() => {
      expect(screen.getByText("Training samples").closest("div")).toHaveTextContent("348");
    });
    expect(screen.getByText("Test samples").closest("div")).toHaveTextContent("358");
  });

  it("keeps selectors while switching tabs and labels the held-out test", async () => {
    mockLabApi();
    renderApp("/ml/training");
    await screen.findByText("Experiment summary");
    fireEvent.change(screen.getByLabelText("Forecast horizon"), { target: { value: "7" } });
    fireEvent.click(screen.getByRole("tab", { name: "Evaluation" }));
    expect(await screen.findByTestId("model-comparison-chart")).toBeInTheDocument();
    expect(screen.getByText(/validation 2024 · h=7/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Evaluation partition"), { target: { value: "test" } });
    expect(await screen.findByText(/final test 2025 · h=7/)).toBeInTheDocument();
    expect(screen.getByText("ERA5-Land modeled reference — not field sensor measurement.")).toBeInTheDocument();
    expect(screen.getByText(/Ridge regression has the lowest MAE/)).toBeInTheDocument();
    expect((screen.getByLabelText("Forecast horizon") as HTMLSelectElement).value).toBe("7");
  });

  it("shows training history unavailable and does not invent a loss curve", async () => {
    mockLabApi();
    renderApp("/ml/training");
    await screen.findByText("Experiment summary");
    fireEvent.click(screen.getByRole("tab", { name: "Training Process" }));
    expect(await screen.findByTestId("training-history-unavailable")).toHaveTextContent(/Training history unavailable/);
    expect(screen.getByText(/Live training is not implemented/i)).toBeInTheDocument();
    expect(screen.queryByText(/epoch 1/i)).not.toBeInTheDocument();
  });

  it("does not offer the untrained satellite feature set", async () => {
    mockLabApi();
    renderApp("/ml/training");
    const featureSet = await screen.findByLabelText("Feature set") as HTMLSelectElement;
    await waitFor(() => {
      expect([...featureSet.options].map((option) => option.value)).toEqual(["A", "B", "C"]);
    });
    fireEvent.click(screen.getByRole("tab", { name: "Dataset" }));
    expect(await screen.findByText(/Feature set D: not trained/)).toBeInTheDocument();
    expect(screen.getByText("swvl1_prev1")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Search features"), { target: { value: "precip" } });
    expect(screen.getByText("precip_prev_7d_mm")).toBeInTheDocument();
    expect(screen.queryByText("swvl1_prev1")).not.toBeInTheDocument();
  });

  it("explains Ridge without describing gradient-descent epochs", async () => {
    mockLabApi();
    renderApp("/ml/training");
    const algorithm = await screen.findByLabelText("Algorithm") as HTMLSelectElement;
    await waitFor(() => {
      expect([...algorithm.options].map((option) => option.value)).toContain("ridge");
    });
    fireEvent.change(algorithm, { target: { value: "ridge" } });
    fireEvent.click(screen.getByRole("tab", { name: "Algorithms" }));
    expect(await screen.findByText(/not gradient-descent epoch training/i)).toBeInTheDocument();
    expect(screen.getByText(/not the solver used by Phase 4.1 Ridge/i)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Algorithm"), { target: { value: "gradient_boosting" } });
    expect(await screen.findByText(/not neural backpropagation/i)).toBeInTheDocument();
  });

  it("labels mathematics demonstrations as educational simulations", async () => {
    mockLabApi();
    renderApp("/ml/training");
    await screen.findByText("Experiment summary");
    fireEvent.click(screen.getByRole("tab", { name: "Mathematics" }));
    expect(await screen.findByTestId("educational-simulation-banner")).toHaveTextContent(
      "Educational simulation — not training telemetry from the agricultural model.",
    );
    expect(screen.getByText("Linear regression (synthetic)")).toBeInTheDocument();
    expect(screen.getByTestId("descent-outcome")).toHaveTextContent("converged");
  });

  it("renders provenance caution flags", async () => {
    mockLabApi();
    renderApp("/ml/training");
    await screen.findByText("Experiment summary");
    fireEvent.click(screen.getByRole("tab", { name: "Experiment Provenance" }));
    expect(await screen.findByText("operational_availability_verified=false")).toBeInTheDocument();
    expect(screen.getByText("is_ground_truth=false")).toBeInTheDocument();
    expect(screen.getByText("suitable_for_modeling=false")).toBeInTheDocument();
    expect(screen.getByText("research_reanalysis")).toBeInTheDocument();
  });

  it("shows an empty state when no experiment artifacts exist", async () => {
    mockLabApi({ listing: [] });
    renderApp("/ml/training");
    expect(await screen.findByText("No experiment artifacts are available.")).toBeInTheDocument();
  });

  it("shows an API error with retry", async () => {
    mockLabApi({ experimentsError: true });
    renderApp("/ml/training");
    expect(await screen.findByText("Experiment index failed.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("lists telemetry runs and shows ridge diagnostics without a fabricated curve", async () => {
    mockLabApi();
    renderApp("/ml/training");
    await screen.findByText("Experiment summary");
    fireEvent.click(screen.getByRole("tab", { name: "Training Runs" }));
    expect(await screen.findByLabelText("Training run")).toBeInTheDocument();
    expect(screen.getByText("Training run summary")).toBeInTheDocument();
    expect(screen.getByText("Not recorded")).toBeInTheDocument();
    expect(screen.getByTestId("missing-metric-history")).toHaveTextContent(/linear system/i);
    expect(screen.queryByTestId("training-metrics-chart")).not.toBeInTheDocument();
    expect(screen.getByText(/Historical training playback/)).toBeInTheDocument();
    expect(screen.getByText("suitable_for_modeling=false")).toBeInTheDocument();
    expect(screen.getByText("test_targets_accessed=false")).toBeInTheDocument();
  });

  it("plays back stored events and steps without inventing states", async () => {
    mockLabApi();
    renderApp("/ml/training");
    await screen.findByText("Experiment summary");
    fireEvent.click(screen.getByRole("tab", { name: "Training Runs" }));
    expect(await screen.findByTestId("playback-cursor")).toHaveTextContent("Event 1 / 4");
    fireEvent.click(screen.getByRole("button", { name: "Step forward" }));
    expect(screen.getByTestId("playback-cursor")).toHaveTextContent("Event 2 / 4");
    fireEvent.click(screen.getByRole("button", { name: "Reset historical playback" }));
    expect(screen.getByTestId("playback-cursor")).toHaveTextContent("Event 1 / 4");
  });

  it("compares runs and warns when requested", async () => {
    mockLabApi();
    renderApp("/ml/training");
    await screen.findByText("Experiment summary");
    fireEvent.click(screen.getByRole("tab", { name: "Training Runs" }));
    expect(await screen.findByLabelText(`Compare ${RUN_ID}`)).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText(`Compare ${RUN_ID}`));
    fireEvent.click(screen.getByLabelText(`Compare ${RUN_ID_B}`));
    expect(screen.getByText(/Horizons, validation counts, and metric definitions match/)).toBeInTheDocument();
    expect(screen.getAllByText("80 ms").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("1.20 s").length).toBeGreaterThanOrEqual(1);
  });

  it("shows boosting stage history from recorded points only", async () => {
    mockLabApi();
    renderApp("/ml/training");
    await screen.findByText("Experiment summary");
    fireEvent.click(screen.getByRole("tab", { name: "Training Runs" }));
    const selector = await screen.findByLabelText("Training run") as HTMLSelectElement;
    fireEvent.change(selector, { target: { value: RUN_ID_B } });
    expect(await screen.findByTestId("training-metrics-chart")).toBeInTheDocument();
    expect(screen.getByText(/Fitted iterations \(n_iter_\): 8/)).toBeInTheDocument();
    expect(screen.queryByText(/epoch 1/i)).not.toBeInTheDocument();
  });

  it("shows an empty telemetry state when no runs exist", async () => {
    mockLabApi({
      runList: {
        experiment_id: EXPERIMENT_ID,
        total: 0,
        limit: 200,
        live_training: false,
        note: "Read-only",
        runs: [],
      },
    });
    renderApp("/ml/training");
    await screen.findByText("Experiment summary");
    fireEvent.click(screen.getByRole("tab", { name: "Training Runs" }));
    expect(await screen.findByTestId("training-runs-empty")).toHaveTextContent(/No telemetry-enabled training runs/);
  });

  it("shows a run API error with retry", async () => {
    mockLabApi({ runsError: true });
    renderApp("/ml/training");
    await screen.findByText("Experiment summary");
    fireEvent.click(screen.getByRole("tab", { name: "Training Runs" }));
    expect(await screen.findByText("Run index failed.")).toBeInTheDocument();
  });
});
