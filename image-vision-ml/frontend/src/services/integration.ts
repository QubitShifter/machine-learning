import type {
  IntegrationDatasetDetail,
  IntegrationDatasetSummary,
  IntegrationFeatureCatalog,
  IntegrationObservation,
  IntegrationObservationPage,
  IntegrationQuality,
} from "@/types/integration";
import { getJson } from "./api";

export interface ObservationQuery {
  sceneId?: string;
  startDate?: string;
  endDate?: string;
  windowComplete?: boolean;
  availability?: "complete" | "incomplete" | "missing";
}

export async function listIntegrationDatasets(): Promise<IntegrationDatasetSummary[]> {
  const payload = await getJson<{ datasets: IntegrationDatasetSummary[] }>(
    "/api/v1/integration/datasets",
  );
  return payload.datasets;
}

export async function getIntegrationDataset(
  datasetId: string,
): Promise<IntegrationDatasetDetail> {
  return getJson(`/api/v1/integration/datasets/${encodeURIComponent(datasetId)}`);
}

export async function getIntegrationQuality(
  datasetId: string,
): Promise<IntegrationQuality> {
  return getJson(
    `/api/v1/integration/datasets/${encodeURIComponent(datasetId)}/quality`,
  );
}

export async function getIntegrationFeatures(
  datasetId: string,
): Promise<IntegrationFeatureCatalog> {
  return getJson(
    `/api/v1/integration/datasets/${encodeURIComponent(datasetId)}/features`,
  );
}

export async function getIntegrationObservations(
  datasetId: string,
  query: ObservationQuery = {},
): Promise<IntegrationObservation[]> {
  const records: IntegrationObservation[] = [];
  let offset = 0;
  const limit = 2000;
  let total = Number.POSITIVE_INFINITY;
  while (offset < total) {
    const params = new URLSearchParams({
      offset: String(offset),
      limit: String(limit),
    });
    if (query.sceneId) params.set("scene_id", query.sceneId);
    if (query.startDate) params.set("start_date", query.startDate);
    if (query.endDate) params.set("end_date", query.endDate);
    if (query.windowComplete !== undefined) {
      params.set("window_complete", String(query.windowComplete));
    }
    if (query.availability) params.set("availability", query.availability);
    const page = await getJson<IntegrationObservationPage>(
      `/api/v1/integration/datasets/${encodeURIComponent(datasetId)}/observations?${params.toString()}`,
    );
    records.push(...page.records);
    total = page.total;
    offset += page.records.length;
    if (page.records.length === 0) break;
  }
  return records;
}
