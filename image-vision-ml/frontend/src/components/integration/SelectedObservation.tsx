import { Link } from "react-router-dom";
import { Card } from "@/components/common/Card";
import { StatusBadge } from "@/components/common/StatusBadge";
import type { IntegrationObservation } from "@/types/integration";
import { formatNumber, formatPercent, formatUtcTimestamp } from "@/utils/format";
import { platformFromSceneId } from "@/utils/integration";

interface Props {
  row: IntegrationObservation;
}

function Flag({ ok, label }: { ok: boolean | null | undefined; label: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] ${
        ok ? "border-moss-600/40 text-moss-400" : "border-sand-400/40 text-sand-300"
      }`}
    >
      {label}: {ok ? "yes" : "no"}
    </span>
  );
}

export function SelectedObservation({ row }: Props) {
  const explorer = row.scene_id
    ? `/satellite?scene=${encodeURIComponent(row.scene_id)}`
    : "/satellite";

  return (
    <Card
      title="Selected observation"
      actions={(
        <Link
          className="rounded border border-moss-600/40 px-2 py-1 text-xs text-moss-300 hover:bg-ink-700"
          to={explorer}
        >
          Open in Satellite Explorer
        </Link>
      )}
    >
      <dl className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4 text-sm">
        <Item label="Acquisition UTC" value={formatUtcTimestamp(row.acquisition_timestamp_utc ?? row.observation_date_utc)} />
        <Item label="Platform" value={platformFromSceneId(row.scene_id) ?? "—"} />
        <Item label="Scene ID" value={row.scene_id ?? "—"} mono />
        <Item label="Mean NDVI" value={formatNumber(row.ndvi_mean, 3)} />
        <Item label="NDVI min / max" value={`${formatNumber(row.ndvi_minimum, 3)} / ${formatNumber(row.ndvi_maximum, 3)}`} />
        <Item label="NDVI median" value={formatNumber(row.ndvi_median, 3)} />
        <Item label="Valid pixels" value={formatPercent(row.valid_ndvi_pct)} />
        <Item label="Cloud / shadow" value={formatPercent(row.cloud_shadow_fraction_pct)} />
      </dl>
      <div className="mt-3 flex flex-wrap gap-2">
        <StatusBadge value={row.satellite_quality_status ?? row.quality_status} />
        <Flag ok={row.satellite_observation_valid} label="Satellite valid" />
        <Flag ok={row.weather_observation_valid} label="Weather grid valid" />
        <Flag ok={row.weather_feature_window_complete} label="Weather windows complete" />
        <Flag ok={row.integrated_observation_complete} label="Integrated complete" />
        <Flag ok={row.suitable_for_modeling} label="Suitable for modeling" />
      </div>
      <p className="mt-1 text-xs text-slate-500">
        Suitable for modeling means this observation may enter supervised soil forecasting.
        Complete weather windows are not enough while soil-moisture labels are missing.
      </p>
      <p className="mt-2 text-xs text-slate-500">
        Weather grid {formatNumber(row.weather_grid_latitude, 2)}°N, {formatNumber(row.weather_grid_longitude, 2)}°E
        {" · "}
        {formatNumber(row.weather_grid_distance_km, 2)} km from AOI centroid
        {" · "}
        {row.weather_grid_method ?? "nearest cell"}
        {" · "}
        ERA5-Land ~0.1°, not 10 m.
      </p>
    </Card>
  );
}

function Item({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <dt className="text-[11px] uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className={`text-slate-200 ${mono ? "font-mono text-xs break-all" : ""}`}>{value}</dd>
    </div>
  );
}
