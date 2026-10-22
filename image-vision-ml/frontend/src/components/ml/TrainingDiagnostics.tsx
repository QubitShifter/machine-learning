import { Card } from "@/components/common/Card";
import type { TrainingRunDetail } from "@/types/ml";
import { displayValue, num, text } from "@/utils/mlLab";
import { coefficientRows, formatDurationMs } from "@/utils/runTelemetry";

interface Props {
  detail: TrainingRunDetail;
}

export function TrainingDiagnostics({ detail }: Props) {
  const algorithm = detail.algorithm;
  const diagnostics = detail.diagnostics;
  if (algorithm === "persistence") {
    return (
      <Card title="Persistence diagnostics">
        <ul className="list-disc space-y-1 pl-5 text-sm text-slate-300">
          <li>Formula: θ̂(D+h) = θ(D−1)</li>
          <li>Historical source day: {text(diagnostics.historical_source_day) ?? "D-1"}</li>
          <li>Training samples: {displayValue(num(diagnostics.n_train), 0)}</li>
          <li>Trainable coefficients: 0</li>
          <li>Optimizer: none</li>
          <li>Fitting iterations: not applicable</li>
          <li>Computation duration: {formatDurationMs(num(diagnostics.computation_duration_ms))}</li>
        </ul>
      </Card>
    );
  }
  if (algorithm === "seasonal") {
    const means = (diagnostics.monthly_means ?? {}) as Record<string, number>;
    const counts = (diagnostics.observations_per_month ?? {}) as Record<string, number>;
    return (
      <Card title="Seasonal baseline diagnostics">
        <p className="mb-2 text-sm text-slate-300">Training-only monthly means. Not gradient descent.</p>
        <p className="text-xs text-slate-400">Estimation duration: {formatDurationMs(num(diagnostics.estimation_duration_ms))}</p>
        <p className="text-xs text-slate-400">Missing groups: {Array.isArray(diagnostics.missing_seasonal_groups) ? diagnostics.missing_seasonal_groups.join(", ") || "none" : "Unavailable"}</p>
        <table className="mt-2 min-w-full text-left text-xs text-slate-300">
          <thead><tr><th className="px-2 py-1">Month</th><th className="px-2 py-1">Mean</th><th className="px-2 py-1">n</th></tr></thead>
          <tbody>
            {Object.keys(means).map((month) => (
              <tr key={month} className="border-t border-ink-800">
                <td className="px-2 py-1">{month}</td>
                <td className="px-2 py-1">{displayValue(means[month], 5, "m³/m³")}</td>
                <td className="px-2 py-1">{counts[month] ?? "Unavailable"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    );
  }
  if (algorithm === "ridge") {
    const coef = coefficientRows(detail);
    return (
      <Card title="Ridge diagnostics">
        <ul className="mb-3 list-disc space-y-1 pl-5 text-sm text-slate-300">
          <li>Alpha: {displayValue(num(diagnostics.alpha), 4)}</li>
          <li>Solver: {text(diagnostics.solver) ?? "Unavailable"}</li>
          <li>Features: {displayValue(num(diagnostics.n_features), 0)}</li>
          <li>Scaling: {text(diagnostics.scaler) ?? "Unavailable"}</li>
          <li>Intercept: {displayValue(num(diagnostics.intercept), 5)}</li>
          <li>Fitting duration: {formatDurationMs(num(diagnostics.fitting_duration_ms))}</li>
          <li>Iteration history: {diagnostics.iteration_history_available ? "available" : "not exposed by estimator"}</li>
        </ul>
        <p className="mb-2 text-xs text-sand-200">
          No epoch curve is shown because the standard Ridge estimator solves a linear system rather than reporting gradient-descent epochs.
        </p>
        <table className="min-w-full text-left text-xs text-slate-300">
          <thead><tr><th className="px-2 py-1">Feature</th><th className="px-2 py-1">Coefficient (scaled)</th></tr></thead>
          <tbody>
            {coef.map((row) => (
              <tr key={row.feature} className="border-t border-ink-800">
                <td className="px-2 py-1">{row.feature}</td>
                <td className="px-2 py-1">{displayValue(row.value, 5)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    );
  }
  return (
    <Card title="Histogram gradient boosting diagnostics">
      <ul className="list-disc space-y-1 pl-5 text-sm text-slate-300">
        <li>Fitted iterations (n_iter_): {displayValue(num(diagnostics.n_iter_), 0)}</li>
        <li>Requested max_iter: {displayValue(num(diagnostics.max_iter), 0)}</li>
        <li>Learning rate: {displayValue(num(diagnostics.learning_rate), 4)}</li>
        <li>Max depth: {displayValue(num(diagnostics.max_depth), 0)}</li>
        <li>Early stopping: {String(diagnostics.early_stopping)}</li>
        <li>Fitting duration: {formatDurationMs(num(diagnostics.fitting_duration_ms))}</li>
        <li>Termination: {text(diagnostics.termination) ?? "Unavailable"}</li>
        <li>Native train_score_ available: {String(diagnostics.native_train_score_available)}</li>
        <li>History source: {text(diagnostics.iteration_history_source) ?? "none"}</li>
      </ul>
      <p className="mt-2 text-xs text-slate-500">
        Boosting stages are not gradient-descent epochs. Native score arrays are empty when early stopping is disabled to preserve chronological training.
      </p>
    </Card>
  );
}
