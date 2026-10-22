import type { ReactNode } from "react";
import type { AlgorithmId, ExperimentListItem, LabTab, PartitionId } from "@/types/ml";
import { ALGORITHM_LABELS, algorithmStatus } from "@/utils/mlLab";

interface Props {
  experiments: ExperimentListItem[];
  experimentId: string;
  onExperiment: (id: string) => void;
  targetLabel: string;
  horizons: number[];
  horizon: number;
  onHorizon: (value: number) => void;
  algorithms: AlgorithmId[];
  algorithm: AlgorithmId;
  onAlgorithm: (value: AlgorithmId) => void;
  featureSets: string[];
  featureSet: string;
  onFeatureSet: (value: string) => void;
  partition: PartitionId;
  onPartition: (value: PartitionId) => void;
  testEvaluated: boolean;
  selected: Record<string, unknown>[];
  telemetryAvailable: boolean;
  tab: LabTab;
  onTab: (value: LabTab) => void;
}

const TABS: { id: LabTab; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "dataset", label: "Dataset" },
  { id: "algorithms", label: "Algorithms" },
  { id: "training", label: "Training Process" },
  { id: "runs", label: "Training Runs" },
  { id: "evaluation", label: "Evaluation" },
  { id: "mathematics", label: "Mathematics" },
  { id: "provenance", label: "Experiment Provenance" },
];

export function ExperimentSelector(props: Props) {
  return (
    <div className="space-y-3">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <Field label="Experiment">
          <select
            value={props.experimentId}
            onChange={(event) => props.onExperiment(event.target.value)}
            aria-label="Experiment"
          >
            {props.experiments.length === 0 ? <option value="">No experiments</option> : null}
            {props.experiments.map((item) => (
              <option key={item.experiment_id} value={item.experiment_id}>
                {item.experiment_id}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Target / depth">
          <select value={props.targetLabel} disabled aria-label="Target variable">
            <option>{props.targetLabel || "Unavailable"}</option>
          </select>
        </Field>
        <Field label="Forecast horizon">
          <select
            value={String(props.horizon)}
            onChange={(event) => props.onHorizon(Number(event.target.value))}
            aria-label="Forecast horizon"
          >
            {(props.horizons.length ? props.horizons : [1, 3, 7]).map((item) => (
              <option key={item} value={item}>{item} day</option>
            ))}
          </select>
        </Field>
        <Field label="Algorithm">
          <select
            value={props.algorithm}
            onChange={(event) => props.onAlgorithm(event.target.value as AlgorithmId)}
            aria-label="Algorithm"
          >
            {props.algorithms.map((item) => (
              <option key={item} value={item}>
                {ALGORITHM_LABELS[item]} — {algorithmStatus(item, props.selected, props.testEvaluated, props.telemetryAvailable)}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Feature set">
          <select
            value={props.featureSet}
            onChange={(event) => props.onFeatureSet(event.target.value)}
            aria-label="Feature set"
          >
            {(props.featureSets.length ? props.featureSets : ["C"]).map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
        </Field>
        <Field label="Evaluation partition">
          <select
            value={props.partition}
            onChange={(event) => props.onPartition(event.target.value as PartitionId)}
            aria-label="Evaluation partition"
          >
            <option value="validation">Validation, 2024</option>
            <option value="test" disabled={!props.testEvaluated}>
              {props.testEvaluated ? "Final test, 2025" : "Final test, 2025 (not evaluated)"}
            </option>
          </select>
        </Field>
      </div>
      <div className="flex flex-wrap gap-1" role="tablist" aria-label="Laboratory sections">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={props.tab === item.id}
            className={`rounded px-3 py-1.5 text-xs ${
              props.tab === item.id
                ? "bg-moss-600/30 text-moss-300"
                : "border border-ink-600 text-slate-300 hover:bg-ink-800"
            }`}
            onClick={() => props.onTab(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block text-xs text-slate-400">
      {label}
      <div className="mt-1">
        <div className="[&_select]:w-full [&_select]:rounded [&_select]:border [&_select]:border-ink-600 [&_select]:bg-ink-800 [&_select]:px-2 [&_select]:py-1.5 [&_select]:text-sm [&_select]:text-slate-100">
          {children}
        </div>
      </div>
    </label>
  );
}
