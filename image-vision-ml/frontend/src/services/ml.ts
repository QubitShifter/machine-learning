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
  TrainingRunArtifacts,
  TrainingRunDetail,
  TrainingRunEvents,
  TrainingRunList,
  TrainingRunMetrics,
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

export async function listTrainingRuns(
  experimentId: string,
  options: {
    model?: string;
    horizonDays?: number;
    featureSet?: string;
    status?: string;
    limit?: number;
  } = {},
): Promise<TrainingRunList> {
  const params = new URLSearchParams();
  if (options.model) params.set("model", options.model);
  if (options.horizonDays !== undefined) params.set("horizon_days", String(options.horizonDays));
  if (options.featureSet) params.set("feature_set", options.featureSet);
  if (options.status) params.set("status", options.status);
  if (options.limit !== undefined) params.set("limit", String(options.limit));
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return getJson(`/api/v1/ml/experiments/${encodeURIComponent(experimentId)}/runs${suffix}`);
}

export async function getTrainingRun(experimentId: string, runId: string): Promise<TrainingRunDetail> {
  return getJson(
    `/api/v1/ml/experiments/${encodeURIComponent(experimentId)}/runs/${encodeURIComponent(runId)}`,
  );
}

export async function getTrainingRunEvents(
  experimentId: string,
  runId: string,
  options: { eventType?: string; phase?: string; sequenceAfter?: number; limit?: number } = {},
): Promise<TrainingRunEvents> {
  const params = new URLSearchParams();
  if (options.eventType) params.set("event_type", options.eventType);
  if (options.phase) params.set("phase", options.phase);
  if (options.sequenceAfter !== undefined) params.set("sequence_after", String(options.sequenceAfter));
  if (options.limit !== undefined) params.set("limit", String(options.limit));
  const query = params.toString();
  const suffix = query ? `?${query}` : "";
  return getJson(
    `/api/v1/ml/experiments/${encodeURIComponent(experimentId)}/runs/${encodeURIComponent(runId)}/events${suffix}`,
  );
}

export async function getTrainingRunMetrics(experimentId: string, runId: string): Promise<TrainingRunMetrics> {
  return getJson(
    `/api/v1/ml/experiments/${encodeURIComponent(experimentId)}/runs/${encodeURIComponent(runId)}/metrics`,
  );
}

export async function getTrainingRunArtifacts(experimentId: string, runId: string): Promise<TrainingRunArtifacts> {
  return getJson(
    `/api/v1/ml/experiments/${encodeURIComponent(experimentId)}/runs/${encodeURIComponent(runId)}/artifacts`,
  );
}
