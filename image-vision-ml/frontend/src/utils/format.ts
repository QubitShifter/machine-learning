export function formatNumber(
  value: number | null | undefined,
  digits = 2,
): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }
  return value.toLocaleString("en-US", {
    maximumFractionDigits: digits,
    minimumFractionDigits: Number.isInteger(value) ? 0 : Math.min(digits, 1),
  });
}

export function formatPercent(
  value: number | null | undefined,
  digits = 1,
): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }
  return `${value.toFixed(digits)}%`;
}

export function formatStatus(value: string | null | undefined): string {
  if (!value) return "unknown";
  return value.replaceAll("_", " ");
}

export function latestValidMonth<T extends { availability?: string | null; complete_days: number; month: string }>(
  months: T[],
): T | undefined {
  return [...months]
    .reverse()
    .find((item) => item.availability === "downloaded" && item.complete_days > 0);
}

export function isCompleteDay(row: {
  hourly_records_available?: number | null;
  hourly_records_expected?: number | null;
  boundary_00utc_available?: boolean | null;
  quality_status?: string | null;
}): boolean {
  return (
    row.hourly_records_available === (row.hourly_records_expected ?? 24) &&
    row.boundary_00utc_available === true
  );
}

export function preferredSatelliteDataset(
  datasets: Array<{ dataset_id: string; scene_count: number }>,
): string | undefined {
  const preferred = datasets.find((item) => item.dataset_id === "plovdiv_2023_2025");
  return (preferred ?? datasets[0])?.dataset_id;
}

export function preferredWeatherDataset(
  datasets: Array<{ dataset_id: string }>,
): string | undefined {
  const preferred = datasets.find((item) => item.dataset_id === "plovdiv_weather_2023_2025");
  return (preferred ?? datasets[0])?.dataset_id;
}

export function preferredIntegrationDataset(
  datasets: Array<{ dataset_id: string; satellite_dataset_id?: string | null }>,
  satelliteId?: string,
): string | undefined {
  if (satelliteId) {
    const matched = datasets.find(
      (item) => item.dataset_id === satelliteId || item.satellite_dataset_id === satelliteId,
    );
    if (matched) return matched.dataset_id;
  }
  const preferred = datasets.find((item) => item.dataset_id === "plovdiv_2023_2025");
  return (preferred ?? datasets[0])?.dataset_id;
}

export function formatUtcTimestamp(value: string | null | undefined): string {
  if (!value) return "—";
  const text = String(value);
  const date = text.slice(0, 10);
  if (text.includes("T") && text.length >= 19) {
    return `${date} ${text.slice(11, 19)} UTC`;
  }
  return `${date} UTC`;
}

export function formatMeasured(
  value: number | null | undefined,
  unit: string,
  digits = 3,
): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "Unavailable";
  }
  return `${formatNumber(value, digits)} ${unit}`;
}
