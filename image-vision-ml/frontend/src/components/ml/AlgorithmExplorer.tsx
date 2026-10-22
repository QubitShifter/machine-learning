import { Card } from "@/components/common/Card";
import type { AlgorithmId, ExperimentTraining } from "@/types/ml";
import { ALGORITHM_LABELS, text } from "@/utils/mlLab";

interface Props {
  algorithm: AlgorithmId;
  horizon: number;
  training: ExperimentTraining | undefined;
}

const THEORY: Record<AlgorithmId, {
  summary: string;
  formula: string;
  learned: string;
  optimization: string;
  strengths: string;
  limits: string;
}> = {
  persistence: {
    summary: "The forecast equals the last complete daily mean soil-water content. Nothing is fitted.",
    formula: "θ̂(D+h) = θ(D−1)",
    learned: "No parameters.",
    optimization: "None. There are no epochs and no gradients.",
    strengths: "Strong when soil moisture changes slowly. Required benchmark.",
    limits: "Cannot anticipate rainfall-driven wetting. Derived change is exactly zero.",
  },
  seasonal: {
    summary: "A training-year monthly mean of the target calendar month. Not a long-term climatology.",
    formula: "θ̂(D+h) = μ_train, month(D+h)",
    learned: "Twelve monthly means from 2023 training targets only.",
    optimization: "Sample mean. February 29 uses February if present.",
    strengths: "Captures a crude annual cycle without weather inputs.",
    limits: "One training year is not a long-term climatology. Compare stored metrics rather than assuming seasonal skill.",
  },
  ridge: {
    summary: "Linear prediction of moisture from scaled historical soil and weather features, with an L2 penalty.",
    formula: "ŷ = β₀ + Σ βⱼ xⱼ,  loss = Σ (y − ŷ)² + α Σ βⱼ²",
    learned: "Intercept and coefficients on StandardScaler units. Alpha is chosen on 2024 MAE.",
    optimization: "sklearn Ridge solves a regularized linear system. This is not gradient-descent epoch training.",
    strengths: "Interpretable, stable with correlated rainfall features.",
    limits: "Linear. Regularization can shrink useful coefficients if alpha is large.",
  },
  gradient_boosting: {
    summary: "Stagewise ensemble of shallow regression trees (HistGradientBoostingRegressor).",
    formula: "Fₘ(x) = Fₘ₋₁(x) + ν hₘ(x), where hₘ fits a residual of the loss.",
    learned: "Tree splits, leaf values, learning rate, depth, iteration count.",
    optimization: "Functional gradient boosting of squared error, not neural backpropagation.",
    strengths: "Can represent nonlinear rainfall–moisture responses.",
    limits: "Easy to overfit one training year. Stagewise trees are not neural-network backpropagation.",
  },
};

