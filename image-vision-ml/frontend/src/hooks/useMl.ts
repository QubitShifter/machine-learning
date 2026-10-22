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
  getTrainingRun,
  getTrainingRunArtifacts,
  getTrainingRunEvents,
  getTrainingRunMetrics,
  listExperiments,
  listTrainingRuns,
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
  runs: (id: string, model?: string, horizon?: number, featureSet?: string, status?: string) =>
    ["ml", "experiment", id, "runs", model ?? "", horizon ?? "", featureSet ?? "", status ?? ""] as const,
  run: (id: string, runId: string) => ["ml", "experiment", id, "run", runId] as const,
  runEvents: (id: string, runId: string) => ["ml", "experiment", id, "run", runId, "events"] as const,
  runMetrics: (id: string, runId: string) => ["ml", "experiment", id, "run", runId, "metrics"] as const,
  runArtifacts: (id: string, runId: string) => ["ml", "experiment", id, "run", runId, "artifacts"] as const,
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

export function useTrainingRuns(
  experimentId: string | undefined,
  filters: { model?: string; horizonDays?: number; featureSet?: string; status?: string } = {},
  enabled = true,
) {
  return useQuery({
    queryKey: mlKeys.runs(experimentId ?? "", filters.model, filters.horizonDays, filters.featureSet, filters.status),
    queryFn: () => listTrainingRuns(experimentId!, {
      model: filters.model,
      horizonDays: filters.horizonDays,
      featureSet: filters.featureSet,
      status: filters.status,
      limit: 200,
    }),
    enabled: Boolean(experimentId) && enabled,
  });
}

export function useTrainingRun(experimentId: string | undefined, runId: string | undefined) {
  return useQuery({
    queryKey: mlKeys.run(experimentId ?? "", runId ?? ""),
    queryFn: () => getTrainingRun(experimentId!, runId!),
    enabled: Boolean(experimentId && runId),
  });
}

export function useTrainingRunEvents(experimentId: string | undefined, runId: string | undefined) {
  return useQuery({
    queryKey: mlKeys.runEvents(experimentId ?? "", runId ?? ""),
    queryFn: () => getTrainingRunEvents(experimentId!, runId!, { limit: 2000 }),
    enabled: Boolean(experimentId && runId),
  });
}

export function useTrainingRunMetrics(experimentId: string | undefined, runId: string | undefined) {
  return useQuery({
    queryKey: mlKeys.runMetrics(experimentId ?? "", runId ?? ""),
    queryFn: () => getTrainingRunMetrics(experimentId!, runId!),
    enabled: Boolean(experimentId && runId),
  });
}

export function useTrainingRunArtifacts(experimentId: string | undefined, runId: string | undefined) {
  return useQuery({
    queryKey: mlKeys.runArtifacts(experimentId ?? "", runId ?? ""),
    queryFn: () => getTrainingRunArtifacts(experimentId!, runId!),
    enabled: Boolean(experimentId && runId),
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
