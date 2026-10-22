import { Card } from "@/components/common/Card";
import { Metric } from "@/components/common/Metric";
import { StatusBadge } from "@/components/common/StatusBadge";
import type { AlgorithmId, ExperimentDetail, ExperimentTraining } from "@/types/ml";
import { ALGORITHM_LABELS, displayValue, metricRow, text } from "@/utils/mlLab";

interface Props {
  detail: ExperimentDetail;
  training: ExperimentTraining | undefined;
  algorithm: AlgorithmId;
  horizon: number;
  featureSet: string;
  featureCount: number | null;
  trainN: number | null;
  valN: number | null;
  testN: number | null;
  sourcePeriod: string;
  validationMetrics: Record<string, unknown>[];
  testMetrics: Record<string, unknown>[] | null;
  testEvaluated: boolean;
}

export function TrainingOverview(props: Props) {
  const selected = props.training?.selected.find((row) => (
    text(row.model_id) === props.algorithm
    && Number(row.horizon_days) === props.horizon
  ));
  const val = metricRow(props.validationMetrics, props.algorithm, props.horizon, props.featureSet);
  const test = props.testMetrics
    ? metricRow(props.testMetrics, props.algorithm, props.horizon, props.featureSet)
    : undefined;
  const features = selected
    ? `${ALGORITHM_LABELS[props.algorithm]} · set ${text(selected.feature_set) ?? props.featureSet}`
    : ALGORITHM_LABELS[props.algorithm];

  return (
    <div className="space-y-4">
      <Card title="Experiment summary">
        <p className="mb-3 text-sm text-sand-200">{props.detail.label}</p>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <Metric label="Experiment ID" value={props.detail.experiment_id} />
          <Metric label="Dataset ID" value={props.detail.dataset_id ?? "Unavailable"} />
          <Metric label="Dataset version" value={props.detail.dataset_version ?? "Unavailable"} />
          <Metric label="Pipeline version" value={props.detail.pipeline_version ?? "Unavailable"} />
          <Metric label="Training date" value={props.training?.generated_at_utc ?? "Unavailable"} />
          <Metric label="Source period" value={props.sourcePeriod || "Unavailable"} />
          <Metric label="Target" value={`${props.detail.target_variable ?? "swvl1"} · ${props.detail.depth_label ?? "Unavailable"}`} />
          <Metric label="Unit" value={props.detail.unit ?? "m3 m-3"} />
          <Metric label="Algorithm" value={features} />
          <Metric label="Random seed" value={displayValue(props.detail.random_seed, 0)} />
          <Metric label="Config fingerprint" value={shorten(props.detail.config_fingerprint)} />
          <Metric label="Research mode" value={props.detail.research_mode} />
        </div>
        <div className="mt-3 flex flex-wrap gap-2 text-xs">
          <StatusBadge value={props.detail.frozen ? "complete" : "pending"} label={props.detail.frozen ? "Frozen" : "Not frozen"} />
          <StatusBadge value={props.testEvaluated ? "complete" : "pending"} label={props.testEvaluated ? "Test evaluated" : "Test not evaluated"} />
          <StatusBadge value="limited" label="Research readiness limited" />
          <StatusBadge value="not_ready" label="suitable_for_modeling false" />
        </div>
      </Card>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <Metric label="Training samples" value={displayValue(props.trainN, 0)} hint="Complete-case rows used to fit this horizon and feature set." />
        <Metric label="Validation samples" value={displayValue(props.valN, 0)} hint="2024 rows used for selection, not coefficient fitting." />
        <Metric label="Test samples" value={props.testEvaluated ? displayValue(props.testN, 0) : "Unavailable"} hint="2025 held-out rows after freeze." />
        <Metric label="Predictive features" value={displayValue(props.featureCount, 0)} hint="Documented predictors in the selected feature set." />
        <Metric label="Validation MAE" value={displayValue(numMae(val), 5, "m³/m³")} hint="From stored validation predictions." />
        <Metric
          label="Test MAE"
          value={props.testEvaluated ? displayValue(numMae(test), 5, "m³/m³") : "Unavailable"}
          hint="Shown only after the frozen holdout."
        />
        <Metric
          label="Skill vs persistence"
          value={props.testEvaluated ? displayValue(numSkill(test), 3) : displayValue(numSkill(val), 3)}
          hint="Positive skill means lower MAE than persistence on the same rows."
        />
        <Metric label="Ground truth" value="false" hint="ERA5-Land modeled reference, not field sensors." />
      </div>
    </div>
  );
}

function numMae(row: Record<string, unknown> | undefined): number | null {
  if (!row) return null;
  const value = row.mae;
  return typeof value === "number" ? value : value === undefined || value === null ? null : Number(value);
}

function numSkill(row: Record<string, unknown> | undefined): number | null {
  if (!row) return null;
  const value = row.skill_mae;
  return typeof value === "number" ? value : value === undefined || value === null ? null : Number(value);
}

function shorten(value: string | null): string {
  if (!value) return "Unavailable";
  return value.length > 18 ? `${value.slice(0, 12)}…` : value;
}
