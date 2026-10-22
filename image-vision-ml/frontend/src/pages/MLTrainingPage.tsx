import { useMemo, useState } from "react";
import { Card } from "@/components/common/Card";
import { QueryState } from "@/components/common/QueryState";
import { AlgorithmExplorer } from "@/components/ml/AlgorithmExplorer";
import { DatasetExplorer } from "@/components/ml/DatasetExplorer";
import { ExperimentProvenancePanel } from "@/components/ml/ExperimentProvenancePanel";
import { ExperimentSelector } from "@/components/ml/ExperimentSelector";
import { MathematicsLab } from "@/components/ml/MathematicsLab";
import { ModelEvaluation } from "@/components/ml/ModelEvaluation";
import { TrainingLifecycle } from "@/components/ml/TrainingLifecycle";
import { TrainingOverview } from "@/components/ml/TrainingOverview";
import { TrainingRunsPanel } from "@/components/ml/TrainingRunsPanel";
import {
  useExperiment,
  useExperimentDataset,
  useExperimentFeatures,
  useExperimentMetrics,
  useExperimentPredictions,
  useExperimentProvenance,
  useExperimentTraining,
  useExperiments,
} from "@/hooks/useMl";
import type { AlgorithmId, LabTab, PartitionId } from "@/types/ml";
import { sampleCount, trainedAlgorithms } from "@/utils/mlLab";

function textYear(value: unknown, label: string): string {
  if (value === null || value === undefined || String(value).trim() === "") {
    return `${label} year unavailable`;
  }
  return `${label} ${String(value)}`;
}

