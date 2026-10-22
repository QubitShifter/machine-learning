import { useMemo, useState } from "react";
import { Link, useOutletContext, useSearchParams } from "react-router-dom";
import { Card } from "@/components/common/Card";
import { Metric } from "@/components/common/Metric";
import { QueryState } from "@/components/common/QueryState";
import { ProvenanceFooter } from "@/components/analysis/ProvenanceFooter";
import { PlannedModules } from "@/components/analysis/PlannedModules";
import { DualAxisChart } from "@/components/charts/DualAxisChart";
import { SeriesChart } from "@/components/charts/SeriesChart";
import { YearOverYearSoilChart } from "@/components/soil/YearOverYearSoilChart";
import {
  useCombinedSoilWeather,
  useSoilDaily,
  useSoilDataset,
  useSoilMonthly,
  useSoilQuality,
} from "@/hooks/useSoil";
import type { DailySoilRow, MonthlySoilRow } from "@/types/api";
import { formatNumber, lastUtcDayOfMonth } from "@/utils/format";
import { yearsFromMonthly } from "@/utils/soilYearComparison";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface Outlet {
  soilId?: string;
  weatherId?: string;
}

const FALLBACK_YEARS = ["2023", "2024", "2025"] as const;

const LAYERS = [
  { key: "swvl1_mean", monthly: "swvl1_mean", label: "0–7 cm", color: "#e4c9a0" },
  { key: "swvl2_mean", monthly: "swvl2_mean", label: "7–28 cm", color: "#c4a574" },
  { key: "swvl3_mean", monthly: "swvl3_mean", label: "28–100 cm", color: "#8b6f47" },
  { key: "swvl4_mean", monthly: "swvl4_mean", label: "100–289 cm", color: "#5c4033" },
] as const;

type LayerKey = typeof LAYERS[number]["key"] | "theta_root_zone_0_100";

