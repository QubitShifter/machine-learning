import { useMemo, useState } from "react";
import { useOutletContext, useSearchParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { QueryState } from "@/components/common/QueryState";
import { FeatureDetails } from "@/components/integration/FeatureDetails";
import { IntegrationOverview } from "@/components/integration/IntegrationOverview";
import { IntegrationScatter } from "@/components/integration/IntegrationScatter";
import { IntegrationTable } from "@/components/integration/IntegrationTable";
import { ObservationSelector } from "@/components/integration/ObservationSelector";
import { PrecipitationWindows } from "@/components/integration/PrecipitationWindows";
import { SelectedObservation } from "@/components/integration/SelectedObservation";
import { WindowCoverage } from "@/components/integration/WindowCoverage";
import { TaskReadiness } from "@/components/quality/TaskReadiness";
import {
  useIntegrationDataset,
  useIntegrationDatasets,
  useIntegrationFeatures,
  useIntegrationObservations,
  useIntegrationQuality,
} from "@/hooks/useIntegration";
import type { ObservationFilter } from "@/types/integration";
import { preferredIntegrationDataset } from "@/utils/format";
import { defaultObservation, type ScatterFeatureId } from "@/utils/integration";

interface Outlet {
  satelliteId?: string;
}

export function IntegrationAnalyticsPage() {
  const { satelliteId } = useOutletContext<Outlet>();
  const [params, setParams] = useSearchParams();
  const [filter, setFilter] = useState<ObservationFilter>("all");
  const [featureId, setFeatureId] = useState<ScatterFeatureId>("precip_prev_7d_mm");
  const listing = useIntegrationDatasets();
  const datasetId = preferredIntegrationDataset(listing.data ?? [], satelliteId);
  const detail = useIntegrationDataset(datasetId);
  const observations = useIntegrationObservations(datasetId);
  const quality = useIntegrationQuality(datasetId);
  const features = useIntegrationFeatures(datasetId);
  const queryClient = useQueryClient();
  const requested = params.get("scene");
  const selection = useMemo(
    () => defaultObservation(observations.data ?? [], requested),
    [observations.data, requested],
  );
  const selected = (observations.data ?? []).find((row) => row.scene_id === selection.sceneId);

  const setScene = (sceneId: string) => {
    const next = new URLSearchParams(params);
    next.set("scene", sceneId);
    setParams(next, { replace: true });
  };

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ["integration"] });
    void listing.refetch();
  };

  const loading = listing.isLoading || detail.isLoading || observations.isLoading;
  const error = listing.error ?? detail.error ?? observations.error ?? quality.error;

  return (
    <div className="space-y-4">
      <header>
        <h2 className="text-lg font-semibold text-slate-100">Satellite + Weather Analytics</h2>
        <p className="text-sm text-slate-400">
          Explore historical weather conditions preceding validated Sentinel-2 observations.
        </p>
        <p className="mt-1 text-xs text-sand-200">
          Exploratory observational analysis. This page does not predict soil moisture or forecast vegetation.
        </p>
      </header>

      <TaskReadiness
        report={quality.data?.task_readiness}
        meaning={quality.data?.suitable_for_modeling_meaning}
      />

      <QueryState
        isLoading={loading && !observations.data}
        error={error}
        onRetry={refresh}
        empty={!loading && !error && (listing.data?.length === 0 || (observations.data?.length ?? 0) === 0)}
        emptyMessage="No integrated satellite–weather observations are available yet. Run the weather integrate command after processing downloaded months."
      >
        <IntegrationOverview
          detail={detail.data}
          quality={quality.data}
          onRefresh={refresh}
          isRefreshing={detail.isFetching || observations.isFetching}
        />
        <ObservationSelector
          observations={observations.data ?? []}
          selectedId={selection.sceneId}
          filter={filter}
          onFilter={setFilter}
          onSelect={setScene}
          invalidRequested={selection.invalidRequested}
          requestedScene={requested}
        />
        {selected ? (
          <>
            <SelectedObservation row={selected} />
            <div className="grid gap-4 xl:grid-cols-[minmax(0,1.4fr)_minmax(18rem,0.8fr)]">
              <PrecipitationWindows row={selected} />
              <WindowCoverage row={selected} rule={detail.data?.window_rule ?? features.data?.window_rule} />
            </div>
            <FeatureDetails row={selected} catalog={features.data?.features} />
          </>
        ) : null}
        <IntegrationScatter
          observations={observations.data ?? []}
          featureId={featureId}
          onFeatureId={setFeatureId}
          selectedId={selection.sceneId}
          onSelect={setScene}
          catalog={features.data?.features}
        />
        <IntegrationTable
          observations={observations.data ?? []}
          selectedId={selection.sceneId}
          onSelect={setScene}
        />
      </QueryState>
    </div>
  );
}
