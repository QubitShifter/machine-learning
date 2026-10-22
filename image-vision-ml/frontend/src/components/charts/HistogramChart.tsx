import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { HistogramBin } from "@/types/api";
import { binsOverlappingDomain } from "@/utils/histogramZoom";

export interface HistogramSeriesView {
  key: string;
  label: string;
  color: string;
  visible: boolean;
  bins: HistogramBin[];
}

interface Props {
  series: HistogramSeriesView[];
  xLabel: string;
  yMode: "count" | "percent";
  domain?: [number, number];
}

export function HistogramChart({ series, xLabel, yMode, domain }: Props) {
  const data = useMemo(() => {
    const byCenter = new Map<number, Record<string, number | string>>();
    for (const item of series) {
      if (!item.visible) continue;
      const bins = domain ? binsOverlappingDomain(item.bins, domain) : item.bins;
      for (const bin of bins) {
        const row = byCenter.get(bin.center) ?? {
          center: bin.center,
          edge_left: bin.edge_left,
          edge_right: bin.edge_right,
        };
        row[item.key] = yMode === "percent"
          ? bin.percent_of_valid ?? 0
          : bin.count;
        byCenter.set(bin.center, row);
      }
    }
    return [...byCenter.values()].sort((a, b) => Number(a.center) - Number(b.center));
  }, [series, yMode, domain]);

  return (
    <div className="h-64 w-full min-w-0" data-testid="histogram-chart">
      <ResponsiveContainer>
        <BarChart data={data} barGap={0} barCategoryGap={0}>
          <CartesianGrid stroke="#1a3144" strokeDasharray="3 3" />
          <XAxis
            dataKey="center"
            type="number"
            domain={domain ?? ["dataMin", "dataMax"]}
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            label={{ value: xLabel, position: "insideBottom", offset: -2, fill: "#94a3b8", fontSize: 11 }}
          />
          <YAxis
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            label={{
              value: yMode === "percent" ? "% of valid pixels" : "pixel count",
              angle: -90,
              position: "insideLeft",
              fill: "#94a3b8",
              fontSize: 11,
            }}
          />
          <Tooltip
            contentStyle={{ background: "#122230", border: "1px solid #27445c" }}
            formatter={(value, name) => [
              value === undefined || value === null ? "missing" : String(value),
              String(name),
            ]}
            labelFormatter={(_, payload) => {
              const row = payload?.[0]?.payload;
              if (!row) return "";
              return `${Number(row.edge_left).toFixed(3)} to ${Number(row.edge_right).toFixed(3)}`;
            }}
          />
          {series.length > 1 ? <Legend /> : null}
          {series.filter((item) => item.visible).map((item) => (
            <Bar
              key={item.key}
              dataKey={item.key}
              name={item.label}
              fill={item.color}
              fillOpacity={series.length > 1 ? 0.45 : 0.85}
              maxBarSize={18}
              isAnimationActive={false}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
