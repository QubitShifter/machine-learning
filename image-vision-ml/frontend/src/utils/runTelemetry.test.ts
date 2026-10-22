import { describe, expect, it } from "vitest";
import type { TrainingEvent } from "@/types/ml";
import {
  comparisonCompatibility,
  eventsThrough,
  formatDurationMs,
  iterationDisplay,
  metricHistoryPoints,
  missingCurveExplanation,
  safeErrorSummary,
  timelineFromEvents,
} from "./runTelemetry";

function event(partial: Partial<TrainingEvent> & Pick<TrainingEvent, "sequence" | "event_type">): TrainingEvent {
  return {
    timestamp_utc: "2026-10-22T19:00:00Z",
    elapsed_ms: partial.sequence * 10,
    phase: "fit",
    ...partial,
  };
}

describe("run telemetry helpers", () => {
  it("formats durations without inventing values", () => {
    expect(formatDurationMs(null)).toBe("Unavailable");
    expect(formatDurationMs(250)).toBe("250 ms");
    expect(formatDurationMs(1500)).toBe("1.50 s");
  });

  it("labels missing iteration counts by algorithm semantics", () => {
    expect(iterationDisplay("persistence", { training_iterations: 0 }).value).toBe("Not applicable");
    expect(iterationDisplay("ridge", { iteration_history_available: false, training_iterations: null }).value).toBe("Not recorded");
    expect(iterationDisplay("gradient_boosting", { training_iterations: 8, n_iter_: 8 }).value).toBe("8");
  });

  it("keeps only recorded metric points", () => {
    const events = [
      event({ sequence: 1, event_type: "run_created" }),
      event({ sequence: 2, event_type: "training_metric", metric_name: "training_mse", metric_value: 0.02, iteration: 1, dataset_partition: "train" }),
      event({ sequence: 3, event_type: "training_metric", metric_name: "training_mse", metric_value: 0.01, iteration: 2, dataset_partition: "train" }),
    ];
    const points = metricHistoryPoints(events, "training_mse");
    expect(points.map((item) => item.value)).toEqual([0.02, 0.01]);
    expect(points).toHaveLength(2);
  });

  it("explains missing curves without fabricating points", () => {
    expect(missingCurveExplanation("persistence", [])).toMatch(/non-trained/i);
    expect(missingCurveExplanation("ridge", [])).toMatch(/linear system/i);
    expect(missingCurveExplanation("ridge", [{ iteration: 1, elapsed_ms: 1, value: 1, metric_name: "mae", dataset_partition: "validation", timestamp_utc: "", calculation_method: null }])).toBeNull();
  });

  it("builds a timeline only from actual events", () => {
    const items = timelineFromEvents([
      event({ sequence: 1, event_type: "run_created", phase: "created" }),
      event({ sequence: 2, event_type: "training_iteration", iteration: 1 }),
      event({ sequence: 3, event_type: "run_completed", phase: "completed" }),
    ]);
    expect(items.map((item) => item.event_type)).toEqual(["run_created", "run_completed"]);
  });

  it("supports historical playback slicing", () => {
    const events = [
      event({ sequence: 1, event_type: "run_created" }),
      event({ sequence: 2, event_type: "training_started" }),
      event({ sequence: 3, event_type: "run_completed" }),
    ];
    expect(eventsThrough(events, 1)).toHaveLength(2);
    expect(eventsThrough(events, -1)).toHaveLength(0);
  });

  it("warns when comparison rows are not aligned", () => {
    const result = comparisonCompatibility([
      { run_id: "a", horizon_days: 1, algorithm: "ridge", feature_set: "C", validation_sample_count: 20, status: "completed" },
      { run_id: "b", horizon_days: 3, algorithm: "ridge", feature_set: "C", validation_sample_count: 19, status: "completed" },
    ]);
    expect(result.compatible).toBe(false);
    expect(result.warnings.join(" ")).toMatch(/horizons differ/i);
  });

  it("redacts filesystem paths from failure summaries", () => {
    expect(safeErrorSummary({ error: "OSError: /home/gpetrov/secret/file.csv missing" })).toContain("[path]");
    expect(safeErrorSummary({ error: "OSError: /home/gpetrov/secret/file.csv missing" })).not.toContain("/home/gpetrov");
  });
});
