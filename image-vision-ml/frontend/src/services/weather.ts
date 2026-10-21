import type {
  DailyWeatherRow,
  MonthlyWeatherRow,
  WeatherDatasetDetail,
  WeatherDatasetSummary,
  WeatherQuality,
  WeatherSummary,
} from "@/types/api";
import { getJson } from "./api";

export async function listWeatherDatasets(): Promise<WeatherDatasetSummary[]> {
  const payload = await getJson<{ datasets: WeatherDatasetSummary[] }>(
    "/api/v1/weather/datasets",
  );
  return payload.datasets;
}

export async function getWeatherDataset(
  datasetId: string,
): Promise<WeatherDatasetDetail> {
  return getJson(`/api/v1/weather/datasets/${encodeURIComponent(datasetId)}`);
}

export async function getWeatherQuality(
  datasetId: string,
): Promise<WeatherQuality> {
  return getJson(`/api/v1/weather/datasets/${encodeURIComponent(datasetId)}/quality`);
}

export async function getWeatherMonthly(
  datasetId: string,
): Promise<MonthlyWeatherRow[]> {
  const payload = await getJson<{ months: MonthlyWeatherRow[] }>(
    `/api/v1/weather/datasets/${encodeURIComponent(datasetId)}/monthly`,
  );
  return payload.months;
}

export async function getWeatherSummary(
  datasetId: string,
  startDate?: string,
  endDate?: string,
): Promise<WeatherSummary> {
  const query = new URLSearchParams();
  if (startDate) query.set("start_date", startDate);
  if (endDate) query.set("end_date", endDate);
  const suffix = query.size ? `?${query.toString()}` : "";
  return getJson(
    `/api/v1/weather/datasets/${encodeURIComponent(datasetId)}/summary${suffix}`,
  );
}

export async function getWeatherDaily(
  datasetId: string,
  startDate?: string,
  endDate?: string,
): Promise<DailyWeatherRow[]> {
  const records: DailyWeatherRow[] = [];
  let offset = 0;
  const limit = 2000;
  let total = Number.POSITIVE_INFINITY;
  while (offset < total) {
    const query = new URLSearchParams({
      offset: String(offset),
      limit: String(limit),
    });
    if (startDate) query.set("start_date", startDate);
    if (endDate) query.set("end_date", endDate);
    const page = await getJson<{
      total: number;
      records: DailyWeatherRow[];
    }>(
      `/api/v1/weather/datasets/${encodeURIComponent(datasetId)}/daily?${query.toString()}`,
    );
    records.push(...page.records);
    total = page.total;
    offset += page.records.length;
    if (page.records.length === 0) break;
  }
  return records;
}
