import { useEffect, useMemo, useState } from "react";
import { Card } from "@/components/common/Card";
import { QueryState } from "@/components/common/QueryState";
import { TrainingDiagnostics } from "@/components/ml/TrainingDiagnostics";
import { TrainingEventExplorer } from "@/components/ml/TrainingEventExplorer";
import { TrainingMetricsChart } from "@/components/ml/TrainingMetricsChart";
import { TrainingPlayback } from "@/components/ml/TrainingPlayback";
import { TrainingRunComparison } from "@/components/ml/TrainingRunComparison";
import { TrainingRunOverview } from "@/components/ml/TrainingRunOverview";
import { TrainingRunSelector } from "@/components/ml/TrainingRunSelector";
import { TrainingRunTimeline } from "@/components/ml/TrainingRunTimeline";
import {
  useTrainingRun,
  useTrainingRunEvents,
  useTrainingRunMetrics,
  useTrainingRuns,
} from "@/hooks/useMl";

interface Props {
  experimentId: string | undefined;
}

export function TrainingRunsPanel({ experimentId }: Props) {
  const [algorithmFilter, setAlgorithmFilter] = useState("");
  const [horizonFilter, setHorizonFilter] = useState("");
  const [featureSetFilter, setFeatureSetFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [runId, setRunId] = useState("");
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const listing = useTrainingRuns(experimentId, {
    model: algorithmFilter || undefined,
    horizonDays: horizonFilter ? Number(horizonFilter) : undefined,
    featureSet: featureSetFilter || undefined,
    status: statusFilter || undefined,
  }, Boolean(experimentId));
  const runs = listing.data?.runs ?? [];
  const selectedId = runId && runs.some((item) => item.run_id === runId) ? runId : runs[0]?.run_id;
  useEffect(() => {
    if (selectedId && selectedId !== runId) setRunId(selectedId);
  }, [selectedId, runId]);
  const detail = useTrainingRun(experimentId, selectedId);
  const eventsQuery = useTrainingRunEvents(experimentId, selectedId);
  const metricsQuery = useTrainingRunMetrics(experimentId, selectedId);
  const events = eventsQuery.data?.events ?? [];
  const hyperparams = useMemo(() => Object.entries(detail.data?.hyperparameters ?? {}), [detail.data]);

  return (
    <div className="space-y-4">
      <Card title="Training runs">
        <QueryState isLoading={listing.isLoading} error={listing.error} onRetry={() => void listing.refetch()}>
          <TrainingRunSelector
            runs={runs}
            runId={selectedId ?? ""}
            onRunId={setRunId}
            algorithmFilter={algorithmFilter}
            onAlgorithmFilter={setAlgorithmFilter}
            horizonFilter={horizonFilter}
            onHorizonFilter={setHorizonFilter}
            featureSetFilter={featureSetFilter}
            onFeatureSetFilter={setFeatureSetFilter}
            statusFilter={statusFilter}
            onStatusFilter={setStatusFilter}
          />
        </QueryState>
      </Card>
      {selectedId && detail.data ? (
        <QueryState
          isLoading={detail.isLoading || eventsQuery.isLoading || metricsQuery.isLoading}
          error={detail.error ?? eventsQuery.error ?? metricsQuery.error}
          onRetry={() => {
            void detail.refetch();
            void eventsQuery.refetch();
          }}
        >
          <TrainingRunOverview detail={detail.data} />
          <TrainingRunTimeline events={events} status={detail.data.inferred_status ?? detail.data.status} />
          <TrainingMetricsChart events={events} algorithm={detail.data.algorithm} />
          <TrainingPlayback events={events} />
          <TrainingDiagnostics detail={detail.data} />
          <Card title="Hyperparameters">
            {hyperparams.length === 0 ? (
              <p className="text-sm text-slate-400">No hyperparameters were stored.</p>
            ) : (
              <dl className="grid gap-2 md:grid-cols-2">
                {hyperparams.map(([key, value]) => (
                  <div key={key}>
                    <dt className="text-[11px] uppercase tracking-wider text-slate-400">{key}</dt>
                    <dd className="break-all font-mono text-sm text-slate-100">{String(value)}</dd>
                  </div>
                ))}
              </dl>
            )}
          </Card>
          <Card title="Run provenance">
            <ul className="list-disc space-y-1 pl-5 text-sm text-slate-300">
              <li>Git commit: {detail.data.git_commit ?? "Unavailable"}{detail.data.git_dirty ? " (dirty)" : ""}</li>
              <li>Python: {detail.data.python_version ?? "Unavailable"}</li>
              <li>Execution mode: {detail.data.execution_mode}</li>
              <li>test_targets_accessed={String(detail.data.test_targets_accessed)}</li>
              <li>operational_availability_verified={String(detail.data.operational_availability_verified)}</li>
              <li>is_ground_truth={String(detail.data.is_ground_truth)}</li>
              <li>suitable_for_modeling={String(detail.data.suitable_for_modeling)}</li>
              <li>research_mode={detail.data.research_mode}</li>
              <li>Frozen Phase 4.1 model: {String(detail.data.is_frozen_phase_4_1_model)}</li>
            </ul>
          </Card>
          <TrainingEventExplorer events={events} />
          <TrainingRunComparison
            runs={runs}
            selectedIds={compareIds}
            onToggle={(id) => setCompareIds((current) => (
              current.includes(id) ? current.filter((item) => item !== id) : [...current, id]
            ))}
          />
        </QueryState>
      ) : null}
    </div>
  );
}
