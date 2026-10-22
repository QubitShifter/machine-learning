import { Card } from "@/components/common/Card";
import { Metric } from "@/components/common/Metric";
import { StatusBadge } from "@/components/common/StatusBadge";
import type { IntegrationDatasetDetail, IntegrationQuality } from "@/types/integration";
import { formatNumber, formatUtcTimestamp } from "@/utils/format";

interface Props {
  detail?: IntegrationDatasetDetail;
  quality?: IntegrationQuality;
  onRefresh: () => void;
  isRefreshing: boolean;
}

export function IntegrationOverview({ detail, quality, onRefresh, isRefreshing }: Props) {
  const observationCount = detail?.observation_count ?? quality?.observation_count ?? 0;
  const complete = detail?.weather_feature_window_complete_count
    ?? quality?.weather_feature_window_complete_count
    ?? 0;
  const incomplete = Math.max(observationCount - complete, 0);
  const modeling = detail?.suitable_for_modeling_count
    ?? quality?.suitable_for_modeling_count
    ?? 0;

  return (
    <Card
      title="Integration overview"
      actions={(
        <button
          type="button"
          className="rounded border border-ink-600 px-2 py-1 text-xs text-slate-300 hover:bg-ink-700"
          onClick={onRefresh}
          disabled={isRefreshing}
        >
          {isRefreshing ? "Refreshing…" : "Refresh"}
        </button>
      )}
    >
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <Metric label="Integrated observations" value={formatNumber(observationCount, 0)} />
        <Metric label="Complete integrations" value={formatNumber(complete, 0)} hint="All 7/14/30-day windows present" />
        <Metric label="Incomplete integrations" value={formatNumber(incomplete, 0)} hint="Valid scenes kept with missing weather" />
        <Metric
          label="Modeling-ready observations"
          value={formatNumber(modeling, 0)}
          hint="Supervised soil-forecasting eligibility only"
        />
        <Metric
          label="Integration version"
          value={detail?.integration_version ?? quality?.integration_version ?? "—"}
        />
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-400">
        <StatusBadge value={detail?.weather_integration_readiness} />
        <StatusBadge
          value={detail?.satellite_supervised_soil_forecasting}
          label={detail?.satellite_supervised_soil_forecasting ?? "soil forecasting unknown"}
        />
        <span>Generated {formatUtcTimestamp(detail?.updated_at ?? quality?.updated_at)}</span>
      </div>
      <p className="mt-2 text-xs text-slate-500">
        Modeling-ready observations count supervised soil-forecasting eligibility
        (`suitable_for_modeling`), not exploratory NDVI or vegetation forecasting.
        Soil-moisture ground-truth labels are not available. A modeling-ready count of zero is a scientific
        limitation, not an application failure. New ERA5-Land months appear here only after the integration
        command is rerun.
      </p>
    </Card>
  );
}
