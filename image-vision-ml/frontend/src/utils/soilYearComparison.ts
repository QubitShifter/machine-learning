import type { MonthlySoilRow } from "@/types/api";

export const MONTH_LABELS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
] as const;

export const MONTH_SHORT = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
] as const;

export const COMPARISON_DEPTHS = [
  { key: "swvl1_mean", label: "Surface layer 0–7 cm", kind: "layer" as const },
  { key: "swvl2_mean", label: "Second layer 7–28 cm", kind: "layer" as const },
  { key: "swvl3_mean", label: "Third layer 28–100 cm", kind: "layer" as const },
  { key: "swvl4_mean", label: "Deep layer 100–289 cm", kind: "layer" as const },
  { key: "theta_root_zone_0_100_mean", label: "Weighted profile 0–100 cm", kind: "profile" as const },
] as const;

export type ComparisonDepthKey = typeof COMPARISON_DEPTHS[number]["key"];

export const YEAR_COLORS = ["#7dce9a", "#f4d35e", "#60a5fa", "#e08a5a", "#c4b5fd", "#67e8f9"];

export const RELATIVE_CHANGE_MIN_ABS = 1e-6;

export interface YearMonthPoint {
  year: string;
  monthIndex: number;
  monthLabel: string;
  value: number | null;
  completeDays: number;
  dayCount: number;
  availability: string | null;
  unit: string;
  min: number | null;
  max: number | null;
  aggregation: string;
  observationKind: string;
}

export interface YearOverYearRow {
  monthIndex: number;
  monthLabel: string;
  values: Record<string, number | null>;
  points: Record<string, YearMonthPoint>;
}

export function yearsFromMonthly(rows: MonthlySoilRow[]): string[] {
  const years = new Set<string>();
  for (const row of rows) {
    const year = yearOf(row.month);
    if (year) years.add(year);
  }
  return [...years].sort();
}

export function completeYearsFromMonthly(rows: MonthlySoilRow[]): string[] {
  return yearsFromMonthly(rows).filter((year) => {
    const months = rows.filter((item) => yearOf(item.month) === year);
    if (months.length !== 12) return false;
    return months.every((item) => item.availability === "complete" && item.complete_days > 0);
  });
}

export function depthLabel(key: ComparisonDepthKey): string {
  return COMPARISON_DEPTHS.find((item) => item.key === key)?.label ?? key;
}

export function depthKind(key: ComparisonDepthKey): "layer" | "profile" {
  return COMPARISON_DEPTHS.find((item) => item.key === key)?.kind ?? "layer";
}

