import { Link, useOutletContext } from "react-router-dom";
import { Card } from "@/components/common/Card";
import { Metric } from "@/components/common/Metric";
import { QueryState } from "@/components/common/QueryState";
import { StatusBadge } from "@/components/common/StatusBadge";
import { CoverageMatrix } from "@/components/quality/CoverageMatrix";
import {
  useSatelliteDataset,
  useSatelliteQuality,
  useSatelliteScenes,
  useSatelliteTimeseries,
} from "@/hooks/useSatellite";
import { useWeatherMonthly, useWeatherQuality } from "@/hooks/useWeather";
import { sceneNdviUrl } from "@/services/api";
import { formatNumber, formatPercent, latestValidMonth } from "@/utils/format";

interface Outlet {
  satelliteId?: string;
  weatherId?: string;
}

export function OverviewPage() {
  const { satelliteId, weatherId } = useOutletContext<Outlet>();
  const dataset = useSatelliteDataset(satelliteId);
  const quality = useSatelliteQuality(satelliteId);
  const scenes = useSatelliteScenes(satelliteId);
  const series = useSatelliteTimeseries(satelliteId);
  const weatherQuality = useWeatherQuality(weatherId);
  const monthly = useWeatherMonthly(weatherId);
  const snapshot = latestValidMonth(monthly.data ?? []);
  const recent = [...(scenes.data ?? [])]
    .filter((item) => item.acquisition_date && (item.status === "processed" || item.overlay_ready))
    .sort((a, b) => String(b.acquisition_date).localeCompare(String(a.acquisition_date)))
    .slice(0, 4);
  const ndviByScene = new Map(
    (series.data ?? []).map((item) => [item.scene_id, item]),
  );
  const coverage = weatherQuality.data?.coverage;
  const daily = weatherQuality.data?.daily;

  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Metric label="Satellite dataset" value={satelliteId ?? "—"} />
        <Metric label="Weather dataset" value={weatherId ?? "—"} />
        <Metric
          label="Study AOI"
          value={dataset.data?.bbox ? dataset.data.bbox.join(", ") : "—"}
          hint="west, south, east, north"
        />
        <Metric
          label="Weather completeness"
          value={formatPercent(daily?.completeness_pct)}
          hint={`${daily?.complete_days ?? "—"} complete / ${daily?.missing_days ?? "—"} missing days`}
        />
      </div>

      <Card title="Dataset overview">
        <QueryState
          isLoading={dataset.isLoading || weatherQuality.isLoading}
          error={dataset.error ?? weatherQuality.error}
          onRetry={() => {
            void dataset.refetch();
            void weatherQuality.refetch();
          }}
        >
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Metric label="Satellite scenes" value={formatNumber(dataset.data?.scene_count, 0)} />
            <Metric
              label="Validated observations"
              value={formatNumber(quality.data?.dataset.validated_scenes, 0)}
            />
            <Metric
              label="Downloaded weather months"
              value={formatNumber(coverage?.downloaded_months?.length, 0)}
            />
            <Metric
              label="Pending weather months"
              value={formatNumber(coverage?.missing_months?.length, 0)}
            />
          </div>
        </QueryState>
      </Card>

      <Card title="Weather coverage 2023–2025">
        <QueryState
          isLoading={weatherQuality.isLoading}
          error={weatherQuality.error}
          onRetry={() => void weatherQuality.refetch()}
          empty={!coverage?.month_availability}
          emptyMessage="Weather coverage is not available yet."
        >
          <CoverageMatrix availability={coverage?.month_availability} />
        </QueryState>
      </Card>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card
          title="Recent satellite scenes"
          actions={(
            <div className="flex gap-3">
              <Link to="/satellite?catalog=1" className="text-xs text-slate-400">Catalog</Link>
              <Link to="/satellite" className="text-xs text-moss-400">Open explorer</Link>
            </div>
          )}
        >
          <QueryState
            isLoading={scenes.isLoading}
            error={scenes.error}
            onRetry={() => void scenes.refetch()}
            empty={recent.length === 0}
            emptyMessage="No validated processed scenes are available yet."
          >
            <ul className="grid gap-3 sm:grid-cols-2">
              {recent.map((scene) => {
                const ndvi = ndviByScene.get(scene.scene_id);
                return (
                  <li key={scene.scene_id} className="rounded-lg border border-ink-600 bg-ink-800/60 p-2">
                    {satelliteId && ndvi?.mean != null ? (
                      <img
                        src={sceneNdviUrl(satelliteId, scene.scene_id)}
                        alt={`NDVI preview ${scene.scene_id}`}
                        className="mb-2 h-28 w-full rounded object-cover"
                        onError={(event) => {
                          event.currentTarget.style.display = "none";
                        }}
                      />
                    ) : null}
                    <Link
                      to={`/satellite?scene=${encodeURIComponent(scene.scene_id)}`}
                      className="block font-mono text-xs text-moss-300"
                    >
                      {scene.acquisition_date ?? "unknown date"}
                    </Link>
                    <p className="text-[11px] text-slate-500">{scene.platform ?? scene.scene_id}</p>
                    <p className="text-xs text-slate-400">
                      NDVI {formatNumber(ndvi?.mean)} · {scene.status}
                    </p>
                    <StatusBadge value={scene.status} />
                  </li>
                );
              })}
            </ul>
          </QueryState>
        </Card>

        <Card title="Latest complete weather month">
          <QueryState
            isLoading={monthly.isLoading}
            error={monthly.error}
            onRetry={() => void monthly.refetch()}
            empty={!snapshot}
            emptyMessage="No fully valid weather month is available yet."
          >
            {snapshot ? (
              <div className="space-y-3">
                <p className="text-sm text-slate-300">
                  ERA5-Land reanalysis for <span className="font-mono">{snapshot.month}</span>, not live weather.
                </p>
                <div className="grid grid-cols-2 gap-2">
                  <Metric label="Mean temperature" value={`${formatNumber(snapshot.temperature_mean_c)} °C`} />
                  <Metric label="Precipitation" value={`${formatNumber(snapshot.precipitation_total_mm)} mm`} />
                  <Metric label="Relative humidity" value={`${formatNumber(snapshot.relative_humidity_mean_pct)} %`} />
                  <Metric label="Wind speed" value={`${formatNumber(snapshot.wind_speed_mean_ms)} m/s`} />
                  <Metric label="Evaporation" value={`${formatNumber(snapshot.evaporation_total_mm)} mm`} />
                  <Metric label="Complete days" value={formatNumber(snapshot.complete_days, 0)} />
                </div>
              </div>
            ) : null}
          </QueryState>
        </Card>
      </div>

      <Card title="Dataset limitations">
        <ul className="list-disc space-y-1 pl-5 text-sm text-slate-300">
          <li>ERA5-Land is coarse 0.1° meteorological reanalysis, not a 10 m raster.</li>
          <li>Sentinel-2 imagery is much finer spatially than the selected weather grid cell.</li>
          <li>The historical weather archive is still being populated; missing months stay missing.</li>
          <li>Soil-moisture predictions are not implemented and are not shown.</li>
        </ul>
      </Card>
    </div>
  );
}
