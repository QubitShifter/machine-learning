import { Card } from "@/components/common/Card";
import { StatusBadge } from "@/components/common/StatusBadge";
import type { ExperimentTraining } from "@/types/ml";

interface Props {
  training: ExperimentTraining | undefined;
}

export function TrainingLifecycle({ training }: Props) {
  const telemetry = training?.telemetry;
  return (
    <div className="space-y-4">
      <Card title="Training lifecycle">
        <ol className="space-y-2">
          {(training?.lifecycle ?? []).map((stage, index) => (
            <li key={stage.stage} className="flex items-start justify-between gap-3 rounded border border-ink-700 px-3 py-2 text-sm">
              <span>
                <span className="mr-2 text-slate-500">{index + 1}.</span>
                {stage.label}
                {stage.artifact ? <span className="ml-2 font-mono text-[11px] text-slate-500">{stage.artifact}</span> : null}
              </span>
              <StatusBadge
                value={stage.status === "completed" ? "complete" : "missing"}
                label={stage.status}
              />
            </li>
          ))}
        </ol>
        <p className="mt-3 text-xs text-slate-500">
          These stages describe the stored Phase 4.1 run. Live training is {training?.live_training ? "active" : "not implemented"}.
          GET requests do not fit models.
        </p>
      </Card>
      <Card title="Historical training telemetry">
        {telemetry?.available ? (
          <p className="text-sm text-slate-200">Per-iteration events are present in training_events.jsonl.</p>
        ) : (
          <p className="text-sm text-sand-200" data-testid="training-history-unavailable">
            {telemetry?.reason ?? "Training history unavailable — this experiment recorded final metrics but not per-iteration telemetry."}
          </p>
        )}
        <p className="mt-2 text-xs text-slate-500">
          Final MAE is not reconstructed into a loss curve. Persistence and the seasonal baseline have no gradient-descent epochs.
          Ridge used a linear-system solver. Boosting stages were not logged.
        </p>
      </Card>
    </div>
  );
}
