import type { AgriculturalMlSummary } from "@/types/api";
import type {
  ExperimentDataset,
  ExperimentDetail,
  ExperimentFeatures,
  ExperimentListItem,
  ExperimentMetrics,
  ExperimentPredictions,
  ExperimentProvenance,
  ExperimentTraining,
} from "@/types/ml";
import { getJson } from "./api";

export async function getAgriculturalMlSummary(): Promise<AgriculturalMlSummary> {
  return getJson("/api/v1/ml/research-dataset");
}

export async function listExperiments(): Promise<ExperimentListItem[]> {
  return getJson("/api/v1/ml/experiments");
}

export async function getExperiment(experimentId: string): Promise<ExperimentDetail> {
  return getJson(`/api/v1/ml/experiments/${encodeURIComponent(experimentId)}`);
}

export async function getExperimentMetrics(
  experimentId: string,
  partition: "validation" | "test",
): Promise<ExperimentMetrics> {
  const params = new URLSearchParams({ partition });
  return getJson(`/api/v1/ml/experiments/${encodeURIComponent(experimentId)}/metrics?${params}`);
}

export async function getExperimentPredictions(
  experimentId: string,
  options: {
    partition: "validation" | "test";
    horizonDays?: number;
    modelId?: string;
    featureSet?: string;
    offset?: number;
    limit?: number;
  },
): Promise<ExperimentPredictions> {
  const params = new URLSearchParams({ partition: options.partition });
  if (options.horizonDays !== undefined) params.set("horizon_days", String(options.horizonDays));
  if (options.modelId) params.set("model_id", options.modelId);
  if (options.featureSet) params.set("feature_set", options.featureSet);
  if (options.offset !== undefined) params.set("offset", String(options.offset));
  if (options.limit !== undefined) params.set("limit", String(options.limit));
  return getJson(`/api/v1/ml/experiments/${encodeURIComponent(experimentId)}/predictions?${params}`);
}

export async function getExperimentDataset(experimentId: string): Promise<ExperimentDataset> {
  return getJson(`/api/v1/ml/experiments/${encodeURIComponent(experimentId)}/dataset`);
}

export async function getExperimentFeatures(experimentId: string): Promise<ExperimentFeatures> {
  return getJson(`/api/v1/ml/experiments/${encodeURIComponent(experimentId)}/features`);
}

export async function getExperimentTraining(experimentId: string): Promise<ExperimentTraining> {
  return getJson(`/api/v1/ml/experiments/${encodeURIComponent(experimentId)}/training`);
}

export async function getExperimentProvenance(experimentId: string): Promise<ExperimentProvenance> {
  return getJson(`/api/v1/ml/experiments/${encodeURIComponent(experimentId)}/provenance`);
}
