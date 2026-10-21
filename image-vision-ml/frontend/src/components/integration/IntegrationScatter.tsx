import {
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card } from "@/components/common/Card";
import type { IntegrationFeatureDefinition, IntegrationObservation } from "@/types/integration";
import { formatNumber, formatUtcTimestamp } from "@/utils/format";
import {
  SCATTER_FEATURE_IDS,
  featureMeta,
  pairedObservations,
  type ScatterFeatureId,
} from "@/utils/integration";

interface Props {
  observations: IntegrationObservation[];
  featureId: ScatterFeatureId;
  onFeatureId: (id: ScatterFeatureId) => void;
  selectedId?: string;
  onSelect: (sceneId: string) => void;
  catalog?: IntegrationFeatureDefinition[];
}

export function IntegrationScatter({
  observations,
  featureId,
  onFeatureId,
  selectedId,
  onSelect,
  catalog,
}: Props) {
  const meta = featureMeta(catalog, featureId);
  const unit = meta?.unit ?? unitFor(featureId);
  const pairs = pairedObservations(observations, featureId);
  const points = pairs.map((item) => ({
    x: item.x,
    y: item.y,
    id: item.row.scene_id ?? "",
    date: item.row.observation_date_utc,
    selected: item.row.scene_id === selectedId,
    complete: Boolean(item.row.weather_feature_window_complete),
  }));

  return (
    <Card title="Exploratory NDVI–weather comparison">
      <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
        <label className="text-sm text-slate-300" htmlFor="scatter-feature">
          Weather feature
          <select
            id="scatter-feature"
            className="mt-1 block rounded border border-ink-600 bg-ink-800 px-2 py-1"
            value={featureId}
            onChange={(event) => onFeatureId(event.target.value as ScatterFeatureId)}
          >
            {SCATTER_FEATURE_IDS.map((id) => (
              <option key={id} value={id}>
                {featureMeta(catalog, id)?.name ?? labelFor(id)}
              </option>
            ))}
          </select>
        </label>
        <p className="text-xs text-slate-400" data-testid="scatter-pair-count">
          Plotted pairs: {points.length} of {observations.length} observations
        </p>
      </div>
      {points.length === 0 ? (
        <p className="text-sm text-slate-400">No paired numeric observations for this feature.</p>
      ) : (
        <div className="h-72 w-full min-w-0" data-testid="integration-scatter">
          <ResponsiveContainer minWidth={240} minHeight={220}>
            <ScatterChart margin={{ top: 8, right: 12, bottom: 12, left: 8 }}>
              <CartesianGrid stroke="#1a3144" strokeDasharray="3 3" />
              <XAxis
                dataKey="x"
                type="number"
                name={unit}
                tick={{ fill: "#94a3b8", fontSize: 11 }}
                label={{ value: `${meta?.name ?? labelFor(featureId)} (${unit})`, fill: "#94a3b8", fontSize: 11, position: "insideBottom", offset: -4 }}
              />
              <YAxis
                dataKey="y"
                type="number"
                name="NDVI"
                tick={{ fill: "#94a3b8", fontSize: 11 }}
                label={{ value: "Mean NDVI", angle: -90, fill: "#94a3b8", fontSize: 11, position: "insideLeft" }}
              />
              <Tooltip
                cursor={{ strokeDasharray: "3 3" }}
                contentStyle={{ background: "#122230", border: "1px solid #27445c" }}
                formatter={(value, name) => [
                  typeof value === "number" ? formatNumber(value, 3) : String(value),
                  name === "y" ? "NDVI" : unit,
                ]}
                labelFormatter={(_, payload) => {
                  const point = payload?.[0]?.payload as (typeof points)[number] | undefined;
                  if (!point) return "";
                  return `${formatUtcTimestamp(point.date)} · ${point.id} · ${point.complete ? "complete windows" : "incomplete windows"}`;
                }}
              />
              <Scatter
                data={points}
                onClick={(state) => {
                  const id = (state as { id?: string }).id;
                  if (id) onSelect(id);
                }}
              >
                {points.map((item) => (
                  <Cell
                    key={item.id}
                    fill={item.selected ? "#f4d35e" : item.complete ? "#7dce9a" : "#cbd5e1"}
                    stroke={item.selected ? "#fff7cc" : "#0b1c27"}
                    r={item.selected ? 7 : 5}
                  />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      )}
      <p className="mt-3 text-xs text-sand-200">
        Exploratory association only. The available observations are sparse, seasonally distributed,
        and not sufficient to establish causality or predict soil moisture.
      </p>
    </Card>
  );
}

function labelFor(id: string): string {
  return {
    precip_prev_7d_mm: "Prior 7-day rainfall",
    precip_prev_14d_mm: "Prior 14-day rainfall",
    precip_prev_30d_mm: "Prior 30-day rainfall",
    temp_mean_prev_7d_c: "Prior 7-day mean temperature",
    temp_mean_prev_30d_c: "Prior 30-day mean temperature",
    rh_mean_prev_7d_pct: "Prior 7-day humidity",
    wind_mean_prev_7d_ms: "Prior 7-day wind speed",
    evap_prev_7d_mm: "Prior 7-day evaporation",
  }[id] ?? id;
}

function unitFor(id: string): string {
  if (id.includes("temp")) return "°C";
  if (id.includes("rh_")) return "%";
  if (id.includes("wind")) return "m/s";
  return "mm";
}
