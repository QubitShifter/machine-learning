import { useQuery } from "@tanstack/react-query";
import {
  getNdviSample,
  getPixelInspect,
  getSatelliteDataset,
  getSatelliteQuality,
  getSatelliteTimeseries,
  getSceneHistograms,
  getSceneMapMetadata,
  getSceneQuality,
  listSatelliteDatasets,
  listSatelliteScenes,
} from "@/services/satellite";

export const satelliteKeys = {
  datasets: ["satellite", "datasets"] as const,
  dataset: (id: string) => ["satellite", "dataset", id] as const,
  scenes: (id: string) => ["satellite", "scenes", id] as const,
  timeseries: (id: string) => ["satellite", "timeseries", id] as const,
  quality: (id: string) => ["satellite", "quality", id] as const,
  sceneQuality: (datasetId: string, sceneId: string) =>
    ["satellite", "scene-quality", datasetId, sceneId] as const,
  mapMetadata: (datasetId: string, sceneId: string) =>
    ["satellite", "map-metadata", datasetId, sceneId] as const,
  histograms: (datasetId: string, sceneId: string, bins: number) =>
    ["satellite", "histograms", datasetId, sceneId, bins] as const,
};

export function useSatelliteDatasets() {
  return useQuery({
    queryKey: satelliteKeys.datasets,
    queryFn: listSatelliteDatasets,
  });
}

export function useSatelliteDataset(datasetId: string | undefined) {
  return useQuery({
    queryKey: satelliteKeys.dataset(datasetId ?? ""),
    queryFn: () => getSatelliteDataset(datasetId!),
    enabled: Boolean(datasetId),
  });
}

export function useSatelliteScenes(datasetId: string | undefined) {
  return useQuery({
    queryKey: satelliteKeys.scenes(datasetId ?? ""),
    queryFn: () => listSatelliteScenes(datasetId!),
    enabled: Boolean(datasetId),
  });
}

export function useSatelliteTimeseries(datasetId: string | undefined) {
  return useQuery({
    queryKey: satelliteKeys.timeseries(datasetId ?? ""),
    queryFn: () => getSatelliteTimeseries(datasetId!),
    enabled: Boolean(datasetId),
  });
}

export function useSatelliteQuality(datasetId: string | undefined) {
  return useQuery({
    queryKey: satelliteKeys.quality(datasetId ?? ""),
    queryFn: () => getSatelliteQuality(datasetId!),
    enabled: Boolean(datasetId),
  });
}

export function useSceneQuality(
  datasetId: string | undefined,
  sceneId: string | undefined,
) {
  return useQuery({
    queryKey: satelliteKeys.sceneQuality(datasetId ?? "", sceneId ?? ""),
    queryFn: () => getSceneQuality(datasetId!, sceneId!),
    enabled: Boolean(datasetId && sceneId),
  });
}

export function useSceneMapMetadata(
  datasetId: string | undefined,
  sceneId: string | undefined,
) {
  return useQuery({
    queryKey: satelliteKeys.mapMetadata(datasetId ?? "", sceneId ?? ""),
    queryFn: () => getSceneMapMetadata(datasetId!, sceneId!),
    enabled: Boolean(datasetId && sceneId),
  });
}

export function useSceneHistograms(
  datasetId: string | undefined,
  sceneId: string | undefined,
  bins = 45,
) {
  return useQuery({
    queryKey: satelliteKeys.histograms(datasetId ?? "", sceneId ?? "", bins),
    queryFn: () => getSceneHistograms(datasetId!, sceneId!, bins),
    enabled: Boolean(datasetId && sceneId),
  });
}

export function sampleNdviAt(
  datasetId: string,
  sceneId: string,
  longitude: number,
  latitude: number,
) {
  return getNdviSample(datasetId, sceneId, longitude, latitude);
}

export function inspectPixelAt(
  datasetId: string,
  sceneId: string,
  longitude: number,
  latitude: number,
) {
  return getPixelInspect(datasetId, sceneId, longitude, latitude);
}
