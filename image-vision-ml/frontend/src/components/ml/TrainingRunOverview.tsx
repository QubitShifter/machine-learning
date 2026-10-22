import { Card } from "@/components/common/Card";
import { Metric } from "@/components/common/Metric";
import { StatusBadge } from "@/components/common/StatusBadge";
import type { TrainingRunDetail } from "@/types/ml";
import { ALGORITHM_LABELS, displayValue, num } from "@/utils/mlLab";
import { formatDurationMs, iterationDisplay, statusTone } from "@/utils/runTelemetry";
import type { AlgorithmId } from "@/types/ml";

interface Props {
  detail: TrainingRunDetail;
}

export function TrainingRunOverview({ detail }: Props) {
  const algorithm = (detail.algorithm ?? "persistence") as AlgorithmId;
  const iterations = iterationDisplay(detail.algorithm, detail.diagnostics);
  const trainMs = num(detail.timings_ms.model_fitting ?? detail.timings_ms.ridge_fit ?? detail.timings_ms.boosting_fit);
  const val = detail.metrics?.validation as Record<string, unknown> | undefined;
  return (
    <Card title="Training run summary">
      <p className="mb-3 text-sm text-sand-200">
        Research-development telemetry run. Not the frozen Phase 4.1 model. 2025 test labels were not accessed.
      </p>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <Metric label="Algorithm" value={ALGORITHM_LABELS[algorithm] ?? String(detail.algorithm)} />
        <Metric label="Target soil layer" value={String(detail.target_variable ?? "swvl1")} hint="ERA5-Land modeled 0–7 cm" />
        <Metric label="Forecast horizon" value={`${detail.horizon_days ?? "Unavailable"} day`} />
        <Metric label="Training samples" value={displayValue(detail.dataset_summary.training_sample_count as number | null, 0)} />
        <Metric label="Validation samples" value={displayValue(detail.dataset_summary.validation_sample_count as number | null, 0)} />
        <Metric label="Features" value={displayValue(detail.dataset_summary.selected_feature_count as number | null, 0)} />
        <Metric label="Training duration" value={formatDurationMs(trainMs)} />
        <Metric label="Total duration" value={formatDurationMs(detail.duration_ms)} />
        <Metric label="Iterations" value={iterations.value} hint={iterations.reason} />
        <Metric label="Training status" value={detail.inferred_status ?? detail.status} />
        <Metric label="Validation MAE" value={displayValue(num(val?.mae), 5, "m³/m³")} hint="Evaluation metric after fitting, not training loss." />
        <Metric label="Validation RMSE" value={displayValue(num(val?.rmse), 5, "m³/m³")} />
        <Metric label="Skill vs persistence" value={displayValue(num(val?.skill_mae), 3)} hint="Same validation rows as this run only." />
        <Metric label="Provenance" value={detail.provenance_label ?? "Unavailable"} />
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-xs">
        <StatusBadge value={statusTone(detail.status)} label={detail.status} />
        <StatusBadge value="not_ready" label="suitable_for_modeling false" />
        <StatusBadge value="not_ready" label="is_ground_truth false" />
        <StatusBadge value="limited" label={detail.execution_mode ?? "research_development"} />
      </div>
    </Card>
  );
}
