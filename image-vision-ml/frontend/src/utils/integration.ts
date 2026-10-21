import type {
  CoverageKind,
  IntegrationFeatureDefinition,
  IntegrationObservation,
  ObservationFilter,
  WeatherWindowDays,
} from "@/types/integration";

export const SCATTER_FEATURE_IDS = [
  "precip_prev_7d_mm",
  "precip_prev_14d_mm",
  "precip_prev_30d_mm",
  "temp_mean_prev_7d_c",
  "temp_mean_prev_30d_c",
  "rh_mean_prev_7d_pct",
  "wind_mean_prev_7d_ms",
  "evap_prev_7d_mm",
] as const;

export type ScatterFeatureId = (typeof SCATTER_FEATURE_IDS)[number];

export const WINDOW_LOOKBACK_RULE =
  "For an acquisition on UTC day D, preceding weather features use completed UTC days D−N through D−1. Weather from acquisition day D is excluded.";

export function platformFromSceneId(sceneId: string | null | undefined): string | null {
  if (!sceneId) return null;
  if (sceneId.startsWith("S2A")) return "Sentinel-2A";
  if (sceneId.startsWith("S2B")) return "Sentinel-2B";
  if (sceneId.startsWith("S2C")) return "Sentinel-2C";
  return null;
}

export function coverageKind(observed: number | null | undefined, expected: number | null | undefined): CoverageKind {
  const have = observed ?? 0;
  const need = expected ?? 0;
  if (need <= 0 || have <= 0) return "missing";
  if (have < need) return "partial";
  return "complete";
}

export function windowField<T>(
  row: IntegrationObservation,
  days: WeatherWindowDays,
  kind: "complete" | "expected" | "observed" | "missing" | "start" | "end",
): T | null {
  const key = {
    complete: `window_${days}d_complete`,
    expected: `window_${days}d_expected_days`,
    observed: `window_${days}d_observed_days`,
    missing: `window_${days}d_missing_days`,
    start: `window_${days}d_start_utc`,
    end: `window_${days}d_end_utc`,
  }[kind] as keyof IntegrationObservation;
  return (row[key] as T | null | undefined) ?? null;
}

export function precipForWindow(row: IntegrationObservation, days: WeatherWindowDays): number | null {
  if (days === 7) return row.precip_prev_7d_mm;
  if (days === 14) return row.precip_prev_14d_mm;
  return row.precip_prev_30d_mm;
}

export function featureValue(row: IntegrationObservation, id: string): number | null {
  const value = row[id as keyof IntegrationObservation];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function filterObservations(
  rows: IntegrationObservation[],
  filter: ObservationFilter,
): IntegrationObservation[] {
  if (filter === "complete") {
    return rows.filter((row) => row.weather_feature_window_complete === true);
  }
  if (filter === "incomplete") {
    return rows.filter((row) => row.weather_feature_window_complete !== true);
  }
  return rows;
}

export function sortObservations(rows: IntegrationObservation[]): IntegrationObservation[] {
  return [...rows].sort((a, b) => {
    const date = String(b.observation_date_utc ?? "").localeCompare(String(a.observation_date_utc ?? ""));
    if (date !== 0) return date;
    return String(a.scene_id ?? "").localeCompare(String(b.scene_id ?? ""));
  });
}

export function defaultObservation(
  rows: IntegrationObservation[],
  requestedScene?: string | null,
): { sceneId: string | undefined; invalidRequested: boolean } {
  const ordered = sortObservations(rows.filter((row) => row.scene_id));
  if (requestedScene && ordered.some((row) => row.scene_id === requestedScene)) {
    return { sceneId: requestedScene, invalidRequested: false };
  }
  const complete = ordered.find((row) => row.weather_feature_window_complete === true);
  return {
    sceneId: complete?.scene_id ?? ordered[0]?.scene_id ?? undefined,
    invalidRequested: Boolean(requestedScene),
  };
}

export function pairedObservations(
  rows: IntegrationObservation[],
  featureId: string,
): Array<{ row: IntegrationObservation; x: number; y: number }> {
  const pairs: Array<{ row: IntegrationObservation; x: number; y: number }> = [];
  for (const row of rows) {
    const x = featureValue(row, featureId);
    const y = row.ndvi_mean;
    if (x === null || y === null || y === undefined || Number.isNaN(y)) continue;
    pairs.push({ row, x, y });
  }
  return pairs;
}

export function featureMeta(
  catalog: IntegrationFeatureDefinition[] | undefined,
  id: string,
): IntegrationFeatureDefinition | undefined {
  return catalog?.find((item) => item.id === id);
}

export function weatherAvailabilityLabel(row: IntegrationObservation): string {
  if (row.weather_feature_window_complete) return "complete windows";
  const observed = (row.window_7d_observed_days ?? 0)
    + (row.window_14d_observed_days ?? 0)
    + (row.window_30d_observed_days ?? 0);
  if (observed === 0) return "missing weather";
  return "incomplete windows";
}
