import { useMemo, useState } from "react";
import { Link, useOutletContext, useSearchParams } from "react-router-dom";
import { Card } from "@/components/common/Card";
import { Metric } from "@/components/common/Metric";
import { QueryState } from "@/components/common/QueryState";
import { SeriesChart } from "@/components/charts/SeriesChart";
import { useWeatherDaily, useWeatherDataset, useWeatherMonthly, useWeatherSummary } from "@/hooks/useWeather";
import { formatNumber, formatPercent, latestValidMonth } from "@/utils/format";

interface Outlet {
  weatherId?: string;
}

const YEARS = ["2023", "2024", "2025"] as const;

export function WeatherAnalyticsPage() {
  const { weatherId } = useOutletContext<Outlet>();
  const [params, setParams] = useSearchParams();
  const dataset = useWeatherDataset(weatherId);
  const monthly = useWeatherMonthly(weatherId);
  const snapshot = latestValidMonth(monthly.data ?? []);
  const requestedYear = params.get("year");
  const requestedMonth = params.get("month");
  const year = requestedYear && YEARS.includes(requestedYear as (typeof YEARS)[number])
    ? requestedYear
    : snapshot?.month.slice(0, 4) ?? "2025";
  const monthFilter = requestedMonth && requestedMonth.length === 7 ? requestedMonth : "";
  const [view, setView] = useState<"daily" | "monthly">("daily");
  const start = monthFilter ? `${monthFilter}-01` : `${year}-01-01`;
  const end = monthFilter ? `${monthFilter}-${lastDay(monthFilter)}` : `${year}-12-31`;
  const daily = useWeatherDaily(weatherId, start, end);
  const summary = useWeatherSummary(weatherId, start, end);
  const spatial = dataset.data?.spatial;
  const yearMonths = (monthly.data ?? []).filter((item) => item.month.startsWith(year));
  const usingFallback = !requestedYear && Boolean(snapshot);

  const charts = useMemo(() => {
    if (view === "monthly") {
      return yearMonths.map((item) => ({
        date: item.month,
        temperature: item.complete_days > 0 ? item.temperature_mean_c : null,
        precipitation: item.complete_days > 0 ? item.precipitation_total_mm : null,
        humidity: item.complete_days > 0 ? item.relative_humidity_mean_pct : null,
        wind: item.complete_days > 0 ? item.wind_speed_mean_ms : null,
        evaporation: item.complete_days > 0 ? item.evaporation_total_mm : null,
      }));
    }
    return (daily.data ?? []).map((item) => ({
      date: item.date_utc ?? "",
      temperature: item.temperature_mean_c,
      precipitation: item.precipitation_total_mm,
      humidity: item.relative_humidity_mean_pct,
      wind: item.wind_speed_mean_ms,
      evaporation: item.evaporation_total_mm,
    }));
  }, [daily.data, view, yearMonths]);

  return (
    <div className="space-y-4">
      <Card
        title="Time selection"
        actions={(
          <Link className="text-xs text-moss-300 hover:underline" to="/integration">
            Combined analytics
          </Link>
        )}
      >
        <div className="flex flex-wrap items-end gap-3">
          <label className="text-sm" htmlFor="weather-year">
            Year
            <select
              id="weather-year"
              className="mt-1 block rounded border border-ink-600 bg-ink-800 px-2 py-1"
              value={year}
              onChange={(event) => {
                params.set("year", event.target.value);
                params.delete("month");
                setParams(params);
              }}
            >
              {YEARS.map((item) => (
                <option key={item} value={item}>{item}</option>
              ))}
            </select>
          </label>
          <label className="text-sm" htmlFor="weather-month">
            Month
            <select
              id="weather-month"
              className="mt-1 block rounded border border-ink-600 bg-ink-800 px-2 py-1"
              value={monthFilter}
              onChange={(event) => {
                if (event.target.value) params.set("month", event.target.value);
                else params.delete("month");
                setParams(params);
              }}
            >
              <option value="">Full year</option>
              {yearMonths.map((item) => (
                <option key={item.month} value={item.month}>
                  {item.month} ({item.availability ?? "unknown"})
                </option>
              ))}
            </select>
          </label>
          <div className="flex gap-1" role="tablist" aria-label="Aggregation">
            {(["daily", "monthly"] as const).map((item) => (
              <button
                key={item}
                type="button"
                className={`rounded px-2 py-1 text-xs uppercase ${
                  view === item ? "bg-moss-600 text-ink-950" : "bg-ink-700"
                }`}
                onClick={() => setView(item)}
              >
                {item}
              </button>
            ))}
          </div>
        </div>
        {usingFallback ? (
          <p className="mt-2 text-xs text-sand-300">
            Defaulted to {year} because it contains the latest complete downloaded month ({snapshot?.month}).
          </p>
        ) : null}
      </Card>

      <Card title="Selected-range metrics">
        <QueryState
          isLoading={summary.isLoading}
          error={summary.error}
          onRetry={() => void summary.refetch()}
        >
          <p className="mb-3 text-xs text-slate-400">
            Partial-period aggregate for {start} to {end} UTC. Only complete daily observations are included in totals.
          </p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Metric label="Mean temperature" value={`${formatNumber(summary.data?.temperature_mean_c)} °C`} />
            <Metric label="Total precipitation" value={`${formatNumber(summary.data?.precipitation_total_mm)} mm`} />
            <Metric label="Mean RH" value={`${formatNumber(summary.data?.relative_humidity_mean_pct)} %`} />
            <Metric label="Mean wind" value={`${formatNumber(summary.data?.wind_speed_mean_ms)} m/s`} />
            <Metric label="Total evaporation" value={`${formatNumber(summary.data?.evaporation_total_mm)} mm`} />
            <Metric label="Complete days" value={formatNumber(summary.data?.complete_days, 0)} />
            <Metric
              label="Completeness"
              value={formatPercent(
                summary.data && summary.data.day_count
                  ? (100 * summary.data.complete_days) / summary.data.day_count
                  : null,
              )}
            />
            <Metric label="Calendar days in range" value={formatNumber(summary.data?.day_count, 0)} />
          </div>
        </QueryState>
      </Card>

      <QueryState
        isLoading={daily.isLoading || monthly.isLoading}
        error={daily.error ?? monthly.error}
        onRetry={() => {
          void daily.refetch();
          void monthly.refetch();
        }}
      >
        <div className="grid gap-4 xl:grid-cols-2">
          <Card title={`Temperature (${view})`}>
            <SeriesChart data={charts.map((item) => ({ date: item.date, value: item.temperature }))} unit="°C" />
          </Card>
          <Card title={`Precipitation (${view})`}>
            <SeriesChart
              kind="bar"
              color="#60a5fa"
              data={charts.map((item) => ({ date: item.date, value: item.precipitation }))}
              unit="mm"
            />
            <p className="mt-2 text-xs text-slate-500">Missing precipitation stays blank. It is not drawn as 0 mm.</p>
          </Card>
          <Card title={`Relative humidity (${view})`}>
            <SeriesChart
              color="#e4d2a8"
              data={charts.map((item) => ({ date: item.date, value: item.humidity }))}
              unit="%"
            />
          </Card>
          <Card title={`Wind speed (${view})`}>
            <SeriesChart
              color="#93c5fd"
              data={charts.map((item) => ({ date: item.date, value: item.wind }))}
              unit="m/s"
            />
          </Card>
          <Card title={`Evaporation (${view})`} className="xl:col-span-2">
            <SeriesChart
              color="#e08a5a"
              data={charts.map((item) => ({ date: item.date, value: item.evaporation }))}
              unit="mm"
            />
          </Card>
        </div>
      </QueryState>

      <Card title="ERA5-Land metadata">
        <dl className="grid gap-2 text-sm sm:grid-cols-2">
          <div><dt className="text-slate-400">Source</dt><dd>Copernicus ERA5-Land hourly reanalysis</dd></div>
          <div><dt className="text-slate-400">Study AOI</dt><dd>Plovdiv · {dataset.data?.bbox?.join(", ") ?? "—"}</dd></div>
          <div>
            <dt className="text-slate-400">Selected grid point</dt>
            <dd className="font-mono">
              {spatial?.source_longitude ?? "—"}°E, {spatial?.source_latitude ?? "—"}°N
            </dd>
          </div>
          <div><dt className="text-slate-400">Native resolution</dt><dd>{spatial?.native_resolution_deg ?? 0.1}°</dd></div>
          <div>
            <dt className="text-slate-400">Distance from AOI center</dt>
            <dd>{spatial?.distance_km != null ? `${formatNumber(Number(spatial.distance_km))} km` : "—"}</dd>
          </div>
          <div><dt className="text-slate-400">Aggregation</dt><dd>{dataset.data?.timezone ?? "UTC"} daily totals</dd></div>
        </dl>
        <p className="mt-3 text-xs text-slate-500">
          This weather cell does not represent every 10 m Sentinel-2 pixel. ERA5-Land and Sentinel-2 remain different spatial products.
        </p>
      </Card>
    </div>
  );
}

function lastDay(month: string): string {
  const [year, mon] = month.split("-").map(Number);
  return String(new Date(Date.UTC(year, mon, 0)).getUTCDate()).padStart(2, "0");
}
