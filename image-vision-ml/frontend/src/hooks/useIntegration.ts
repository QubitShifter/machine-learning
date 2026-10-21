import { useQuery } from "@tanstack/react-query";
import {
  getIntegrationDataset,
  getIntegrationFeatures,
  getIntegrationObservations,
  getIntegrationQuality,
  listIntegrationDatasets,
} from "@/services/integration";

export const integrationKeys = {
  datasets: ["integration", "datasets"] as const,
  dataset: (id: string) => ["integration", "dataset", id] as const,
  observations: (id: string) => ["integration", "observations", id] as const,
  quality: (id: string) => ["integration", "quality", id] as const,
  features: (id: string) => ["integration", "features", id] as const,
  allFor: (id: string) => ["integration", id] as const,
};

export function useIntegrationDatasets() {
  return useQuery({
    queryKey: integrationKeys.datasets,
    queryFn: listIntegrationDatasets,
  });
}

export function useIntegrationDataset(datasetId: string | undefined) {
  return useQuery({
    queryKey: integrationKeys.dataset(datasetId ?? ""),
    queryFn: () => getIntegrationDataset(datasetId!),
    enabled: Boolean(datasetId),
  });
}

export function useIntegrationObservations(datasetId: string | undefined) {
  return useQuery({
    queryKey: integrationKeys.observations(datasetId ?? ""),
    queryFn: () => getIntegrationObservations(datasetId!),
    enabled: Boolean(datasetId),
  });
}

export function useIntegrationQuality(datasetId: string | undefined) {
  return useQuery({
    queryKey: integrationKeys.quality(datasetId ?? ""),
    queryFn: () => getIntegrationQuality(datasetId!),
    enabled: Boolean(datasetId),
  });
}

export function useIntegrationFeatures(datasetId: string | undefined) {
  return useQuery({
    queryKey: integrationKeys.features(datasetId ?? ""),
    queryFn: () => getIntegrationFeatures(datasetId!),
    enabled: Boolean(datasetId),
  });
}
