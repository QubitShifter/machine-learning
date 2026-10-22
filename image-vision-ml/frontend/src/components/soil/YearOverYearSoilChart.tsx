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
import type { MonthlySoilRow } from "@/types/api";
import { formatNumber } from "@/utils/format";
import {
  COMPARISON_DEPTHS,
  MONTH_SHORT,
  SEASONS,
  buildYearOverYearRows,
  completeYearsFromMonthly,
  depthKind,
  depthLabel,
  interannualDelta,
  seasonalMean,
  formatYearOverYearTooltip,
  type ComparisonDepthKey,
  type YearMonthPoint,
  yearColor,
  yearsFromMonthly,
} from "@/utils/soilYearComparison";

interface Props {
  months: MonthlySoilRow[];
  spatial?: Record<string, unknown> | null;
  onExploreYear?: (year: string, monthIndex?: number) => void;
}

export function YearOverYearSoilChart({ months, spatial, onExploreYear }: Props) {
  const years = useMemo(() => yearsFromMonthly(months), [months]);
  const completeYears = useMemo(() => completeYearsFromMonthly(months), [months]);
  const [depth, setDepth] = useState<ComparisonDepthKey>("theta_root_zone_0_100_mean");
  const [enabledYears, setEnabledYears] = useState<string[] | null>(null);
  const selectedYears = enabledYears ?? (completeYears.length ? completeYears : years);
  const [monthIndex, setMonthIndex] = useState(1);
  const [yearA, setYearA] = useState<string>("");
  const [yearB, setYearB] = useState<string>("");
  const comparisonYears = selectedYears.length ? selectedYears : years;
  const resolvedA = yearA && comparisonYears.includes(yearA) ? yearA : comparisonYears[0] ?? "";
  const resolvedB = yearB && comparisonYears.includes(yearB)
    ? yearB
    : comparisonYears[comparisonYears.length - 1] ?? "";

  const rows = useMemo(
    () => buildYearOverYearRows(months, depth, selectedYears),
    [months, depth, selectedYears],
  );
  const chartData = rows.map((item) => {
    const values = Object.fromEntries(
      Object.entries(item.values).map(([year, value]) => [year, value === null ? undefined : value]),
    );
    return {
      monthLabel: MONTH_SHORT[item.monthIndex - 1],
      monthIndex: item.monthIndex,
      ...values,
      points: item.points,
      depth,
    };
  });
  const delta = resolvedA && resolvedB
    ? interannualDelta(months, depth, monthIndex, resolvedA, resolvedB)
    : null;
  const seasons = years.map((year) => ({
    year,
    values: SEASONS.map((season) => seasonalMean(months, depth, season.id, year)),
  }));

  return (
    <section className="space-y-3" data-testid="soil-yoy-section">
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm" htmlFor="soil-yoy-depth">
          Comparison soil depth
          <select
            id="soil-yoy-depth"
            aria-label="Comparison soil depth"
            className="mt-1 block rounded border border-ink-600 bg-ink-800 px-2 py-1"
            value={depth}
            onChange={(event) => setDepth(event.target.value as ComparisonDepthKey)}
          >
            {COMPARISON_DEPTHS.map((item) => (
              <option key={item.key} value={item.key}>{item.label}</option>
            ))}
          </select>
        </label>
        <fieldset className="text-sm">
          <legend className="text-slate-400">Years</legend>
          <div className="soil-year-toggle-row mt-1">
            {years.map((year) => (
              <div key={year} className="flex items-center gap-1.5">
                <label className="flex items-center gap-1 text-xs">
                  <input
                    type="checkbox"
                    aria-label={year}
                    checked={selectedYears.includes(year)}
                    onChange={() => {
                      const next = selectedYears.includes(year)
                        ? selectedYears.filter((item) => item !== year)
                        : [...selectedYears, year].sort();
                      setEnabledYears(next);
                    }}
                  />
                  <span style={{ color: yearColor(year, years) }}>{year}</span>
                  {completeYears.includes(year) ? null : (
                    <span className="text-slate-500">(incomplete)</span>
                  )}
                </label>
                {onExploreYear ? (
                  <button
                    type="button"
                    className="rounded border border-ink-600 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-moss-300 hover:border-moss-500"
                    aria-label={`Explore this year ${year}`}
                    onClick={() => onExploreYear(year)}
                  >
                    Explore this year
                  </button>
                ) : null}
              </div>
            ))}
          </div>
        </fieldset>
      </div>
      <p className="text-[11px] text-slate-500">
        {depthKind(depth) === "profile"
          ? "Weighted 0–100 cm profile: 0.07θ1 + 0.21θ2 + 0.72θ3. Layer 4 (100–289 cm) is excluded."
          : `Single ERA5-Land TESSEL layer (${depthLabel(depth)}), not the weighted 0–100 cm profile.`}
      </p>

      <div className="h-80 w-full min-w-0" data-testid="soil-yoy-chart">
        <ResponsiveContainer>
          <LineChart data={chartData} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
            <CartesianGrid stroke="#1a3144" strokeDasharray="3 3" />
            <XAxis dataKey="monthLabel" tick={{ fill: "#94a3b8", fontSize: 11 }} />
            <YAxis
              tick={{ fill: "#94a3b8", fontSize: 11 }}
              domain={["auto", "auto"]}
              label={{ value: "m³/m³", angle: -90, position: "insideLeft", fill: "#94a3b8", fontSize: 11 }}
            />
            <Tooltip content={<YearOverYearTooltip depth={depth} />} />
            <Legend />
            {selectedYears.map((year) => (
              <Line
                key={year}
                type="monotone"
                dataKey={year}
                name={year}
                stroke={yearColor(year, years)}
                strokeWidth={1.8}
                dot={{ r: 3, strokeWidth: 1 }}
                activeDot={{ r: 5 }}
                connectNulls={false}
                isAnimationActive={false}
                className={onExploreYear ? "cursor-pointer" : undefined}
                onClick={(point) => {
                  if (!onExploreYear) return;
                  onExploreYear(year, monthFromChartEvent(point));
                }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="soil-comparison-stats">
      <div className="rounded-lg border border-ink-700 bg-ink-950/40 p-3" data-testid="soil-yoy-delta">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Interannual month comparison</h3>
        <div className="mt-2 flex flex-wrap gap-3">
          <label className="text-xs">
            Month
            <select
              aria-label="Comparison month"
              className="ml-1 rounded border border-ink-600 bg-ink-800 px-2 py-1"
              value={monthIndex}
              onChange={(event) => setMonthIndex(Number(event.target.value))}
            >
              {rows.map((item) => (
                <option key={item.monthIndex} value={item.monthIndex}>{item.monthLabel}</option>
              ))}
            </select>
          </label>
          <label className="text-xs">
            Year A
            <select
              aria-label="Comparison year A"
              className="ml-1 rounded border border-ink-600 bg-ink-800 px-2 py-1"
              value={resolvedA}
              onChange={(event) => setYearA(event.target.value)}
            >
              {years.map((year) => <option key={year} value={year}>{year}</option>)}
            </select>
          </label>
          <label className="text-xs">
            Year B
            <select
              aria-label="Comparison year B"
              className="ml-1 rounded border border-ink-600 bg-ink-800 px-2 py-1"
              value={resolvedB}
              onChange={(event) => setYearB(event.target.value)}
            >
              {years.map((year) => <option key={year} value={year}>{year}</option>)}
            </select>
          </label>
        </div>
        {delta ? (
          <dl className="mt-2 grid gap-1 text-xs sm:grid-cols-2">
            <div>
              <dt className="text-slate-500">{rows[monthIndex - 1]?.monthLabel} {resolvedA}</dt>
              <dd className="font-mono">{formatTheta(delta.thetaA)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">{rows[monthIndex - 1]?.monthLabel} {resolvedB}</dt>
              <dd className="font-mono">{formatTheta(delta.thetaB)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Δθ = θ<sub>{resolvedB}</sub> − θ<sub>{resolvedA}</sub></dt>
              <dd className="font-mono" data-testid="soil-yoy-delta-value">{formatTheta(delta.delta)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Relative change</dt>
              <dd>
                {delta.relativePct == null
                  ? delta.relativeUndefinedReason
                  : `${delta.relativePct.toFixed(2)}%`}
              </dd>
            </div>
          </dl>
        ) : (
          <p className="mt-2 text-xs text-slate-500">Select two years to compare a calendar month.</p>
        )}
        <p className="mt-2 text-[11px] text-slate-500">
          A positive Δθ means year B is wetter in this cell, not that crop health is better.
        </p>
      </div>

      <div className="max-w-full overflow-x-auto rounded-lg border border-ink-700 bg-ink-950/40 p-3" data-testid="soil-yoy-seasons">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Seasonal means</h3>
        <p className="mt-1 text-[11px] text-slate-500">
          Winter DJF YYYY–YYYY+1 uses December of YYYY with January and February of YYYY+1.
          Spring, summer, and autumn stay inside one calendar year. Incomplete seasons are gaps, not averages of the remaining months.
        </p>
        <table className="mt-2 w-full min-w-[28rem] border-collapse text-xs">
          <thead>
            <tr className="text-left text-slate-500">
              <th className="py-1 pr-2 font-normal">Season</th>
              {years.map((year) => (
                <th key={year} className="py-1 pr-2 font-normal">{year}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {SEASONS.map((season, index) => (
              <tr key={season.id} className="border-t border-ink-700">
                <th scope="row" className="py-1 pr-2 text-left font-normal text-slate-400">
                  {season.winterSpansCalendarYears ? "Winter DJF (Dec Y–Feb Y+1)" : season.label}
                </th>
                {seasons.map((item) => (
                  <td key={item.year} className="py-1 pr-2 font-mono">
                    {formatTheta(item.values[index]?.value ?? null)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      </div>

      <p className="text-xs text-slate-400" data-testid="soil-yoy-provenance">
        ERA5-Land modeled volumetric soil water. Nearest-grid-cell estimate; not independently measured field soil moisture.
        Source grid {formatCoord(spatial?.source_latitude, "N")}, {formatCoord(spatial?.source_longitude, "E")}
        {spatial?.distance_km != null ? ` · approximately ${formatNumber(Number(spatial.distance_km), 2)} km from AOI center` : ""}.
        Three complete years are not a robust long-term climatology.
      </p>
    </section>
  );
}

function monthFromChartEvent(data: unknown): number | undefined {
  if (!data || typeof data !== "object") return undefined;
  const payload = "payload" in data
    ? (data as { payload?: { monthIndex?: unknown } }).payload
    : undefined;
  const monthIndex = payload?.monthIndex;
  return typeof monthIndex === "number" && monthIndex >= 1 && monthIndex <= 12
    ? monthIndex
    : undefined;
}

function formatTheta(value: number | null): string {
  return value == null ? "—" : `${value.toFixed(4)} m³/m³`;
}

function formatCoord(value: unknown, hemisphere: "N" | "E"): string {
  if (value == null || value === "") return "—";
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "—";
  return `${numeric.toFixed(1)}° ${hemisphere}`;
}

function YearOverYearTooltip({
  active,
  payload,
  label,
  depth,
}: {
  active?: boolean;
  payload?: Array<{ dataKey?: string; value?: number | null; color?: string; payload?: Record<string, unknown> }>;
  label?: string;
  depth: ComparisonDepthKey;
}) {
  if (!active || !payload?.length) return null;
  const points = (payload[0]?.payload?.points ?? {}) as Record<string, YearMonthPoint>;
  return (
    <div className="max-w-xs rounded border border-ink-600 bg-ink-900 px-3 py-2 text-xs text-slate-200" data-testid="soil-yoy-tooltip">
      <p className="font-semibold">{label}</p>
      <p className="text-slate-400">{depthLabel(depth)}</p>
      {payload.map((item) => {
        const year = String(item.dataKey ?? "");
        const point = points[year];
        return (
          <div key={year} className="mt-2 border-t border-ink-700 pt-1">
            {(point
              ? formatYearOverYearTooltip(point, depth)
              : [`Year ${year}`, `Monthly mean ${formatTheta(typeof item.value === "number" ? item.value : null)}`]
            ).map((line) => (
              <p key={line} style={line.startsWith("Year") ? { color: item.color } : undefined}>{line}</p>
            ))}
          </div>
        );
      })}
    </div>
  );
}
