import type {
  CombinedSoilWeather,
  CombinedSoilWeatherRow,
  DailySoilRow,
  MonthlySoilRow,
  SoilDatasetDetail,
  SoilDatasetSummary,
  SoilQuality,
  WetnessRow,
} from "@/types/api";
import { getJson } from "./api";

async function pagedRecords<T>(path: string, startDate?: string, endDate?: string): Promise<T[]> {
  const records: T[] = [];
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
    const page = await getJson<{ total: number; records: T[] }>(`${path}?${query.toString()}`);
    records.push(...page.records);
    total = page.total;
    offset += page.records.length;
    if (page.records.length === 0) break;
  }
  return records;
}

export async function listSoilDatasets(): Promise<SoilDatasetSummary[]> {
  const payload = await getJson<{ datasets: SoilDatasetSummary[] }>(
    "/api/v1/soil/datasets",
  );
  return payload.datasets;
}

export async function getSoilDataset(datasetId: string): Promise<SoilDatasetDetail> {
  return getJson(`/api/v1/soil/datasets/${encodeURIComponent(datasetId)}`);
}

export async function getSoilQuality(datasetId: string): Promise<SoilQuality> {
  return getJson(`/api/v1/soil/datasets/${encodeURIComponent(datasetId)}/quality`);
}

export async function getSoilDaily(
  datasetId: string,
  startDate?: string,
  endDate?: string,
): Promise<DailySoilRow[]> {
  return pagedRecords(
    `/api/v1/soil/datasets/${encodeURIComponent(datasetId)}/daily`,
    startDate,
    endDate,
  );
}

export async function getSoilMonthly(datasetId: string): Promise<MonthlySoilRow[]> {
  const payload = await getJson<{ months: MonthlySoilRow[] }>(
    `/api/v1/soil/datasets/${encodeURIComponent(datasetId)}/monthly`,
  );
  return payload.months;
}

export async function getWetness(
  weatherDatasetId: string,
  startDate?: string,
  endDate?: string,
): Promise<WetnessRow[]> {
  return pagedRecords(
    `/api/v1/soil/wetness/${encodeURIComponent(weatherDatasetId)}`,
    startDate,
    endDate,
  );
}

export async function getCombinedSoilWeather(
  soilDatasetId: string,
  weatherDatasetId: string,
  startDate?: string,
  endDate?: string,
): Promise<CombinedSoilWeather> {
  const records: CombinedSoilWeatherRow[] = [];
  let offset = 0;
  const limit = 2000;
  let total = Number.POSITIVE_INFINITY;
  let last: CombinedSoilWeather | null = null;
  while (offset < total) {
    const query = new URLSearchParams({
      offset: String(offset),
      limit: String(limit),
    });
    if (startDate) query.set("start_date", startDate);
    if (endDate) query.set("end_date", endDate);
    const page = await getJson<CombinedSoilWeather>(
      `/api/v1/soil/combined/${encodeURIComponent(soilDatasetId)}/${encodeURIComponent(weatherDatasetId)}?${query}`,
    );
    last = page;
    records.push(...page.records);
    total = page.total;
    offset += page.records.length;
    if (page.records.length === 0) break;
  }
  return {
    ...(last ?? {
      soil_dataset_id: soilDatasetId,
      weather_dataset_id: weatherDatasetId,
      unit_soil: "m3 m-3",
      unit_precipitation: "mm",
      observation_kind_soil: "modeled_volumetric_soil_moisture",
      is_ground_truth: false,
      is_measured_soil_moisture: false,
      spatial: null,
      lagged_correlation_status: "prepared_not_interpreted",
      total: 0,
    }),
    records,
  };
}
