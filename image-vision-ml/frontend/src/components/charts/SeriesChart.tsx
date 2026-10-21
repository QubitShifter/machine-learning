import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export interface SeriesPoint {
  date: string;
  value: number | null;
  extra?: string;
  id?: string;
  selected?: boolean;
}

interface Props {
  data: SeriesPoint[];
  unit: string;
  kind?: "line" | "bar" | "scatter";
  color?: string;
  connectNulls?: boolean;
  onPointClick?: (id: string) => void;
}

export function SeriesChart({
  data,
  unit,
  kind = "line",
  color = "#7dce9a",
  connectNulls = false,
  onPointClick,
}: Props) {
  const chartData = data.map((item) => ({
    ...item,
    value: item.value === null ? undefined : item.value,
  }));

  const tooltip = (
    <Tooltip
      contentStyle={{ background: "#122230", border: "1px solid #27445c" }}
      formatter={(value) => [
        value === undefined || value === null ? "missing" : `${value} ${unit}`,
        unit,
      ]}
      labelFormatter={(label, payload) => {
        const extra = payload?.[0]?.payload?.extra;
        const date = payload?.[0]?.payload?.date ?? label;
        return extra ? `${date} · ${extra}` : String(date);
      }}
    />
  );

  if (kind === "bar") {
    return (
      <div className="h-64 w-full min-w-0">
        <ResponsiveContainer>
          <BarChart data={chartData}>
            <CartesianGrid stroke="#1a3144" strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fill: "#94a3b8", fontSize: 11 }} minTickGap={24} />
            <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
            {tooltip}
            <Bar dataKey="value" fill={color} maxBarSize={12} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  }

  if (kind === "scatter") {
    const points = data
      .filter((item) => item.value !== null && item.date)
      .map((item) => ({
        t: Date.parse(`${item.date}T00:00:00Z`),
        date: item.date,
        value: item.value as number,
        extra: item.extra,
        id: item.id ?? item.extra ?? item.date,
        selected: Boolean(item.selected),
      }))
      .filter((item) => Number.isFinite(item.t));
    return (
      <div className="h-64 w-full min-w-0">
        <ResponsiveContainer>
          <ScatterChart>
            <CartesianGrid stroke="#1a3144" strokeDasharray="3 3" />
            <XAxis
              dataKey="t"
              type="number"
              domain={["dataMin", "dataMax"]}
              tick={{ fill: "#94a3b8", fontSize: 11 }}
              tickFormatter={(value) => new Date(value).toISOString().slice(0, 10)}
            />
            <YAxis dataKey="value" tick={{ fill: "#94a3b8", fontSize: 11 }} />
            {tooltip}
            <Scatter
              data={points}
              onClick={(state) => {
                const id = (state as { id?: string }).id;
                if (id) onPointClick?.(id);
              }}
            >
              {points.map((item) => (
                <Cell
                  key={item.id}
                  fill={item.selected ? "#f4d35e" : color}
                  stroke={item.selected ? "#fff7cc" : color}
                  r={item.selected ? 6 : 4}
                />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    );
  }

  return (
    <div className="h-64 w-full min-w-0">
      <ResponsiveContainer>
        <LineChart data={chartData}>
          <CartesianGrid stroke="#1a3144" strokeDasharray="3 3" />
          <XAxis dataKey="date" tick={{ fill: "#94a3b8", fontSize: 11 }} minTickGap={24} />
          <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
          {tooltip}
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            dot={false}
            connectNulls={connectNulls}
            strokeWidth={1.6}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