export function SoilAnalysisPage() {
  const { soilId, weatherId } = useOutletContext<Outlet>();
  const [params, setParams] = useSearchParams();
  const dataset = useSoilDataset(soilId);
  const quality = useSoilQuality(soilId);
  const monthly = useSoilMonthly(soilId);
  const snapshot = [...(monthly.data ?? [])].reverse().find((item) => item.complete_days > 0);
  const requestedYear = params.get("year");
  const requestedMonth = params.get("month");
  const availableYears = yearsFromMonthly(monthly.data ?? []);
  const yearChoices = availableYears.length ? availableYears : [...FALLBACK_YEARS];
  const detailYear = requestedYear && yearChoices.includes(requestedYear)
    ? requestedYear
    : snapshot?.month.slice(0, 4) ?? yearChoices[0] ?? "2023";
  const detailMonth = requestedMonth && requestedMonth.length === 7 ? requestedMonth : "";
  const [detailAggregation, setDetailAggregation] = useState<"daily" | "monthly">("daily");
  const [detailSoilLayer, setDetailSoilLayer] = useState<LayerKey>("swvl1_mean");
  const start = detailMonth ? `${detailMonth}-01` : `${detailYear}-01-01`;
  const end = detailMonth ? `${detailMonth}-${lastUtcDayOfMonth(detailMonth)}` : `${detailYear}-12-31`;
  const daily = useSoilDaily(soilId, start, end);
  const combined = useCombinedSoilWeather(soilId, weatherId, start, end);
  const spatial = dataset.data?.spatial ?? quality.data?.spatial;
  const yearMonths = (monthly.data ?? []).filter((item) => item.month.startsWith(detailYear));
  const selectedDay = (daily.data ?? []).filter((item) => item.complete_day).at(-1)
    ?? (daily.data ?? []).at(-1);
  const depthSource = detailAggregation === "monthly"
    ? yearMonths.find((item) => item.month === (detailMonth || snapshot?.month)) ?? yearMonths.at(-1)
    : selectedDay;
  const depthRows = depthValues(depthSource, detailAggregation);
  const usingFallback = !requestedYear && Boolean(snapshot);

  const series = useMemo(() => {
    if (detailAggregation === "monthly") {
      return yearMonths.map((item) => ({
        date: item.month,
        value: layerValueMonthly(item, detailSoilLayer),
        extra: `${item.complete_days} complete days · monthly mean`,
      }));
    }
    return (daily.data ?? []).map((item) => ({
      date: item.date_utc ?? "",
      value: layerValueDaily(item, detailSoilLayer),
      extra: item.complete_day ? "complete modeled day" : "incomplete or missing",
    }));
  }, [daily.data, detailAggregation, detailSoilLayer, yearMonths]);

  const exploreYear = (nextYear: string, monthIndex?: number) => {
    const next = new URLSearchParams(params);
    next.set("year", nextYear);
    if (monthIndex && monthIndex >= 1 && monthIndex <= 12) {
      next.set("month", `${nextYear}-${String(monthIndex).padStart(2, "0")}`);
    } else {
      next.delete("month");
    }
    setParams(next);
    requestAnimationFrame(() => {
      document.getElementById("detailed-soil-analysis")?.scrollIntoView?.({
        behavior: "smooth",
        block: "start",
      });
    });
  };

  return (
    <div className="space-y-6">
      <section data-testid="soil-historical-workspace" className="space-y-3">
        <header>
          <h2 className="text-base font-semibold tracking-wide text-slate-100">Historical Comparison</h2>
          <p className="mt-1 text-xs text-slate-400">
            Compare seasonal soil-water behavior across available years.
          </p>
        </header>
        <Card title="Historical Soil Moisture — Year-over-Year Comparison">
          <QueryState
            isLoading={monthly.isLoading}
            error={monthly.error}
            onRetry={() => void monthly.refetch()}
            empty={!monthly.data?.length}
            emptyMessage="No monthly soil-water summary is available for year-over-year comparison."
          >
            <YearOverYearSoilChart
              months={monthly.data ?? []}
              spatial={spatial}
              onExploreYear={exploreYear}
            />
          </QueryState>
        </Card>
      </section>

      <section
        id="detailed-soil-analysis"
        data-testid="soil-detailed-workspace"
        className="scroll-mt-20 space-y-3"
      >
        <header className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold tracking-wide text-slate-100">Detailed Soil Analysis</h2>
            <p className="mt-1 text-xs text-slate-400">
              Inspect soil moisture at individual depths over a selected period.
            </p>
          </div>
          <Link className="text-xs text-moss-300 hover:underline" to="/weather">
            Weather and wetness
          </Link>
        </header>

        <Card>
          <div className="soil-control-bar" data-testid="soil-detail-controls">
            <label className="text-sm" htmlFor="soil-year">
              Year
              <select
                id="soil-year"
                aria-label="Detailed year"
                className="mt-1 block rounded border border-ink-600 bg-ink-800 px-2 py-1"
                value={detailYear}
                onChange={(event) => {
                  const next = new URLSearchParams(params);
                  next.set("year", event.target.value);
                  next.delete("month");
                  setParams(next);
                }}
              >
                {yearChoices.map((item) => <option key={item} value={item}>{item}</option>)}
              </select>
            </label>
            <label className="text-sm" htmlFor="soil-month">
              Month
              <select
                id="soil-month"
                aria-label="Detailed month"
                className="mt-1 block rounded border border-ink-600 bg-ink-800 px-2 py-1"
                value={detailMonth}
                onChange={(event) => {
                  const next = new URLSearchParams(params);
                  if (event.target.value) next.set("month", event.target.value);
                  else next.delete("month");
                  setParams(next);
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
            <div className="flex gap-1" role="tablist" aria-label="Soil aggregation">
              {(["daily", "monthly"] as const).map((item) => (
                <button
                  key={item}
                  type="button"
                  role="tab"
                  aria-selected={detailAggregation === item}
                  className={`rounded px-2 py-1 text-xs uppercase ${
                    detailAggregation === item ? "bg-moss-600 text-ink-950" : "bg-ink-700"
                  }`}
                  onClick={() => setDetailAggregation(item)}
                >
                  {item}
                </button>
              ))}
            </div>
            <label className="text-sm" htmlFor="soil-detail-layer">
              Layer
              <select
                id="soil-detail-layer"
                className="mt-1 block rounded border border-ink-600 bg-ink-800 px-2 py-1"
                value={detailSoilLayer}
                onChange={(event) => setDetailSoilLayer(event.target.value as LayerKey)}
                aria-label="Soil layer"
              >
                {LAYERS.map((item) => (
                  <option key={item.key} value={item.key}>{item.label}</option>
                ))}
                <option value="theta_root_zone_0_100">0–100 cm weighted</option>
              </select>
            </label>
          </div>
          {usingFallback ? (
            <p className="mt-2 text-xs text-sand-300">
              Defaulted to {detailYear} because it contains processed complete soil days ({snapshot?.month}).
            </p>
          ) : null}
        </Card>

        <div className="grid min-w-0 gap-4 xl:grid-cols-2">
        <Card title={detailAggregation === "monthly" ? "Monthly depth profile (mean of complete days)" : "Daily depth profile"}>
          <QueryState
            isLoading={daily.isLoading || monthly.isLoading}
            error={daily.error ?? monthly.error}
            onRetry={() => {
              void daily.refetch();
              void monthly.refetch();
            }}
            empty={!depthRows.some((item) => item.value != null)}
            emptyMessage="No complete modeled soil-water profile is available for this range."
          >
            <div className="h-72 w-full min-w-0" data-testid="soil-depth-chart">
              <ResponsiveContainer>
                <BarChart data={depthRows} layout="vertical" margin={{ left: 80 }}>
                  <CartesianGrid stroke="#1a3144" strokeDasharray="3 3" />
                  <XAxis type="number" domain={[0, 1]} tick={{ fill: "#94a3b8", fontSize: 11 }} />
                  <YAxis type="category" dataKey="label" tick={{ fill: "#94a3b8", fontSize: 11 }} width={90} />
                  <Tooltip
                    contentStyle={{ background: "#122230", border: "1px solid #27445c" }}
                    formatter={(value) => [
                      value == null ? "missing" : `${value} m³/m³`,
                      "volumetric water",
                    ]}
                  />
                  <Bar dataKey="value" fill="#c4a574" maxBarSize={18} isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <Metric
              label="0–100 cm weighted mean"
              value={`${formatNumber(rootZone(depthSource, detailAggregation), 3)} m³/m³`}
              hint="0.07θ1 + 0.21θ2 + 0.72θ3; layer 4 excluded"
            />
            <ProvenanceFooter
              items={[
                { label: "Source", value: "ERA5-Land volumetric soil water (modeled/reanalysis)" },
                { label: "Dataset", value: soilId },
                { label: "Stamp", value: detailAggregation === "monthly" ? (depthSource as MonthlySoilRow | undefined)?.month : selectedDay?.date_utc },
                { label: "Units", value: "m³/m³" },
                { label: "Grid", value: gridLabel(spatial) },
                { label: "Kind", value: "modeled_volumetric_soil_moisture" },
                { label: "Quality", value: quality.data?.status },
              ]}
              note="This coarse ERA5-Land cell is not 10 m Sentinel-2 precision."
            />
          </QueryState>
        </Card>

        <Card title="Soil-water time series">
          <QueryState
            isLoading={daily.isLoading || monthly.isLoading}
            error={daily.error ?? monthly.error}
            empty={!series.length}
            emptyMessage="No soil-water observations in this range."
          >
            <SeriesChart data={series} unit="m³/m³" color="#c4a574" connectNulls={false} />
          <p className="mt-2 text-xs text-slate-500">
            Gaps stay gaps. Hover shows UTC date, layer, and modeled-data provenance. Long missing intervals are not bridged.
          </p>
        </QueryState>
        </Card>
        </div>

      <Card title="Rainfall versus modeled soil water">
        <QueryState
          isLoading={combined.isLoading}
          error={combined.error}
          onRetry={() => void combined.refetch()}
          empty={!combined.data?.records.length}
          emptyMessage="Aligned rainfall and soil-water records are not available for this range."
        >
          <DualAxisChart
            data={(combined.data?.records ?? []).map((item) => ({
              date: item.date_utc ?? "",
              bar: item.is_forecast ? null : item.precipitation_total_mm,
              line: layerValueCombined(item, detailSoilLayer),
              extra: [
                item.soil_present ? "modeled θ" : "soil missing",
                item.weather_present ? "ERA5 precip" : "weather missing",
                item.source_grid_id,
              ].filter(Boolean).join(" · "),
            }))}
            barLabel="Precipitation"
            barUnit="mm"
            lineLabel={layerLabel(detailSoilLayer)}
            lineUnit="m³/m³"
          />
          <p className="mt-2 text-xs text-slate-500">
            Precipitation (mm) and volumetric moisture (m³/m³) use separate axes.
            Lagged rainfall–moisture correlation is prepared in the API (`{combined.data?.lagged_correlation_status}`)
            and is not interpreted from one month of overlapping observations.
          </p>
        </QueryState>
      </Card>

      <Card title="Antecedent precipitation (separate panel)">
        <QueryState
          isLoading={combined.isLoading}
          error={combined.error}
          empty={!combined.data?.records.length}
        >
          <SeriesChart
            unit="mm"
            color="#60a5fa"
            connectNulls={false}
            data={(combined.data?.records ?? []).map((item) => ({
              date: item.date_utc ?? "",
              value: item.is_forecast ? null : item.api_k090_mm,
              extra: "API k=0.90, weather-derived wetness proxy",
            }))}
          />
          <p className="mt-2 text-xs text-slate-500">
            API is a rainfall-history wetness proxy, not soil moisture. Future forecasts are excluded from historical analytics.
          </p>
        </QueryState>
      </Card>

      <Card>
        <dl className="grid gap-2 text-xs sm:grid-cols-2 lg:grid-cols-3">
          <div><dt className="text-slate-500">Source</dt><dd>ERA5-Land modeled reanalysis</dd></div>
          <div>
            <dt className="text-slate-500">Grid</dt>
            <dd className="font-mono">
              {String(spatial?.source_latitude ?? "—")}°N, {String(spatial?.source_longitude ?? "—")}°E
            </dd>
          </div>
          <div>
            <dt className="text-slate-500">Distance</dt>
            <dd>{spatial?.distance_km != null ? `${formatNumber(Number(spatial.distance_km), 2)} km from AOI center` : "—"}</dd>
          </div>
          <div><dt className="text-slate-500">Quality</dt><dd>{quality.data?.status ?? "unknown"}</dd></div>
          <div><dt className="text-slate-500">Ground truth</dt><dd>no</dd></div>
          <div><dt className="text-slate-500">Units</dt><dd>m³/m³ · monthly mean of complete days</dd></div>
        </dl>
      </Card>
      </section>

      <PlannedModules />
    </div>
  );
}

function depthValues(source: DailySoilRow | MonthlySoilRow | undefined, view: "daily" | "monthly") {
  return LAYERS.map((item) => ({
    label: item.label,
    value: view === "monthly"
      ? (source as MonthlySoilRow | undefined)?.[item.monthly] ?? null
      : (source as DailySoilRow | undefined)?.[item.key] ?? null,
  }));
}

function rootZone(source: DailySoilRow | MonthlySoilRow | undefined, view: "daily" | "monthly") {
  if (!source) return null;
  if (view === "monthly") return (source as MonthlySoilRow).theta_root_zone_0_100_mean;
  return (source as DailySoilRow).theta_root_zone_0_100;
}

function layerValueDaily(row: DailySoilRow, layer: LayerKey): number | null {
  return row[layer];
}

function layerValueMonthly(row: MonthlySoilRow, layer: LayerKey): number | null {
  if (layer === "theta_root_zone_0_100") return row.theta_root_zone_0_100_mean;
  return row[layer];
}

function layerValueCombined(
  row: { swvl1_mean: number | null; swvl2_mean: number | null; swvl3_mean: number | null; swvl4_mean: number | null; theta_root_zone_0_100: number | null },
  layer: LayerKey,
): number | null {
  return row[layer];
}

function layerLabel(layer: LayerKey): string {
  if (layer === "theta_root_zone_0_100") return "0–100 cm θ";
  return LAYERS.find((item) => item.key === layer)?.label ?? layer;
}

function gridLabel(spatial: Record<string, unknown> | null | undefined): string {
  if (!spatial) return "ERA5-Land ~0.1° cell";
  const distance = spatial.distance_km == null ? "—" : formatNumber(Number(spatial.distance_km), 2);
  return `${spatial.source_latitude ?? "—"}°N, ${spatial.source_longitude ?? "—"}°E · ${distance} km from AOI`;
}