export function monthValue(row: MonthlySoilRow, depth: ComparisonDepthKey): number | null {
  const value = row[depth];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function yearColor(year: string, years: string[]): string {
  const index = Math.max(0, years.indexOf(year));
  return YEAR_COLORS[index % YEAR_COLORS.length];
}

export function buildYearOverYearRows(
  rows: MonthlySoilRow[],
  depth: ComparisonDepthKey,
  years: string[],
): YearOverYearRow[] {
  const byMonth = new Map<string, MonthlySoilRow>();
  for (const row of rows) {
    if (row.month) byMonth.set(row.month, row);
  }
  return MONTH_LABELS.map((monthLabel, index) => {
    const monthIndex = index + 1;
    const values: Record<string, number | null> = {};
    const points: Record<string, YearMonthPoint> = {};
    for (const year of years) {
      const key = `${year}-${String(monthIndex).padStart(2, "0")}`;
      const row = byMonth.get(key);
      const value = row ? monthValue(row, depth) : null;
      values[year] = value;
      points[year] = {
        year,
        monthIndex,
        monthLabel,
        value,
        completeDays: row?.complete_days ?? 0,
        dayCount: row?.day_count ?? 0,
        availability: row?.availability ?? "missing",
        unit: row?.unit ?? "m³/m³",
        min: depth === "theta_root_zone_0_100_mean" ? row?.theta_root_zone_0_100_min ?? null : null,
        max: depth === "theta_root_zone_0_100_mean" ? row?.theta_root_zone_0_100_max ?? null : null,
        aggregation: row?.aggregation ?? "monthly_mean_of_complete_days",
        observationKind: row?.observation_kind ?? "modeled_volumetric_soil_moisture",
      };
    }
    return { monthIndex, monthLabel, values, points };
  });
}

export function interannualDelta(
  rows: MonthlySoilRow[],
  depth: ComparisonDepthKey,
  monthIndex: number,
  yearA: string,
  yearB: string,
): {
  thetaA: number | null;
  thetaB: number | null;
  delta: number | null;
  relativePct: number | null;
  relativeUndefinedReason: string | null;
  pointA: YearMonthPoint | null;
  pointB: YearMonthPoint | null;
} {
  const chart = buildYearOverYearRows(rows, depth, [yearA, yearB]);
  const month = chart[monthIndex - 1];
  const pointA = month?.points[yearA] ?? null;
  const pointB = month?.points[yearB] ?? null;
  const thetaA = pointA?.value ?? null;
  const thetaB = pointB?.value ?? null;
  if (thetaA == null || thetaB == null) {
    return {
      thetaA,
      thetaB,
      delta: null,
      relativePct: null,
      relativeUndefinedReason: "One or both monthly means are missing.",
      pointA,
      pointB,
    };
  }
  const delta = thetaB - thetaA;
  if (Math.abs(thetaA) < RELATIVE_CHANGE_MIN_ABS) {
    return {
      thetaA,
      thetaB,
      delta,
      relativePct: null,
      relativeUndefinedReason: "Relative change is undefined because |θ_yearA| is near zero.",
      pointA,
      pointB,
    };
  }
  return {
    thetaA,
    thetaB,
    delta,
    relativePct: (delta / thetaA) * 100,
    relativeUndefinedReason: null,
    pointA,
    pointB,
  };
}

export type SeasonId = "winter" | "spring" | "summer" | "autumn";

export const SEASONS: Array<{
  id: SeasonId;
  label: string;
  months: number[];
  winterSpansCalendarYears: boolean;
}> = [
  { id: "winter", label: "Winter DJF", months: [12, 1, 2], winterSpansCalendarYears: true },
  { id: "spring", label: "Spring MAM", months: [3, 4, 5], winterSpansCalendarYears: false },
  { id: "summer", label: "Summer JJA", months: [6, 7, 8], winterSpansCalendarYears: false },
  { id: "autumn", label: "Autumn SON", months: [9, 10, 11], winterSpansCalendarYears: false },
];

export function seasonalMean(
  rows: MonthlySoilRow[],
  depth: ComparisonDepthKey,
  season: SeasonId,
  startYear: string,
): { label: string; value: number | null; complete: boolean; months: string[] } {
  const spec = SEASONS.find((item) => item.id === season)!;
  const start = Number(startYear);
  const keys = spec.months.map((month) => {
    const year = spec.winterSpansCalendarYears && month <= 2 ? start + 1 : start;
    return `${year}-${String(month).padStart(2, "0")}`;
  });
  const label = spec.winterSpansCalendarYears
    ? `${spec.label} ${start}–${start + 1}`
    : `${spec.label} ${start}`;
  const byMonth = new Map(rows.map((item) => [item.month, item]));
  const selected = keys.map((key) => byMonth.get(key));
  if (selected.some((item) => !item || item.availability !== "complete" || monthValue(item, depth) == null)) {
    return { label, value: null, complete: false, months: keys };
  }
  const values = selected.map((item) => monthValue(item!, depth) as number);
  const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
  return { label, value: mean, complete: true, months: keys };
}

export function formatYearOverYearTooltip(point: YearMonthPoint, depth: ComparisonDepthKey): string[] {
  const lines = [
    `Year ${point.year}`,
    `Month ${point.monthLabel}`,
    `Soil depth ${depthLabel(depth)}`,
    `Monthly mean ${point.value == null ? "null" : `${point.value.toFixed(4)} m³/m³`}`,
    "Units m³/m³",
    `Complete days ${point.completeDays}`,
    `Monthly completeness ${point.availability ?? "missing"}`,
    "Source ERA5-Land",
    "Observation type modeled reanalysis",
  ];
  if (point.min != null && point.max != null) {
    lines.splice(7, 0, `Daily min/max in month ${point.min.toFixed(4)} / ${point.max.toFixed(4)} m³/m³ (not a confidence interval)`);
  }
  return lines;
}

export function yearOf(month: string | null | undefined): string | null {
  if (!month || month.length < 4) return null;
  return month.slice(0, 4);
}

export function utcDaysInMonth(year: string, monthIndex: number): number {
  return new Date(Date.UTC(Number(year), monthIndex, 0)).getUTCDate();
}
