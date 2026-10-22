export interface ExperimentListItem {
  experiment_id: string;
  label: string;
  frozen: boolean;
  test_evaluated: boolean;
  operational_forecast: boolean;
  suitable_for_modeling: boolean;
}

export interface ExperimentDetail {
  experiment_id: string;
  label: string;
  frozen: boolean;
  test_evaluated: boolean;
  suitable_for_modeling: boolean;
  trained_model_present: boolean;
  operational_forecast: boolean;
  target_source_kind: string;
  is_ground_truth: boolean;
  dataset_id: string | null;
  dataset_version: string | null;
  pipeline_version: string | null;
  target_variable: string | null;
  depth_label: string | null;
  unit: string | null;
  horizons_days: number[];
  feature_sets: string[];
  primary_feature_set: string | null;
  config_fingerprint: string | null;
  frozen_at_utc: string | null;
  random_seed: number | null;
  research_mode: string;
  validation_comparison: Record<string, unknown>[];
  final_test_metrics: Record<string, unknown>[] | null;
}

export interface ExperimentMetrics {
  experiment_id: string;
  partition: string;
  total: number;
  records: Record<string, unknown>[];
}

export interface ExperimentPredictions {
  experiment_id: string;
  partition: string;
  total: number;
  offset: number;
  limit: number;
  records: Record<string, unknown>[];
  selected_only: boolean;
  label: string;
}

export interface FeatureSetInfo {
  id: string;
  name: string | null;
  enabled: boolean;
  status: string;
  columns: string[];
  reason?: string | null;
}

export interface SampleCount {
  split: string;
  horizon_days: number;
  feature_set: string;
  n: number;
  purged_or_missing?: number;
}

export interface ExperimentDataset {
  experiment_id: string;
  available: boolean;
  label: string;
  dataset_id: string | null;
  dataset_version: string | null;
  pipeline_version: string | null;
  target_variable: string | null;
  depth_label: string | null;
  unit: string | null;
  horizons_days: number[];
  feature_sets: FeatureSetInfo[];
  n_joined_rows: number | null;
  eligible_rows: number | null;
  counts: SampleCount[];
  missing_data_policy: string | null;
  satellite_features_enabled: boolean;
  chronological_splits: Record<string, unknown>;
  suitable_for_modeling: boolean;
  is_ground_truth: boolean;
  target_source_kind: string;
}

export interface ExperimentFeature {
  feature_id: string | null;
  column_name: string;
  scientific_meaning: string | null;
  input_source: string | null;
  source_variable: string | null;
  units: string | null;
  temporal_window: string | null;
  formula: string | null;
  missing_data_policy: string | null;
  feature_sets: string[];
  used_by_primary: boolean;
  satellite: boolean;
}

export interface ExperimentFeatures {
  experiment_id: string;
  available: boolean;
  primary_feature_set: string | null;
  satellite_excluded: boolean;
  satellite_reason: string | null;
  predictive_feature_count: number | null;
  records: ExperimentFeature[];
  note: string;
}

export interface TrainingLifecycleStage {
  stage: string;
  label: string;
  status: string;
  artifact: string | null;
}

export interface ExperimentTraining {
  experiment_id: string;
  available: boolean;
  live_training: boolean;
  fitted_on: string | null;
  validation_used_for_fitting: boolean;
  test_used_for_fitting: boolean;
  random_seed: number | null;
  generated_at_utc: string | null;
  selected: Record<string, unknown>[];
  trained_candidate_count: number | null;
  telemetry: {
    available?: boolean;
    format?: string;
    reason?: string | null;
  };
  lifecycle: TrainingLifecycleStage[];
  coefficients: Record<string, unknown>[];
  seasonal_monthly_means: Record<string, unknown> | null;
  suitable_for_modeling: boolean;
  note: string;
}

