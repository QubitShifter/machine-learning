import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export interface DualAxisPoint {
  date: string;
  bar?: number | null;
  line?: number | null;
  extra?: string;
}

interface Props {
  data: DualAxisPoint[];
  barLabel: string;
  barUnit: string;
  lineLabel: string;
  lineUnit: string;
  barColor?: string;
  lineColor?: string;
}

export function DualAxisChart({
  data,
  barLabel,
  barUnit,
  lineLabel,
  lineUnit,
  barColor = "#60a5fa",
  lineColor = "#c4a574",
}: Props) {
  const chartData = data.map((item) => ({
    ...item,
    bar: item.bar === null ? undefined : item.bar,
    line: item.line === null ? undefined : item.line,
  }));
  return (
    <div className="h-72 w-full min-w-0" data-testid="dual-axis-chart">
      <ResponsiveContainer>
        <ComposedChart data={chartData}>
          <CartesianGrid stroke="#1a3144" strokeDasharray="3 3" />
          <XAxis dataKey="date" tick={{ fill: "#94a3b8", fontSize: 11 }} minTickGap={24} />
          <YAxis
            yAxisId="bar"
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            label={{ value: barUnit, angle: -90, position: "insideLeft", fill: "#94a3b8", fontSize: 11 }}
          />
          <YAxis
            yAxisId="line"
            orientation="right"
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            label={{ value: lineUnit, angle: 90, position: "insideRight", fill: "#94a3b8", fontSize: 11 }}
          />
          <Tooltip
            contentStyle={{ background: "#122230", border: "1px solid #27445c" }}
            formatter={(value, name) => {
              if (value === undefined || value === null) return ["missing", String(name)];
              const unit = String(name) === barLabel ? barUnit : lineUnit;
              return [`${value} ${unit}`, String(name)];
            }}
            labelFormatter={(label, payload) => {
              const extra = payload?.[0]?.payload?.extra;
              return extra ? `${label} · ${extra}` : String(label);
            }}
          />
          <Legend />
          <Bar yAxisId="bar" dataKey="bar" name={barLabel} fill={barColor} maxBarSize={10} isAnimationActive={false} />
          <Line
            yAxisId="line"
            dataKey="line"
            name={lineLabel}
            stroke={lineColor}
            dot={false}
            connectNulls={false}
            strokeWidth={1.6}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
