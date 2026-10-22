import { Card } from "@/components/common/Card";
import type { TrainingRunListItem } from "@/types/ml";
import { ALGORITHM_LABELS, displayValue } from "@/utils/mlLab";
import { comparisonCompatibility, formatDurationMs } from "@/utils/runTelemetry";
import type { AlgorithmId } from "@/types/ml";

interface Props {
  runs: TrainingRunListItem[];
  selectedIds: string[];
  onToggle: (runId: string) => void;
}

export function TrainingRunComparison({ runs, selectedIds, onToggle }: Props) {
  const selected = runs.filter((item) => selectedIds.includes(item.run_id));
  const compatibility = comparisonCompatibility(selected);
  return (
    <Card title="Training run comparison">
      <p className="mb-2 text-xs text-slate-400">
        Compare completed research-development runs. Faster fitting is not treated as higher accuracy.
        Training-loss values from different objectives are not ranked together.
      </p>
      <ul className="mb-3 space-y-1 text-sm">
        {runs.map((run) => (
          <li key={run.run_id}>
            <label className="flex items-center gap-2 text-slate-200">
              <input
                type="checkbox"
                checked={selectedIds.includes(run.run_id)}
                onChange={() => onToggle(run.run_id)}
                aria-label={`Compare ${run.run_id}`}
              />
              <span className="font-mono text-xs">{run.run_id}</span>
              <span>{run.algorithm} h={run.horizon_days} {run.feature_set}</span>
            </label>
          </li>
        ))}
      </ul>
      {selected.length < 2 ? (
        <p className="text-sm text-slate-400">Select two or more runs to compare.</p>
      ) : (
        <>
          {compatibility.warnings.map((warning) => (
            <p key={warning} className="text-sm text-sand-200">{warning}</p>
          ))}
          <div className="mt-3 overflow-auto">
            <table className="min-w-full text-left text-xs text-slate-300">
              <thead>
                <tr className="text-slate-400">
                  <th className="px-2 py-1">Run</th>
                  <th className="px-2 py-1">Algorithm</th>
                  <th className="px-2 py-1">h</th>
                  <th className="px-2 py-1">Set</th>
                  <th className="px-2 py-1">Train n</th>
                  <th className="px-2 py-1">Val n</th>
                  <th className="px-2 py-1">Fit</th>
                  <th className="px-2 py-1">Total</th>
                  <th className="px-2 py-1">Val MAE</th>
                  <th className="px-2 py-1">Val RMSE</th>
                  <th className="px-2 py-1">Skill</th>
                </tr>
              </thead>
              <tbody>
                {selected.map((run) => (
                  <tr key={run.run_id} className="border-t border-ink-700">
                    <td className="break-all px-2 py-1 font-mono">{run.run_id}</td>
                    <td className="px-2 py-1">{ALGORITHM_LABELS[run.algorithm as AlgorithmId] ?? run.algorithm}</td>
                    <td className="px-2 py-1">{run.horizon_days}</td>
                    <td className="px-2 py-1">{run.feature_set}</td>
                    <td className="px-2 py-1">{displayValue(run.training_sample_count, 0)}</td>
                    <td className="px-2 py-1">{displayValue(run.validation_sample_count, 0)}</td>
                    <td className="px-2 py-1">{formatDurationMs(run.training_duration_ms)}</td>
                    <td className="px-2 py-1">{formatDurationMs(run.duration_ms)}</td>
                    <td className="px-2 py-1">{displayValue(run.validation_mae, 5)}</td>
                    <td className="px-2 py-1">{displayValue(run.validation_rmse, 5)}</td>
                    <td className="px-2 py-1">{displayValue(run.validation_skill_mae, 3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {compatibility.compatible ? (
            <p className="mt-2 text-xs text-slate-500">
              Horizons, validation counts, and metric definitions match. This still does not replace the frozen 2025 holdout comparison.
            </p>
          ) : (
            <p className="mt-2 text-xs text-sand-200">No unqualified winner is shown because the evaluation row sets or horizons differ.</p>
          )}
        </>
      )}
    </Card>
  );
}
