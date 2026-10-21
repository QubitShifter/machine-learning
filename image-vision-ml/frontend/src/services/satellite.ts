import type {
  MapOverlayMetadata,
  NdviSample,
  SatelliteDatasetDetail,
  SatelliteDatasetSummary,
  SatelliteQuality,
  SatelliteSceneRecord,
  SceneQuality,
  TimeseriesObservation,
} from "@/types/api";
import { getJson } from "./api";

export async function listSatelliteDatasets(): Promise<SatelliteDatasetSummary[]> {
  const payload = await getJson<{ datasets: SatelliteDatasetSummary[] }>(
    "/api/v1/satellite/datasets",
  );
  return payload.datasets;
}

export async function getSatelliteDataset(
  datasetId: string,
): Promise<SatelliteDatasetDetail> {
  return getJson(`/api/v1/satellite/datasets/${encodeURIComponent(datasetId)}`);
}

export async function listSatelliteScenes(
  datasetId: string,
): Promise<SatelliteSceneRecord[]> {
  const payload = await getJson<{ scenes: SatelliteSceneRecord[] }>(
    `/api/v1/satellite/datasets/${encodeURIComponent(datasetId)}/scenes`,
  );
  return payload.scenes;
}

export async function getSatelliteTimeseries(
  datasetId: string,
): Promise<TimeseriesObservation[]> {
  const payload = await getJson<{ observations: TimeseriesObservation[] }>(
    `/api/v1/satellite/datasets/${encodeURIComponent(datasetId)}/timeseries/ndvi`,
  );
  return payload.observations;
}

export async function getSatelliteQuality(
  datasetId: string,
): Promise<SatelliteQuality> {
  return getJson(`/api/v1/satellite/datasets/${encodeURIComponent(datasetId)}/quality`);
}

export async function getSceneQuality(
  datasetId: string,
  sceneId: string,
): Promise<SceneQuality> {
  return getJson(
    `/api/v1/satellite/datasets/${encodeURIComponent(datasetId)}/scenes/${encodeURIComponent(sceneId)}/quality`,
  );
}

export async function getSceneMapMetadata(
  datasetId: string,
  sceneId: string,
): Promise<MapOverlayMetadata> {
  return getJson(
    `/api/v1/satellite/datasets/${encodeURIComponent(datasetId)}/scenes/${encodeURIComponent(sceneId)}/map/metadata`,
  );
}

export async function getNdviSample(
  datasetId: string,
  sceneId: string,
  longitude: number,
  latitude: number,
): Promise<NdviSample> {
  const query = new URLSearchParams({
    longitude: String(longitude),
    latitude: String(latitude),
  });
  return getJson(
    `/api/v1/satellite/datasets/${encodeURIComponent(datasetId)}/scenes/${encodeURIComponent(sceneId)}/map/ndvi/sample?${query}`,
  );
}
