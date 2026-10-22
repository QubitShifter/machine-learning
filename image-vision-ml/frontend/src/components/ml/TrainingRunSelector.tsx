import type { TrainingRunListItem } from "@/types/ml";
import { ALGORITHM_LABELS } from "@/utils/mlLab";
import { formatDurationMs } from "@/utils/runTelemetry";

interface Props {
  runs: TrainingRunListItem[];
  runId: string;
  onRunId: (value: string) => void;
  algorithmFilter: string;
  onAlgorithmFilter: (value: string) => void;
  horizonFilter: string;
  onHorizonFilter: (value: string) => void;
  featureSetFilter: string;
  onFeatureSetFilter: (value: string) => void;
  statusFilter: string;
  onStatusFilter: (value: string) => void;
}

export function TrainingRunSelector(props: Props) {
  return (
    <div className="space-y-3">
      <p className="text-xs text-slate-400">
        Frozen Phase 4.1 evaluation is the original experiment without iteration telemetry.
        Rows below are separately trained research-development runs.
      </p>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <label className="block text-xs text-slate-400">
          Algorithm filter
          <select className={selectClass} aria-label="Run algorithm filter" value={props.algorithmFilter} onChange={(event) => props.onAlgorithmFilter(event.target.value)}>
            <option value="">All algorithms</option>
            {Object.entries(ALGORITHM_LABELS).map(([id, label]) => (
              <option key={id} value={id}>{label}</option>
            ))}
          </select>
        </label>
        <label className="block text-xs text-slate-400">
          Horizon filter
          <select className={selectClass} aria-label="Run horizon filter" value={props.horizonFilter} onChange={(event) => props.onHorizonFilter(event.target.value)}>
            <option value="">All horizons</option>
            <option value="1">1 day</option>
            <option value="3">3 day</option>
            <option value="7">7 day</option>
          </select>
        </label>
        <label className="block text-xs text-slate-400">
          Feature-set filter
          <select className={selectClass} aria-label="Run feature-set filter" value={props.featureSetFilter} onChange={(event) => props.onFeatureSetFilter(event.target.value)}>
            <option value="">All feature sets</option>
            <option value="A">A</option>
            <option value="B">B</option>
            <option value="C">C</option>
          </select>
        </label>
        <label className="block text-xs text-slate-400">
          Status filter
          <select className={selectClass} aria-label="Run status filter" value={props.statusFilter} onChange={(event) => props.onStatusFilter(event.target.value)}>
            <option value="">All statuses</option>
            <option value="completed">completed</option>
            <option value="failed">failed</option>
            <option value="interrupted">interrupted</option>
          </select>
        </label>
      </div>
      {props.runs.length === 0 ? (
        <p className="text-sm text-sand-200" data-testid="training-runs-empty">
          No telemetry-enabled training runs are stored for this experiment. The frozen Phase 4.1
          evaluation remains available on the other tabs. New runs are created only by an explicit CLI train-run.
        </p>
      ) : (
        <label className="block text-xs text-slate-400">
          Training run
          <select
            className={selectClass}
            aria-label="Training run"
            value={props.runId}
            onChange={(event) => props.onRunId(event.target.value)}
          >
            {props.runs.map((run) => (
              <option key={run.run_id} value={run.run_id}>
                {run.run_id} · {run.algorithm} · h={run.horizon_days} · {run.status} · {formatDurationMs(run.duration_ms)}
                {run.validation_mae != null ? ` · val MAE ${run.validation_mae}` : ""}
              </option>
            ))}
          </select>
        </label>
      )}
    </div>
  );
}

const selectClass = "mt-1 w-full rounded border border-ink-600 bg-ink-800 px-2 py-1.5 text-sm text-slate-100";
