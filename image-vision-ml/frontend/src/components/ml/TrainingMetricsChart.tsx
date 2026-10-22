import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card } from "@/components/common/Card";
import type { TrainingEvent } from "@/types/ml";
import { availableMetricNames, metricHistoryPoints, missingCurveExplanation } from "@/utils/runTelemetry";

interface Props {
  events: TrainingEvent[];
  algorithm: string | null;
}

const COLORS = ["#7dce9a", "#60a5fa", "#c4a574", "#f87171"];

export function TrainingMetricsChart({ events, algorithm }: Props) {
  const names = availableMetricNames(events);
  const [metric, setMetric] = useState(names[0] ?? "training_mse");
  const [hidden, setHidden] = useState<Record<string, boolean>>({});
  const selected = names.includes(metric) ? metric : names[0];
  const points = useMemo(() => metricHistoryPoints(events, selected), [events, selected]);
  const seriesKeys = [...new Set(points.map((item) => `${item.metric_name}:${item.dataset_partition}`))];
  const chartData = useMemo(() => {
    return points.map((item) => {
      const row: Record<string, number | string | null> = {
        x: item.iteration ?? item.elapsed_ms,
        elapsed_ms: item.elapsed_ms,
        iteration: item.iteration,
        timestamp_utc: item.timestamp_utc,
        calculation_method: item.calculation_method,
      };
      row[`${item.metric_name}:${item.dataset_partition}`] = item.value;
      return row;
    });
  }, [points]);
  const explanation = missingCurveExplanation(algorithm, points);

  return (
    <Card title="Recorded metric history">
      <p className="mb-2 text-xs text-slate-400">
        Points are stored events only. No interpolation or smoothing. MAE is not plotted as training loss unless it was the recorded metric.
      </p>
      {names.length ? (
        <div className="mb-3 flex flex-wrap gap-2">
          <label className="text-xs text-slate-400">
            Metric
            <select
              aria-label="Displayed metric"
              className="ml-2 rounded border border-ink-600 bg-ink-800 px-2 py-1 text-sm text-slate-100"
              value={selected}
              onChange={(event) => setMetric(event.target.value)}
            >
              {names.map((name) => (
                <option key={name} value={name}>{name}</option>
              ))}
            </select>
          </label>
          {seriesKeys.map((key, index) => (
            <label key={key} className="text-xs text-slate-300">
              <input
                type="checkbox"
                className="mr-1"
                checked={!hidden[key]}
                onChange={() => setHidden((current) => ({ ...current, [key]: !current[key] }))}
              />
              {key}
              <span className="ml-1 inline-block h-2 w-2 rounded-full" style={{ background: COLORS[index % COLORS.length] }} />
            </label>
          ))}
        </div>
      ) : null}
      {explanation ? (
        <p className="text-sm text-sand-200" data-testid="missing-metric-history">{explanation}</p>
      ) : (
        <div className="h-72 w-full min-w-0" data-testid="training-metrics-chart">
          <ResponsiveContainer>
            <LineChart data={chartData}>
              <CartesianGrid stroke="#1a3144" strokeDasharray="3 3" />
              <XAxis dataKey="x" tick={{ fill: "#94a3b8", fontSize: 11 }} label={{ value: "iteration / stage", fill: "#94a3b8", fontSize: 11, position: "insideBottom", offset: -2 }} />
              <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: "#122230", border: "1px solid #27445c" }}
                formatter={(value, name) => [value, String(name)]}
                labelFormatter={(_, payload) => {
                  const row = payload?.[0]?.payload as { iteration?: number; elapsed_ms?: number; timestamp_utc?: string; calculation_method?: string };
                  return `iteration ${row?.iteration ?? "n/a"} · ${row?.elapsed_ms} ms · ${row?.calculation_method ?? ""}`;
                }}
              />
              <Legend />
              {seriesKeys.map((key, index) => (
                hidden[key] ? null : (
                  <Line
                    key={key}
                    type="linear"
                    dataKey={key}
                    stroke={COLORS[index % COLORS.length]}
                    dot
                    connectNulls={false}
                    isAnimationActive={false}
                  />
                )
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </Card>
  );
}