export interface ExperimentProvenance {
  experiment_id: string;
  available: boolean;
  pipeline_version: string | null;
  dataset_id: string | null;
  dataset_version: string | null;
  config_fingerprint: string | null;
  features_daily_sha256: string | null;
  frozen: boolean;
  frozen_at_utc: string | null;
  test_consulted: boolean;
  test_evaluated_at_utc: string | null;
  test_repeat: boolean | null;
  git_revision: string | null;
  git_dirty: boolean | null;
  python_version: string | null;
  package_versions: Record<string, string>;
  random_seed: number | null;
  research_mode: string;
  operational_forecast: boolean;
  operational_availability_verified: boolean;
  is_ground_truth: boolean;
  is_measured_soil_moisture: boolean;
  suitable_for_modeling: boolean;
  target_source_kind: string;
  training_events_format: string;
  training_events_present: boolean;
  label: string;
}

export interface TrainingRunListItem {
  run_id: string;
  experiment_id: string;
  algorithm: string | null;
  horizon_days: number | null;
  feature_set: string | null;
  status: string;
  inferred_status: string | null;
  created_at_utc: string | null;
  start_at_utc: string | null;
  finish_at_utc: string | null;
  duration_ms: number | null;
  training_duration_ms: number | null;
  training_sample_count: number | null;
  validation_sample_count: number | null;
  selected_feature_count: number | null;
  validation_mae: number | null;
  validation_rmse: number | null;
  validation_skill_mae: number | null;
  provenance_label: string | null;
  execution_mode: string | null;
  is_frozen_phase_4_1_model: boolean;
  test_targets_accessed: boolean;
  suitable_for_modeling: boolean;
  research_mode: string;
}

export interface TrainingRunList {
  experiment_id: string;
  total: number;
  limit: number;
  runs: TrainingRunListItem[];
  live_training: boolean;
  note: string;
}

export interface TrainingEvent {
  schema_version?: string;
  run_id?: string;
  sequence: number;
  timestamp_utc: string;
  elapsed_ms: number;
  event_type: string;
  phase: string;
  model?: string | null;
  horizon_days?: number | null;
  iteration?: number | null;
  metric_name?: string | null;
  metric_value?: number | null;
  metric_unit?: string | null;
  dataset_partition?: string | null;
  details?: Record<string, unknown>;
}

export interface TrainingRunDetail {
  experiment_id: string;
  run_id: string;
  available: boolean;
  live_training: boolean;
  status: string;
  inferred_status: string | null;
  algorithm: string | null;
  horizon_days: number | null;
  feature_set: string | null;
  target_variable: string | null;
  created_at_utc: string | null;
  start_at_utc: string | null;
  finish_at_utc: string | null;
  duration_ms: number | null;
  timings_ms: Record<string, unknown>;
  hyperparameters: Record<string, unknown>;
  diagnostics: Record<string, unknown>;
  dataset_summary: Record<string, unknown>;
  training_summary: Record<string, unknown>;
  metrics: Record<string, unknown>;
  artifacts: Record<string, unknown>;
  git_commit: string | null;
  git_dirty: boolean | null;
  python_version: string | null;
  provenance_label: string | null;
  execution_mode: string | null;
  research_mode: string;
  is_frozen_phase_4_1_model: boolean;
  test_targets_accessed: boolean;
  operational_forecast: boolean;
  operational_availability_verified: boolean;
  is_ground_truth: boolean;
  is_measured_soil_moisture: boolean;
  suitable_for_modeling: boolean;
  telemetry_validation_ok: boolean | null;
  event_count: number | null;
  note: string;
}

export interface TrainingRunEvents {
  experiment_id: string;
  run_id: string;
  total: number;
  returned: number;
  sequence_after: number;
  limit: number;
  truncated_final_line: boolean;
  events: TrainingEvent[];
  live_training: boolean;
  note: string;
}

export interface TrainingRunMetrics {
  experiment_id: string;
  run_id: string;
  records: Record<string, unknown>[];
  history: TrainingEvent[];
  training: Record<string, unknown>;
  validation: Record<string, unknown>;
  live_training: boolean;
  note: string;
}

export interface TrainingRunArtifacts {
  experiment_id: string;
  run_id: string;
  artifacts: { name: string; kind: string; size_bytes: number | null; deserializable: boolean }[];
  live_training: boolean;
  note: string;
}

export type LabTab =
  | "overview"
  | "dataset"
  | "algorithms"
  | "training"
  | "runs"
  | "evaluation"
  | "mathematics"
  | "provenance";

export type AlgorithmId = "persistence" | "seasonal" | "ridge" | "gradient_boosting";
export type PartitionId = "validation" | "test";
