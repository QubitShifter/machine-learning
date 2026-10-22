import type { TrainingEvent, TrainingRunDetail, TrainingRunListItem } from "@/types/ml";
import { num, text } from "@/utils/mlLab";

export const PLAYBACK_LABEL = "Historical training playback";

const TIMELINE_TYPES = [
  "run_created",
  "dataset_validation_completed",
  "features_prepared",
  "split_verified",
  "preprocessing_completed",
  "training_started",
  "training_completed",
  "validation_completed",
  "artifact_saved",
  "run_completed",
  "run_failed",
] as const;

export function formatDurationMs(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "Unavailable";
  }
  if (value < 1000) return `${Math.round(value)} ms`;
  const seconds = value / 1000;
  if (seconds < 60) return `${seconds.toFixed(seconds < 10 ? 2 : 1)} s`;
  const minutes = Math.floor(seconds / 60);
  const rest = seconds - minutes * 60;
  return `${minutes} min ${rest.toFixed(0)} s`;
}

export function iterationDisplay(
  algorithm: string | null | undefined,
  diagnostics: Record<string, unknown> | undefined,
): { value: string; reason: string } {
  const model = algorithm ?? "";
  if (model === "persistence" || model === "seasonal") {
    return { value: "Not applicable", reason: "Non-trained baseline. No optimizer iterations." };
  }
  if (diagnostics?.iteration_history_available === false && diagnostics?.training_iterations == null) {
    return {
      value: "Not recorded",
      reason: text(diagnostics.iteration_history_reason) ?? "The estimator did not expose an iteration history.",
    };
  }
  const count = num(diagnostics?.training_iterations ?? diagnostics?.n_iter_);
  if (count === null) {
    return { value: "Not recorded", reason: "Fitted iteration count was not stored." };
  }
  return { value: String(count), reason: model === "gradient_boosting" ? "Boosting stages (n_iter_), not gradient-descent epochs." : "Recorded iterations." };
}

export interface MetricPoint {
  iteration: number | null;
  elapsed_ms: number;
  value: number;
  metric_name: string;
  dataset_partition: string;
  timestamp_utc: string;
  calculation_method: string | null;
}

export function metricHistoryPoints(events: TrainingEvent[], metricName?: string): MetricPoint[] {
  return events
    .filter((event) => event.event_type === "training_metric" && event.metric_value !== null && event.metric_value !== undefined)
    .filter((event) => (metricName ? event.metric_name === metricName : true))
    .filter((event) => Number.isFinite(Number(event.metric_value)))
    .map((event) => ({
      iteration: event.iteration ?? null,
      elapsed_ms: event.elapsed_ms,
      value: Number(event.metric_value),
      metric_name: String(event.metric_name),
      dataset_partition: String(event.dataset_partition ?? "unspecified"),
      timestamp_utc: event.timestamp_utc,
      calculation_method: text(event.details?.calculation_method),
    }));
}

export function availableMetricNames(events: TrainingEvent[]): string[] {
  const names = new Set<string>();
  for (const event of events) {
    if (event.event_type === "training_metric" && event.metric_name) names.add(event.metric_name);
  }
  return [...names];
}

export function missingCurveExplanation(algorithm: string | null | undefined, points: MetricPoint[]): string | null {
  if (points.length > 0) return null;
  if (algorithm === "persistence") {
    return "Persistence is a non-trained forecasting baseline. It has no training-loss curve.";
  }
  if (algorithm === "seasonal") {
    return "The seasonal baseline estimates monthly means from training targets. There is no optimization curve.";
  }
  if (algorithm === "ridge") {
    return "Ridge solved a regularized linear system. sklearn's default solver does not expose an epoch loss history, so none is plotted.";
  }
  if (algorithm === "gradient_boosting") {
    return "No stagewise metric history was recorded for this run. Native train_score_ is empty when early stopping is disabled.";
  }
  return "No metric history was recorded for this run.";
}

export interface TimelineItem {
  event_type: string;
  label: string;
  timestamp_utc: string;
  elapsed_ms: number;
  sequence: number;
  failed?: boolean;
}

export function timelineFromEvents(events: TrainingEvent[]): TimelineItem[] {
  const labels: Record<string, string> = {
    run_created: "Run created",
    dataset_validation_completed: "Dataset checked",
    features_prepared: "Features prepared",
    split_verified: "Split verified",
    preprocessing_completed: "Preprocessing completed",
    training_started: "Training started",
    training_completed: "Training finished",
    validation_completed: "Validation evaluated",
    artifact_saved: "Model artifacts written",
    run_completed: "Run completed",
    run_failed: "Run failed",
  };
  return events
    .filter((event) => (TIMELINE_TYPES as readonly string[]).includes(event.event_type))
    .map((event) => ({
      event_type: event.event_type,
      label: labels[event.event_type] ?? event.event_type,
      timestamp_utc: event.timestamp_utc,
      elapsed_ms: event.elapsed_ms,
      sequence: event.sequence,
      failed: event.event_type === "run_failed",
    }));
}

export function eventsThrough(events: TrainingEvent[], index: number): TrainingEvent[] {
  if (index < 0) return [];
  return events.slice(0, Math.min(index + 1, events.length));
}

export function safeErrorSummary(details: Record<string, unknown> | undefined): string {
  const raw = text(details?.error) ?? "Run failed.";
  return raw.replace(/\/home\/[^\s]+/g, "[path]").replace(/[A-Za-z]:\\[^\s]+/g, "[path]");
}

export interface ComparisonCompatibility {
  compatible: boolean;
  warnings: string[];
}

export function comparisonCompatibility(runs: Array<Pick<TrainingRunListItem, "run_id" | "horizon_days" | "algorithm" | "feature_set" | "validation_sample_count" | "status">>): ComparisonCompatibility {
  const warnings: string[] = [];
  if (runs.length < 2) {
    return { compatible: false, warnings: ["Select at least two completed runs."] };
  }
  const horizons = new Set(runs.map((item) => item.horizon_days));
  if (horizons.size > 1) warnings.push("Forecast horizons differ. Validation MAE is not directly comparable.");
  const samples = new Set(runs.map((item) => item.validation_sample_count));
  if (samples.size > 1) warnings.push("Validation row counts differ. Do not declare a winner without qualification.");
  const incomplete = runs.filter((item) => item.status !== "completed");
  if (incomplete.length) warnings.push("Only completed runs should be ranked on validation metrics.");
  const comparable = horizons.size === 1 && samples.size === 1 && incomplete.length === 0;
  return { compatible: comparable, warnings };
}

export function statusTone(status: string | null | undefined): string {
  if (status === "completed") return "complete";
  if (status === "failed" || status === "interrupted") return "failed";
  if (status === "training" || status === "validating" || status === "saving" || status === "preparing") return "pending";
  return "missing";
}

export function coefficientRows(detail: TrainingRunDetail | undefined): Array<{ feature: string; value: number }> {
  const raw = detail?.diagnostics?.coefficients;
  if (!Array.isArray(raw)) return [];
  return raw
    .map((item) => {
      if (!item || typeof item !== "object") return null;
      const row = item as { feature?: unknown; value?: unknown };
      const value = num(row.value);
      const feature = text(row.feature);
      if (feature === null || value === null) return null;
      return { feature, value };
    })
    .filter((item): item is { feature: string; value: number } => item !== null);
}
