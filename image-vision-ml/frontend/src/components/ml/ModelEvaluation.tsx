import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card } from "@/components/common/Card";
import type { AlgorithmId, PartitionId } from "@/types/ml";
import { ALGORITHM_LABELS, deriveInterpretation, displayValue, metricRow, num, text } from "@/utils/mlLab";

interface Props {
  horizon: number;
  featureSet: string;
  partition: PartitionId;
  algorithm: AlgorithmId;
  validationRecords: Record<string, unknown>[];
  testRecords: Record<string, unknown>[];
  testEvaluated: boolean;
  predictions: Record<string, unknown>[];
  predictionLabel: string;
}

const MODELS: AlgorithmId[] = ["persistence", "seasonal", "ridge", "gradient_boosting"];
const COLORS: Record<string, string> = {
  observed: "#e2e8f0",
  persistence: "#94a3b8",
  seasonal: "#c4a574",
  ridge: "#7dce9a",
  gradient_boosting: "#60a5fa",
};

export function ModelEvaluation(props: Props) {
  const records = props.partition === "test" ? props.testRecords : props.validationRecords;
  const bars = MODELS.map((modelId) => {
    const row = metricRow(records, modelId, props.horizon, props.featureSet);
    return {
      name: ALGORITHM_LABELS[modelId],
      mae: num(row?.mae),
      rmse: num(row?.rmse),
      skill: num(row?.skill_mae),
      n: num(row?.n),
    };
  });
  const series = useMemo(() => pivotPredictions(props.predictions), [props.predictions]);
  const residuals = useMemo(() => {
    return props.predictions
      .filter((row) => text(row.model_id) === props.algorithm)
      .map((row) => {
        const observed = num(row.observed_modeled_target);
        const predicted = num(row.prediction);
        if (observed === null || predicted === null) return null;
        return { date: text(row.issue_date_utc) ?? "", error: predicted - observed };
      })
      .filter((item): item is { date: string; error: number } => item !== null);
  }, [props.predictions, props.algorithm]);
  const histogram = useMemo(() => binResiduals(residuals.map((item) => item.error)), [residuals]);
  const selected = metricRow(records, props.algorithm, props.horizon, props.featureSet);
  const interpretation = props.testEvaluated
    ? deriveInterpretation(props.testRecords, props.horizon, props.featureSet)
    : ["The 2025 holdout has not been evaluated for this experiment."];

  return (
    <div className="space-y-4">
      <Card title={`Model comparison · ${props.partition === "test" ? "final test 2025" : "validation 2024"} · h=${props.horizon}`}>
        <div className="h-72 w-full min-w-0" data-testid="model-comparison-chart">
          <ResponsiveContainer>
            <BarChart data={bars}>
              <CartesianGrid stroke="#1a3144" strokeDasharray="3 3" />
              <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <Tooltip contentStyle={{ background: "#122230", border: "1px solid #27445c" }} />
              <Legend />
              <Bar dataKey="mae" name="MAE" fill="#7dce9a" isAnimationActive={false} />
              <Bar dataKey="rmse" name="RMSE" fill="#60a5fa" isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="mt-4 h-56 w-full min-w-0">
          <ResponsiveContainer>
            <BarChart data={bars}>
              <CartesianGrid stroke="#1a3144" strokeDasharray="3 3" />
              <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <ReferenceLine y={0} stroke="#64748b" />
              <Tooltip contentStyle={{ background: "#122230", border: "1px solid #27445c" }} />
              <Bar dataKey="skill" name="Skill vs persistence" fill="#c4a574" isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <p className="mt-2 text-xs text-slate-500">
          Lower MAE/RMSE is better. Skill is 1 − MAE_model/MAE_persistence. n={displayValue(selected ? num(selected.n) : null, 0)}.
        </p>
      </Card>
      <Card title="Forecast versus ERA5-Land modeled reference">
        <p className="mb-2 text-xs text-sand-200">ERA5-Land modeled reference — not field sensor measurement.</p>
        <div className="h-72 w-full min-w-0" data-testid="prediction-comparison-chart">
          <ResponsiveContainer>
            <LineChart data={series}>
              <CartesianGrid stroke="#1a3144" strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fill: "#94a3b8", fontSize: 10 }} minTickGap={28} />
              <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <Tooltip contentStyle={{ background: "#122230", border: "1px solid #27445c" }} />
              <Legend />
              <Line dataKey="observed" name="Modeled swvl1" stroke={COLORS.observed} dot={false} isAnimationActive={false} />
              {MODELS.map((modelId) => (
                series.some((row) => row[modelId] !== undefined) ? (
                  <Line
                    key={modelId}
                    dataKey={modelId}
                    name={ALGORITHM_LABELS[modelId]}
                    stroke={COLORS[modelId]}
                    dot={false}
                    isAnimationActive={false}
                  />
                ) : null
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
        <p className="mt-2 text-xs text-slate-500">{props.predictionLabel}</p>
      </Card>
      <Card title={`Residuals · ${ALGORITHM_LABELS[props.algorithm]} · predicted − observed`}>
        <div className="grid gap-4 xl:grid-cols-2">
          <div className="h-56">
            <ResponsiveContainer>
              <LineChart data={residuals}>
                <CartesianGrid stroke="#1a3144" strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fill: "#94a3b8", fontSize: 10 }} minTickGap={28} />
                <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
                <ReferenceLine y={0} stroke="#64748b" />
                <Tooltip contentStyle={{ background: "#122230", border: "1px solid #27445c" }} />
                <Line dataKey="error" name="error" stroke="#fb7185" dot={false} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="h-56">
            <ResponsiveContainer>
              <BarChart data={histogram}>
                <CartesianGrid stroke="#1a3144" strokeDasharray="3 3" />
                <XAxis dataKey="bin" tick={{ fill: "#94a3b8", fontSize: 10 }} />
                <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
                <Bar dataKey="count" fill="#fb7185" isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </Card>
      <Card title="Generalization and interpretation">
        <ul className="list-disc space-y-1 pl-5 text-sm text-slate-300">
          {interpretation.map((line) => <li key={line}>{line}</li>)}
          <li>
            Validation/test differences are observed associations on one year each. They are not proof of a single cause such as overfitting.
          </li>
        </ul>
      </Card>
    </div>
  );
}

function pivotPredictions(records: Record<string, unknown>[]) {
  const byDate = new Map<string, Record<string, number | string>>();
  for (const row of records) {
    const date = text(row.issue_date_utc);
    const model = text(row.model_id);
    if (!date || !model) continue;
    const current = byDate.get(date) ?? { date };
    const observed = num(row.observed_modeled_target);
    const predicted = num(row.prediction);
    if (observed !== null) current.observed = observed;
    if (predicted !== null) current[model] = predicted;
    byDate.set(date, current);
  }
  return [...byDate.values()].sort((a, b) => String(a.date).localeCompare(String(b.date)));
}

function binResiduals(values: number[]) {
  if (!values.length) return [];
  const min = Math.min(...values);
  const max = Math.max(...values);
  const bins = 12;
  const width = (max - min) / bins || 1;
  const counts = Array.from({ length: bins }, (_, index) => ({
    bin: (min + width * index).toFixed(3),
    count: 0,
  }));
  for (const value of values) {
    const index = Math.min(bins - 1, Math.max(0, Math.floor((value - min) / width)));
    counts[index].count += 1;
  }
  return counts;
}
