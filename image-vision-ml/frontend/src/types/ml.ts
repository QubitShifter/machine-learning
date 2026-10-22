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

export type LabTab =
  | "overview"
  | "dataset"
  | "algorithms"
  | "training"
  | "evaluation"
  | "mathematics"
  | "provenance";

export type AlgorithmId = "persistence" | "seasonal" | "ridge" | "gradient_boosting";
export type PartitionId = "validation" | "test";
