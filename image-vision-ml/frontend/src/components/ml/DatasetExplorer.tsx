import { useMemo, useState } from "react";
import { Card } from "@/components/common/Card";
import { Metric } from "@/components/common/Metric";
import type { ExperimentDataset, ExperimentFeatures } from "@/types/ml";
import { displayValue, exclusionCount, sampleCount } from "@/utils/mlLab";

interface Props {
  dataset: ExperimentDataset;
  features: ExperimentFeatures | undefined;
  horizon: number;
  featureSet: string;
}

export function DatasetExplorer({ dataset, features, horizon, featureSet }: Props) {
  const [query, setQuery] = useState("");
  const train = sampleCount(dataset.counts, "training", horizon, featureSet);
  const validation = sampleCount(dataset.counts, "validation", horizon, featureSet);
  const test = sampleCount(dataset.counts, "test", horizon, featureSet);
  const trainEx = exclusionCount(dataset.counts, "training", horizon, featureSet);
  const rows = useMemo(() => {
    const records = features?.records ?? [];
    const needle = query.trim().toLowerCase();
    if (!needle) return records;
    return records.filter((item) => (
      item.column_name.toLowerCase().includes(needle)
      || (item.formula ?? "").toLowerCase().includes(needle)
      || (item.input_source ?? "").toLowerCase().includes(needle)
    ));
  }, [features, query]);

  return (
    <div className="space-y-4">
      <Card title="Chronological partitions">
        <div className="grid gap-3 md:grid-cols-3">
          <SplitCard year="2023" role="Training" n={train} excluded={trainEx} color="bg-moss-600/20" />
          <SplitCard year="2024" role="Validation" n={validation} excluded={exclusionCount(dataset.counts, "validation", horizon, featureSet)} color="bg-sand-400/15" />
          <SplitCard year="2025" role="Testing" n={test} excluded={exclusionCount(dataset.counts, "test", horizon, featureSet)} color="bg-slate-700/50" />
        </div>
        <ul className="mt-4 list-disc space-y-1 pl-5 text-sm text-slate-300">
          <li>Chronological splits keep future years out of training. Soil moisture is serially correlated, so random shuffling leaks future states.</li>
          <li>Leakage is using information that would not have been available at issue time 00:00 UTC. Features stop at D−1.</li>
          <li>Scalers and seasonal means are fitted on 2023 only. 2024 is for model selection. 2025 is a frozen holdout.</li>
        </ul>
        <p className="mt-2 text-xs text-slate-500">
          Counts are complete-case rows for horizon {horizon} and feature set {featureSet}. Exclusions combine warm-up, missing windows, and horizon-aware purging; those causes are not separated in the stored summary.
        </p>
      </Card>
      <Card title="Sample statistics">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <Metric label="Joined feature/target rows" value={displayValue(dataset.n_joined_rows, 0)} />
          <Metric label="Eligible rows" value={displayValue(dataset.eligible_rows, 0)} />
          <Metric label="Training rows" value={displayValue(train, 0)} />
          <Metric label="Validation rows" value={displayValue(validation, 0)} />
          <Metric label="Test rows" value={displayValue(test, 0)} />
          <Metric label="Training exclusions" value={displayValue(trainEx, 0)} />
          <Metric label="Missing-data policy" value={dataset.missing_data_policy ?? "Unavailable"} />
          <Metric label="Predictive features" value={displayValue(features?.predictive_feature_count, 0)} hint="Not the 168-column feature table width." />
        </div>
      </Card>
      <Card title="Feature explorer">
        <input
          className="mb-3 w-full rounded border border-ink-600 bg-ink-800 px-2 py-1.5 text-sm"
          placeholder="Search features"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          aria-label="Search features"
        />
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-xs">
            <thead className="text-slate-400">
              <tr>
                <th className="px-2 py-1">Name</th>
                <th className="px-2 py-1">Meaning / formula</th>
                <th className="px-2 py-1">Source</th>
                <th className="px-2 py-1">Unit</th>
                <th className="px-2 py-1">Lookback</th>
                <th className="px-2 py-1">Sets</th>
                <th className="px-2 py-1">Usage</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((item) => (
                <tr key={item.column_name} className="border-t border-ink-700">
                  <td className="px-2 py-1 font-mono text-slate-100">{item.column_name}</td>
                  <td className="px-2 py-1 text-slate-300">{item.formula ?? item.scientific_meaning ?? "Unavailable"}</td>
                  <td className="px-2 py-1">{item.input_source ?? "Unavailable"}</td>
                  <td className="px-2 py-1">{item.units ?? "Unavailable"}</td>
                  <td className="px-2 py-1">{item.temporal_window ?? "Unavailable"}</td>
                  <td className="px-2 py-1">{item.feature_sets.join(", ") || "Unavailable"}</td>
                  <td className="px-2 py-1">{item.used_by_primary ? "primary model" : "catalog only"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-xs text-slate-500">{features?.note}</p>
        <ul className="mt-2 text-xs text-slate-500">
          {(dataset.feature_sets ?? []).map((item) => (
            <li key={item.id}>
              Feature set {item.id}: {item.enabled ? "available" : "not trained"}
              {item.reason ? ` — ${item.reason}` : ""}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}

function SplitCard({
  year, role, n, excluded, color,
}: {
  year: string;
  role: string;
  n: number | null;
  excluded: number | null;
  color: string;
}) {
  return (
    <div className={`rounded-lg border border-ink-600 p-3 ${color}`}>
      <p className="text-xs uppercase tracking-wide text-slate-400">{year}</p>
      <p className="mt-1 text-lg text-slate-100">{role}</p>
      <p className="font-mono text-sm">{displayValue(n, 0)} samples</p>
      <p className="text-xs text-slate-400">Excluded {displayValue(excluded, 0)}</p>
    </div>
  );
}