export function MLTrainingPage() {
  const listing = useExperiments();
  const experiments = listing.data ?? [];
  const [experimentId, setExperimentId] = useState(experiments[0]?.experiment_id ?? "");
  const selectedId = experimentId || experiments[0]?.experiment_id;
  const detail = useExperiment(selectedId);
  const dataset = useExperimentDataset(selectedId);
  const features = useExperimentFeatures(selectedId);
  const training = useExperimentTraining(selectedId);
  const provenance = useExperimentProvenance(selectedId);
  const [horizon, setHorizon] = useState(1);
  const [algorithm, setAlgorithm] = useState<AlgorithmId>("persistence");
  const [featureSet, setFeatureSet] = useState("C");
  const [partition, setPartition] = useState<PartitionId>("validation");
  const [tab, setTab] = useState<LabTab>("overview");

  const horizons = detail.data?.horizons_days?.length ? detail.data.horizons_days : [1, 3, 7];
  const enabledSets = (dataset.data?.feature_sets ?? [])
    .filter((item) => item.enabled)
    .map((item) => item.id);
  const algorithms = useMemo(
    () => trainedAlgorithms(training.data?.selected ?? []),
    [training.data],
  );
  const testEvaluated = Boolean(detail.data?.test_evaluated);
  const effectivePartition: PartitionId = partition === "test" && !testEvaluated ? "validation" : partition;
  const validationMetrics = useExperimentMetrics(selectedId, "validation");
  const testMetrics = useExperimentMetrics(selectedId, "test", testEvaluated);
  const predictions = useExperimentPredictions(
    selectedId,
    effectivePartition,
    horizon,
    featureSet || "C",
    tab === "evaluation",
  );

  const trainN = sampleCount(dataset.data?.counts ?? [], "training", horizon, featureSet || "C");
  const valN = sampleCount(dataset.data?.counts ?? [], "validation", horizon, featureSet || "C");
  const testN = sampleCount(dataset.data?.counts ?? [], "test", horizon, featureSet || "C");
  const targetLabel = detail.data
    ? `${detail.data.target_variable ?? "swvl1"} · ${detail.data.depth_label ?? "depth unavailable"}`
    : "Unavailable";
  const splits = dataset.data?.chronological_splits ?? {};
  const sourcePeriod = [
    textYear(splits.training, "Training"),
    textYear(splits.validation, "Validation"),
    textYear(splits.test, "Testing"),
  ].join(" · ") || "Unavailable";

  return (
    <div className="space-y-4">
      <Card title="ML Training Laboratory">
        <p className="mb-3 text-sm text-slate-300">
          Research inspection of stored soil-moisture forecasting experiments. Visiting this page does not train models.
          Educational simulations are labeled separately from ERA5-Land results.
        </p>
        <QueryState isLoading={listing.isLoading} error={listing.error} onRetry={() => void listing.refetch()}>
          {experiments.length === 0 ? (
            <p className="text-sm text-slate-400">No experiment artifacts are available.</p>
          ) : (
            <ExperimentSelector
              experiments={experiments}
              experimentId={selectedId ?? ""}
              onExperiment={setExperimentId}
              targetLabel={targetLabel}
              horizons={horizons}
              horizon={horizon}
              onHorizon={setHorizon}
              algorithms={algorithms}
              algorithm={algorithm}
              onAlgorithm={setAlgorithm}
              featureSets={enabledSets.length ? enabledSets : detail.data?.feature_sets ?? ["C"]}
              featureSet={featureSet}
              onFeatureSet={setFeatureSet}
              partition={effectivePartition}
              onPartition={setPartition}
              testEvaluated={testEvaluated}
              selected={training.data?.selected ?? []}
              telemetryAvailable={Boolean(training.data?.telemetry?.available)}
              tab={tab}
              onTab={setTab}
            />
          )}
        </QueryState>
      </Card>

      <QueryState
        isLoading={detail.isLoading || dataset.isLoading}
        error={detail.error ?? dataset.error ?? training.error}
        onRetry={() => {
          void detail.refetch();
          void dataset.refetch();
        }}
      >
        {tab === "overview" && detail.data ? (
          <TrainingOverview
            detail={detail.data}
            training={training.data}
            algorithm={algorithm}
            horizon={horizon}
            featureSet={featureSet}
            featureCount={features.data?.predictive_feature_count ?? null}
            trainN={trainN}
            valN={valN}
            testN={testN}
            sourcePeriod={sourcePeriod}
            validationMetrics={validationMetrics.data?.records ?? []}
            testMetrics={testMetrics.data?.records ?? null}
            testEvaluated={testEvaluated}
          />
        ) : null}
        {tab === "dataset" && dataset.data ? (
          <DatasetExplorer
            dataset={dataset.data}
            features={features.data}
            horizon={horizon}
            featureSet={featureSet}
          />
        ) : null}
        {tab === "algorithms" ? (
          <AlgorithmExplorer algorithm={algorithm} horizon={horizon} training={training.data} />
        ) : null}
        {tab === "training" ? <TrainingLifecycle training={training.data} /> : null}
        {tab === "runs" ? <TrainingRunsPanel experimentId={selectedId} /> : null}
        {tab === "evaluation" ? (
          <QueryState
            isLoading={predictions.isLoading || validationMetrics.isLoading}
            error={predictions.error ?? validationMetrics.error}
            onRetry={() => void predictions.refetch()}
          >
            <ModelEvaluation
              horizon={horizon}
              featureSet={featureSet}
              partition={effectivePartition}
              algorithm={algorithm}
              validationRecords={validationMetrics.data?.records ?? []}
              testRecords={testMetrics.data?.records ?? []}
              testEvaluated={testEvaluated}
              predictions={predictions.data?.records ?? []}
              predictionLabel={predictions.data?.label ?? "ERA5-Land modeled soil-moisture research predictions. Not field measurements."}
            />
          </QueryState>
        ) : null}
        {tab === "mathematics" ? <MathematicsLab /> : null}
        {tab === "provenance" && provenance.data ? (
          <ExperimentProvenancePanel provenance={provenance.data} />
        ) : null}
      </QueryState>
    </div>
  );
}
