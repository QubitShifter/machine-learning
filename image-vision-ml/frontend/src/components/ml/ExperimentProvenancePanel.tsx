import { Card } from "@/components/common/Card";
import { Metric } from "@/components/common/Metric";
import { StatusBadge } from "@/components/common/StatusBadge";
import { ProvenanceFooter } from "@/components/analysis/ProvenanceFooter";
import type { ExperimentProvenance } from "@/types/ml";

interface Props {
  provenance: ExperimentProvenance;
}

export function ExperimentProvenancePanel({ provenance }: Props) {
  return (
    <Card title="Reproducibility">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <Metric label="Experiment ID" value={provenance.experiment_id} />
        <Metric label="Dataset ID" value={provenance.dataset_id ?? "Unavailable"} />
        <Metric label="Dataset version" value={provenance.dataset_version ?? "Unavailable"} />
        <Metric label="Pipeline" value={provenance.pipeline_version ?? "Unavailable"} />
        <Metric label="Config fingerprint" value={shorten(provenance.config_fingerprint)} />
        <Metric label="Features SHA-256" value={shorten(provenance.features_daily_sha256)} />
        <Metric label="Frozen at" value={provenance.frozen_at_utc ?? "Unavailable"} />
        <Metric label="Test evaluated at" value={provenance.test_evaluated_at_utc ?? "Unavailable"} />
        <Metric label="Git revision" value={provenance.git_revision ?? "Unavailable"} />
        <Metric label="Git dirty" value={provenance.git_dirty == null ? "Unavailable" : String(provenance.git_dirty)} />
        <Metric label="Python" value={provenance.python_version ?? "Unavailable"} />
        <Metric label="scikit-learn" value={provenance.package_versions["scikit-learn"] ?? "Unavailable"} />
        <Metric label="Random seed" value={provenance.random_seed == null ? "Unavailable" : String(provenance.random_seed)} />
        <Metric label="Research mode" value={provenance.research_mode} />
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <StatusBadge value="not_ready" label="operational_forecast=false" />
        <StatusBadge value="not_ready" label="operational_availability_verified=false" />
        <StatusBadge value="not_ready" label="is_ground_truth=false" />
        <StatusBadge value="not_ready" label="suitable_for_modeling=false" />
      </div>
      <p className="mt-3 text-sm text-sand-200">
        Trained research models do not change scientific eligibility flags. {provenance.label}
      </p>
      <ProvenanceFooter
        items={[
          { label: "training_events.jsonl", value: provenance.training_events_present ? "present" : "absent" },
          { label: "test repeat", value: provenance.test_repeat == null ? "n/a" : String(provenance.test_repeat) },
          { label: "target kind", value: provenance.target_source_kind },
        ]}
        note="Local filesystem paths and environment variables are not included in this panel."
      />
    </Card>
  );
}

function shorten(value: string | null): string {
  if (!value) return "Unavailable";
  return value.length > 20 ? `${value.slice(0, 14)}…` : value;
}
