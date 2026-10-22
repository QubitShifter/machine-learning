import { useQuery } from "@tanstack/react-query";
import {
  getAgriculturalMlSummary,
  getExperiment,
  getExperimentDataset,
  getExperimentFeatures,
  getExperimentMetrics,
  getExperimentPredictions,
  getExperimentProvenance,
  getExperimentTraining,
  listExperiments,
} from "@/services/ml";

export const mlKeys = {
  research: ["ml", "research-dataset"] as const,
  experiments: ["ml", "experiments"] as const,
  detail: (id: string) => ["ml", "experiment", id] as const,
  dataset: (id: string) => ["ml", "experiment", id, "dataset"] as const,
  features: (id: string) => ["ml", "experiment", id, "features"] as const,
  training: (id: string) => ["ml", "experiment", id, "training"] as const,
  provenance: (id: string) => ["ml", "experiment", id, "provenance"] as const,
  metrics: (id: string, partition: string) => ["ml", "experiment", id, "metrics", partition] as const,
  predictions: (
    id: string,
    partition: string,
    horizon: number,
    featureSet: string,
  ) => ["ml", "experiment", id, "predictions", partition, horizon, featureSet] as const,
};

export function useAgriculturalMlSummary() {
  return useQuery({
    queryKey: mlKeys.research,
    queryFn: getAgriculturalMlSummary,
  });
}

export function useExperiments() {
  return useQuery({
    queryKey: mlKeys.experiments,
    queryFn: listExperiments,
  });
}

export function useExperiment(experimentId: string | undefined) {
  return useQuery({
    queryKey: mlKeys.detail(experimentId ?? ""),
    queryFn: () => getExperiment(experimentId!),
    enabled: Boolean(experimentId),
  });
}

export function useExperimentDataset(experimentId: string | undefined) {
  return useQuery({
    queryKey: mlKeys.dataset(experimentId ?? ""),
    queryFn: () => getExperimentDataset(experimentId!),
    enabled: Boolean(experimentId),
  });
}

export function useExperimentFeatures(experimentId: string | undefined) {
  return useQuery({
    queryKey: mlKeys.features(experimentId ?? ""),
    queryFn: () => getExperimentFeatures(experimentId!),
    enabled: Boolean(experimentId),
  });
}

export function useExperimentTraining(experimentId: string | undefined) {
  return useQuery({
    queryKey: mlKeys.training(experimentId ?? ""),
    queryFn: () => getExperimentTraining(experimentId!),
    enabled: Boolean(experimentId),
  });
}

export function useExperimentProvenance(experimentId: string | undefined) {
  return useQuery({
    queryKey: mlKeys.provenance(experimentId ?? ""),
    queryFn: () => getExperimentProvenance(experimentId!),
    enabled: Boolean(experimentId),
  });
}

export function useExperimentMetrics(
  experimentId: string | undefined,
  partition: "validation" | "test",
  enabled = true,
) {
  return useQuery({
    queryKey: mlKeys.metrics(experimentId ?? "", partition),
    queryFn: () => getExperimentMetrics(experimentId!, partition),
    enabled: Boolean(experimentId) && enabled,
  });
}

export function useExperimentPredictions(
  experimentId: string | undefined,
  partition: "validation" | "test",
  horizonDays: number,
  featureSet: string,
  enabled = true,
) {
  return useQuery({
    queryKey: mlKeys.predictions(experimentId ?? "", partition, horizonDays, featureSet),
    queryFn: () => getExperimentPredictions(experimentId!, {
      partition,
      horizonDays,
      featureSet,
      limit: 2000,
    }),
    enabled: Boolean(experimentId) && enabled,
  });
}
