import type { AlgorithmId, SampleCount } from "@/types/ml";

export const ALGORITHM_LABELS: Record<AlgorithmId, string> = {
  persistence: "Persistence",
  seasonal: "Training-year seasonal",
  ridge: "Ridge regression",
  gradient_boosting: "Histogram gradient boosting",
};

export function num(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

export function text(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  const rendered = String(value).trim();
  return rendered === "" || rendered === "NaN" ? null : rendered;
}

export function displayValue(
  value: number | null | undefined,
  digits = 5,
  unit?: string,
): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "Unavailable";
  }
  const formatted = value.toLocaleString("en-US", {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  });
  return unit ? `${formatted} ${unit}` : formatted;
}

export function sampleCount(
  counts: SampleCount[],
  split: string,
  horizon: number,
  featureSet: string,
): number | null {
  const row = counts.find(
    (item) =>
      item.split === split
      && Number(item.horizon_days) === horizon
      && item.feature_set === featureSet,
  );
  return row ? Number(row.n) : null;
}

export function exclusionCount(
  counts: SampleCount[],
  split: string,
  horizon: number,
  featureSet: string,
): number | null {
  const row = counts.find(
    (item) =>
      item.split === split
      && Number(item.horizon_days) === horizon
      && item.feature_set === featureSet,
  );
  if (!row || row.purged_or_missing === undefined || row.purged_or_missing === null) {
    return null;
  }
  return Number(row.purged_or_missing);
}

export function metricRow(
  records: Record<string, unknown>[],
  modelId: string,
  horizon: number,
  featureSet?: string,
): Record<string, unknown> | undefined {
  return records.find((row) => {
    const model = text(row.model_id);
    const days = num(row.horizon_days);
    const setId = text(row.feature_set);
    if (model !== modelId || days !== horizon) return false;
    if (featureSet && setId && setId !== featureSet) return false;
    return true;
  });
}

export function deriveInterpretation(
  testRecords: Record<string, unknown>[],
  horizon: number,
  featureSet: string,
): string[] {
  const models: AlgorithmId[] = ["persistence", "seasonal", "ridge", "gradient_boosting"];
  const rows = models
    .map((modelId) => {
      const row = metricRow(testRecords, modelId, horizon, featureSet);
      return row
        ? { modelId, mae: num(row.mae), skill: num(row.skill_mae), n: num(row.n) }
        : null;
    })
    .filter((item): item is NonNullable<typeof item> => item !== null && item.mae !== null);
  if (!rows.length) {
    return ["Held-out metrics for this selection are unavailable."];
  }
  const ranked = [...rows].sort((a, b) => (a.mae ?? Infinity) - (b.mae ?? Infinity));
  const winner = ranked[0];
  const lines = [
    `On the ${horizon}-day 2025 holdout (${displayValue(winner.n, 0)} matched rows), ${ALGORITHM_LABELS[winner.modelId]} has the lowest MAE (${displayValue(winner.mae, 5)} m³/m³).`,
  ];
  for (const row of rows) {
    if (row.modelId === "persistence") continue;
    if (row.skill === null) {
      lines.push(`${ALGORITHM_LABELS[row.modelId]} skill versus persistence is unavailable.`);
    } else if (row.skill > 0) {
      lines.push(`${ALGORITHM_LABELS[row.modelId]} skill versus persistence is ${displayValue(row.skill, 3)} (better than persistence).`);
    } else if (row.skill < 0) {
      lines.push(`${ALGORITHM_LABELS[row.modelId]} skill versus persistence is ${displayValue(row.skill, 3)} (worse than persistence).`);
    } else {
      lines.push(`${ALGORITHM_LABELS[row.modelId]} matches persistence MAE.`);
    }
  }
  lines.push("Targets are ERA5-Land modeled soil moisture, not field-sensor measurements.");
  return lines;
}

export function trainedAlgorithms(selected: Record<string, unknown>[]): AlgorithmId[] {
  const found = new Set<AlgorithmId>();
  for (const row of selected) {
    const model = text(row.model_id);
    if (model === "persistence" || model === "seasonal" || model === "ridge" || model === "gradient_boosting") {
      found.add(model);
    }
  }
  const order: AlgorithmId[] = ["persistence", "seasonal", "ridge", "gradient_boosting"];
  return order.filter((item) => found.has(item));
}

export function algorithmStatus(
  modelId: AlgorithmId,
  selected: Record<string, unknown>[],
  testEvaluated: boolean,
  telemetryAvailable: boolean,
): string {
  const present = selected.some((row) => text(row.model_id) === modelId);
  if (!present && modelId !== "persistence") return "Not trained";
  if (!telemetryAvailable && (modelId === "ridge" || modelId === "gradient_boosting")) {
    return testEvaluated ? "Evaluation completed · training history unavailable" : "Evaluation not completed · training history unavailable";
  }
  if (testEvaluated) return "Evaluation completed";
  return "Available";
}