export function AlgorithmExplorer({ algorithm, horizon, training }: Props) {
  const theory = THEORY[algorithm] ?? THEORY.persistence;
  const selected = training?.selected.find((row) => (
    text(row.model_id) === algorithm && Number(row.horizon_days) === horizon
  ));
  const ridge = (training?.coefficients ?? []).find((row) => Number(row.horizon_days) === horizon && row.available);
  const seasonal = training?.seasonal_monthly_means
    ? (training.seasonal_monthly_means as Record<string, { monthly_means?: Record<string, number> }>)[String(horizon)]
    : undefined;

  return (
    <div className="space-y-4">
      <Card title={ALGORITHM_LABELS[algorithm]}>
        <p className="text-sm text-slate-200">{theory.summary}</p>
        <p className="mt-2 font-mono text-xs text-moss-300">{theory.formula}</p>
        <dl className="mt-3 grid gap-2 text-sm text-slate-300 md:grid-cols-2">
          <div><dt className="text-xs uppercase text-slate-500">Learned</dt><dd>{theory.learned}</dd></div>
          <div><dt className="text-xs uppercase text-slate-500">Optimization</dt><dd>{theory.optimization}</dd></div>
          <div><dt className="text-xs uppercase text-slate-500">Strengths</dt><dd>{theory.strengths}</dd></div>
          <div><dt className="text-xs uppercase text-slate-500">Limitations</dt><dd>{theory.limits}</dd></div>
        </dl>
      </Card>
      <Card title="Actual fitted parameters from artifacts">
        {!selected ? (
          <p className="text-sm text-slate-400">This algorithm was not among the frozen selected models for the current horizon.</p>
        ) : (
          <ul className="space-y-1 text-sm text-slate-300">
            <li>Feature set {text(selected.feature_set) ?? "Unavailable"}</li>
            <li>Training rows {String(selected.n_train ?? selected.n ?? "Unavailable")}</li>
            {algorithm === "ridge" ? <li>Alpha {String(selected.alpha ?? "Unavailable")}</li> : null}
            {algorithm === "gradient_boosting" ? (
              <>
                <li>Max depth {String(selected.max_depth ?? "Unavailable")}</li>
                <li>Learning rate {String(selected.learning_rate ?? "Unavailable")}</li>
                <li>Max iter {String(selected.max_iter ?? "Unavailable")}</li>
              </>
            ) : null}
            <li>Artifact {text(selected.path) ?? "none (persistence)"}</li>
          </ul>
        )}
        {algorithm === "ridge" && ridge && Array.isArray(ridge.coefficients) ? (
          <div className="mt-3 overflow-x-auto">
            <p className="text-xs text-slate-500">{String(ridge.note)}</p>
            <table className="mt-2 min-w-full text-left text-xs">
              <thead><tr><th className="px-2 py-1">Feature</th><th className="px-2 py-1">Scaled coefficient</th></tr></thead>
              <tbody>
                {(ridge.coefficients as Array<{ feature: string; value: number }>).map((item) => (
                  <tr key={item.feature} className="border-t border-ink-700">
                    <td className="px-2 py-1 font-mono">{item.feature}</td>
                    <td className="px-2 py-1">{item.value.toFixed(4)}</td>
                  </tr>
                ))}
                <tr className="border-t border-ink-700">
                  <td className="px-2 py-1">intercept</td>
                  <td className="px-2 py-1">{Number(ridge.intercept).toFixed(4)}</td>
                </tr>
              </tbody>
            </table>
          </div>
        ) : null}
        {algorithm === "seasonal" && seasonal?.monthly_means ? (
          <p className="mt-3 text-xs text-slate-400">
            Training-year monthly means (m³/m³): {Object.entries(seasonal.monthly_means).map(([month, value]) => `${month}=${Number(value).toFixed(3)}`).join(", ")}
          </p>
        ) : null}
      </Card>
      <Card title="Gradient descent (educational)">
        <p className="text-sm text-slate-200">
          Gradient descent updates parameters with θ_next = θ_current − learning_rate × gradient.
          It is a general optimizer for differentiable losses, not the solver used by Phase 4.1 Ridge,
          and it is not gradient boosting.
        </p>
        <dl className="mt-3 grid gap-2 text-sm text-slate-300 md:grid-cols-2">
          <div><dt className="text-xs uppercase text-slate-500">Objective</dt><dd>A scalar loss of the current parameters.</dd></div>
          <div><dt className="text-xs uppercase text-slate-500">Gradient</dt><dd>Direction of steepest increase of that loss.</dd></div>
          <div><dt className="text-xs uppercase text-slate-500">Learning rate</dt><dd>Step size. Too small crawls; too large diverges.</dd></div>
          <div><dt className="text-xs uppercase text-slate-500">Minima</dt><dd>Quadratic bowls have a unique global minimum; non-convex losses may have local minima.</dd></div>
        </dl>
        <p className="mt-2 text-xs text-sand-200">
          Educational simulation — not training telemetry from the agricultural model. Use the Mathematics tab for the quadratic demo.
        </p>
      </Card>
    </div>
  );
}
