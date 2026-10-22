import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Link, useOutletContext, useSearchParams } from "react-router-dom";
import { Card } from "@/components/common/Card";
import { QueryState } from "@/components/common/QueryState";
import { StatusBadge } from "@/components/common/StatusBadge";
import { SeriesChart } from "@/components/charts/SeriesChart";
import { SatelliteMap } from "@/components/maps/SatelliteMap";
import { NdviLegend } from "@/components/satellite/NdviLegend";
import { InspectorSection } from "@/components/satellite/InspectorSection";
import { PixelInspector } from "@/components/satellite/PixelInspector";
import { SceneScientificPanels } from "@/components/satellite/SceneScientificPanels";
import { SclLegend } from "@/components/satellite/SclLegend";
import { usePersistedBoolean } from "@/hooks/usePersistedBoolean";
import { PlannedModules } from "@/components/analysis/PlannedModules";
import {
  useSatelliteDataset,
  useSatelliteDatasets,
  useSatelliteScenes,
  useSatelliteTimeseries,
  inspectPixelAt,
  useSceneMapMetadata,
  useSceneQuality,
} from "@/hooks/useSatellite";
import { useAoiRegistry } from "@/hooks/useAoi";
import { useIntegrationDatasets, useIntegrationObservations } from "@/hooks/useIntegration";
import { preferredIntegrationDataset } from "@/utils/format";
import { sceneMapNdviUrl, sceneMapRgbUrl, sceneMapSclUrl } from "@/services/api";
import type { PixelInspect, SatelliteSceneRecord } from "@/types/api";
import { formatNumber, formatPercent } from "@/utils/format";

interface Outlet {
  satelliteId?: string;
}

export function SatelliteExplorerPage() {
  const { satelliteId: defaultId } = useOutletContext<Outlet>();
  const [params, setParams] = useSearchParams();
  const datasets = useSatelliteDatasets();
  const [datasetId, setDatasetId] = useState<string | undefined>(defaultId);
  const activeId = datasetId ?? defaultId;
  const dataset = useSatelliteDataset(activeId);
  const scenes = useSatelliteScenes(activeId);
  const series = useSatelliteTimeseries(activeId);
  const catalog = params.get("catalog") === "1";
  const requestedScene = params.get("scene") ?? undefined;
  const requestedMode = parseMode(params.get("mode"));
  const [query, setQuery] = useState("");
  const [opacity, setOpacity] = useState(0.85);
  const [showAoi, setShowAoi] = useState(true);
  const [sample, setSample] = useState<PixelInspect | null>(null);
  const [pendingClick, setPendingClick] = useState<{ longitude: number; latitude: number } | null>(null);
  const [inspecting, setInspecting] = useState(false);
  const [inspectorCollapsed, setInspectorCollapsed] = usePersistedBoolean("explorer.inspectorCollapsed", false);
  const [sceneInfoOpen, setSceneInfoOpen] = usePersistedBoolean("explorer.sceneInfoOpen", false);
  const [legendOpen, setLegendOpen] = usePersistedBoolean("explorer.legendOpen", true);
  const [pixelOpen, setPixelOpen] = usePersistedBoolean("explorer.pixelOpen", true);
  const inspectorRef = useRef<HTMLElement | null>(null);
  const inspectRequest = useRef(0);
  const aoiRegistry = useAoiRegistry();

  const processed = useMemo(
    () => (scenes.data ?? []).filter((item) => item.status === "processed" || item.overlay_ready),
    [scenes.data],
  );
  const visible = useMemo(() => {
    const source = catalog ? scenes.data ?? [] : processed;
    const filtered = source.filter((item) => sceneLabel(item).toLowerCase().includes(query.toLowerCase()));
    const ordered = [...filtered].sort((a, b) => String(b.acquisition_date).localeCompare(String(a.acquisition_date)));
    if (requestedScene) {
      const selected = (scenes.data ?? []).find((item) => item.scene_id === requestedScene);
      if (selected && !ordered.some((item) => item.scene_id === selected.scene_id)) {
        ordered.unshift(selected);
      }
    }
    return ordered;
  }, [catalog, processed, query, requestedScene, scenes.data]);

  const defaultScene = processed
    .filter((item) => item.overlay_ready)
    .sort((a, b) => String(b.acquisition_date).localeCompare(String(a.acquisition_date)))[0]
    ?? processed[0];
  const activeSceneId = requestedScene && (scenes.data ?? []).some((item) => item.scene_id === requestedScene)
    ? requestedScene
    : defaultScene?.scene_id;
  const scene = (scenes.data ?? []).find((item) => item.scene_id === activeSceneId);
  const quality = useSceneQuality(activeId, activeSceneId);
  const overlay = useSceneMapMetadata(activeId, activeSceneId);
  const integrationList = useIntegrationDatasets();
  const integrationId = preferredIntegrationDataset(integrationList.data ?? [], activeId);
  const integrated = useIntegrationObservations(integrationId);
  const hasWeatherContext = Boolean(
    activeSceneId && (integrated.data ?? []).some((row) => row.scene_id === activeSceneId),
  );
  const mode = overlay.data?.supported_modes.includes(requestedMode)
    ? requestedMode
    : overlayFallback(overlay.data?.supported_modes);
  const overlayUrl = activeId && activeSceneId && overlay.data?.overlay_available
    ? overlayImageUrl(mode, activeId, activeSceneId, overlay.data.cache_id)
    : null;

  useEffect(() => {
    setSample(null);
    setPendingClick(null);
    setInspecting(false);
  }, [activeSceneId]);

  const inspectLocation = async (longitude: number, latitude: number) => {
    if (!activeId || !activeSceneId) return;
    const requestId = inspectRequest.current + 1;
    inspectRequest.current = requestId;
    setPendingClick({ longitude, latitude });
    setInspecting(true);
    setPixelOpen(true);
    scrollInspectorToTop(inspectorRef.current);
    try {
      const result = await inspectPixelAt(activeId, activeSceneId, longitude, latitude);
      if (inspectRequest.current !== requestId) return;
      setSample(result);
    } catch (error) {
      if (inspectRequest.current !== requestId) return;
      setSample({
        scene_id: activeSceneId,
        acquisition_date: scene?.acquisition_date ?? null,
        longitude,
        latitude,
        crs: "EPSG:4326",
        coverage_state: "out_of_coverage",
        inside_raster: false,
        valid: false,
        row: null,
        col: null,
        sampling: "nearest_10m_target_grid",
        red_b04: null,
        green_b03: null,
        blue_b02: null,
        nir_b08: null,
        ndvi: null,
        scl_class: null,
        scl_class_name: null,
        valid_mask: null,
        exclusion_reason: null,
        calibration_status: quality.data?.calibration_status ?? null,
        scene_quality_status: quality.data?.scene_quality_status ?? quality.data?.quality_status ?? null,
        missing_reasons: { coverage: "request_failed" },
        message: error instanceof Error ? error.message : "Pixel inspect failed",
        source: "processed_rasters",
        estimated_from_display_rgb: false,
      });
    } finally {
      if (inspectRequest.current === requestId) setInspecting(false);
    }
  };

  const setScene = (sceneId: string) => {
    params.set("scene", sceneId);
    setParams(params, { replace: true });
  };
  const setMode = (next: "rgb" | "ndvi" | "scl") => {
    params.set("mode", next);
    setParams(params, { replace: true });
  };

  return (
    <div className="space-y-4">
      <Card title="Scene selector">
        <QueryState
          isLoading={datasets.isLoading || scenes.isLoading}
          error={datasets.error ?? scenes.error}
          onRetry={() => {
            void datasets.refetch();
            void scenes.refetch();
          }}
          empty={!visible.length && !scenes.isLoading}
          emptyMessage={catalog ? "No discovered scenes match this filter." : "No validated overlay-ready scenes are available."}
        >
          <div className="grid gap-3 lg:grid-cols-4">
            <label className="text-sm text-slate-300">
              Dataset
              <select
                className="mt-1 w-full rounded border border-ink-600 bg-ink-800 px-2 py-1"
                value={activeId ?? ""}
                onChange={(event) => {
                  setDatasetId(event.target.value);
                  params.delete("scene");
                  setParams(params, { replace: true });
                }}
              >
                {(datasets.data ?? []).map((item) => (
                  <option key={item.dataset_id} value={item.dataset_id}>
                    {item.dataset_id}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm text-slate-300" htmlFor="scene-select">
              Acquisition
              <select
                id="scene-select"
                className="mt-1 w-full rounded border border-ink-600 bg-ink-800 px-2 py-1 font-mono text-xs"
                value={activeSceneId ?? ""}
                onChange={(event) => setScene(event.target.value)}
              >
                {visible.map((item) => (
                  <option key={item.scene_id} value={item.scene_id}>
                    {sceneLabel(item)}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm text-slate-300">
              Filter
              <input
                className="mt-1 w-full rounded border border-ink-600 bg-ink-800 px-2 py-1"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Date, platform, or scene ID"
              />
            </label>
            <label className="flex items-end gap-2 text-sm text-slate-300">
              <input
                type="checkbox"
                checked={catalog}
                onChange={(event) => {
                  if (event.target.checked) params.set("catalog", "1");
                  else params.delete("catalog");
                  setParams(params, { replace: true });
                }}
              />
              All discovered scenes
            </label>
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-400">
            <StatusBadge value={quality.data?.quality_status ?? scene?.status} />
            <span>cloud {formatPercent(quality.data?.cloud_shadow_fraction_pct ?? scene?.cloud_cover)}</span>
            {scene && !scene.overlay_ready ? (
              <span role="status">Catalog/unprocessed scene: overlay unavailable</span>
            ) : null}
          </div>
        </QueryState>
      </Card>

      <div
        data-testid="satellite-workspace"
        className={`satellite-workspace ${inspectorCollapsed ? "is-inspector-collapsed" : ""}`}
      >
        <section className="satellite-map-panel flex min-h-0 flex-col rounded-xl border border-ink-600/70 bg-ink-900/80 p-3">
          <header className="mb-3 flex flex-wrap items-start justify-between gap-2">
            <h2 className="text-sm font-semibold tracking-wide text-slate-200">Georeferenced scene map</h2>
            <div className="flex flex-wrap items-center gap-2">
              <div className="flex gap-1" role="tablist" aria-label="Visualization mode">
                {(["ndvi", "rgb", "scl"] as const).map((item) => (
                  <button
                    key={item}
                    type="button"
                    role="tab"
                    aria-selected={mode === item}
                    className={`rounded px-2 py-1 text-xs uppercase ${
                      mode === item ? "bg-moss-600 text-ink-950" : "bg-ink-700 text-slate-300"
                    }`}
                    onClick={() => setMode(item)}
                    disabled={Boolean(overlay.data && !overlay.data.supported_modes.includes(item))}
                  >
                    {item}
                  </button>
                ))}
              </div>
              <label className="flex items-center gap-2 text-xs text-slate-300">
                Opacity
                <input
                  aria-label="Overlay opacity"
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  value={opacity}
                  onChange={(event) => setOpacity(Number(event.target.value))}
                />
              </label>
              <label className="flex items-center gap-2 text-xs text-slate-300">
                <input type="checkbox" checked={showAoi} onChange={(event) => setShowAoi(event.target.checked)} />
                AOI outline
              </label>
              <button
                type="button"
                className="rounded border border-ink-600 px-2 py-1 text-xs"
                aria-expanded={!inspectorCollapsed}
                aria-controls="satellite-inspector"
                onClick={() => setInspectorCollapsed((current) => !current)}
              >
                {inspectorCollapsed ? "Show inspector" : "Hide inspector"}
              </button>
            </div>
          </header>
          <div className="satellite-map-viewport">
            <SatelliteMap
              bbox={dataset.data?.bbox}
              metadata={overlay.data}
              overlayUrl={overlayUrl}
              mode={mode}
              opacity={opacity}
              showAoi={showAoi}
              overlayAvailable={Boolean(overlay.data?.overlay_available)}
              overlayError={overlay.error?.message}
              isLoading={overlay.isLoading}
              fillParent
              selectedPoint={sample ?? pendingClick}
              onInspect={(longitude, latitude) => {
                void inspectLocation(longitude, latitude);
              }}
            />
          </div>
        </section>

        {inspectorCollapsed ? null : (
          <aside
            id="satellite-inspector"
            ref={inspectorRef}
            data-testid="satellite-inspector"
            className="satellite-inspector-panel space-y-3"
          >
            <div className="rounded-lg border border-ink-600/70 bg-ink-900/80 px-3 py-2">
              {hasWeatherContext && activeSceneId ? (
                <Link
                  className="inline-flex rounded border border-moss-600/40 px-2 py-1 text-xs text-moss-300 hover:bg-ink-700"
                  to={`/integration?scene=${encodeURIComponent(activeSceneId)}`}
                >
                  View weather context
                </Link>
              ) : (
                <p className="text-xs text-slate-500" role="status">
                  Weather context unavailable for this scene.
                </p>
              )}
            </div>
            <InspectorSection
              id="pixel-inspector-panel"
              title="Pixel inspector"
              open={pixelOpen}
              onToggle={() => setPixelOpen((current) => !current)}
              summary={sample
                ? `${sample.longitude.toFixed(4)}°E, ${sample.latitude.toFixed(4)}°N · ${sample.valid ? "valid" : sample.coverage_state}`
                : "Click the map to sample a raster pixel"}
            >
              <PixelInspector sample={sample} loading={inspecting} pending={pendingClick} />
            </InspectorSection>

            <InspectorSection
              id="scene-information-panel"
              title="Scene information"
              open={sceneInfoOpen}
              onToggle={() => setSceneInfoOpen((current) => !current)}
              summary={(
                <>
                  {[
                    quality.data?.acquisition_date ?? scene?.acquisition_date,
                    activeSceneId,
                    quality.data?.scene_quality_status ?? quality.data?.quality_status ?? scene?.status,
                    `cal ${quality.data?.calibration_status
                      ?? (quality.data?.calibration?.validation_status as string | undefined)
                      ?? "unknown"}`,
                  ].filter(Boolean).join(" · ")}
                  {quality.data?.scene_quality_status === "rejected"
                    || quality.data?.quality_status === "rejected"
                    || quality.data?.scene_quality_status === "requires_review" ? (
                    <span className="mt-1 block text-sand-300">Not validated science — quality status is visible while collapsed.</span>
                  ) : null}
                </>
              )}
            >
              <QueryState
                isLoading={quality.isLoading}
                error={quality.error}
                onRetry={() => void quality.refetch()}
                empty={!quality.data && !scene}
              >
                <MetadataGroup title="Acquisition">
                  <Row label="Date" value={quality.data?.acquisition_date ?? scene?.acquisition_date} />
                  <Row label="Platform" value={quality.data?.satellite_platform ?? scene?.platform} />
                  <CopyRow label="Scene ID" value={activeSceneId} />
                  <Row label="Collection" value={dataset.data?.collection} />
                </MetadataGroup>
                <MetadataGroup title="Vegetation">
                  <Row label="NDVI min" value={formatNumber(quality.data?.ndvi_minimum)} />
                  <Row label="NDVI mean" value={formatNumber(quality.data?.ndvi_mean)} />
                  <Row label="NDVI max" value={formatNumber(quality.data?.ndvi_maximum)} />
                </MetadataGroup>
                <MetadataGroup title="Quality">
                  <Row label="Valid pixels" value={formatPercent(quality.data?.valid_ndvi_pct ?? scene?.valid_percentage)} />
                  <Row label="AOI coverage" value={formatPercent(quality.data?.actual_aoi_coverage_pct ?? scene?.aoi_coverage)} />
                  <Row label="Cloud / shadow" value={formatPercent(quality.data?.cloud_shadow_fraction_pct ?? scene?.cloud_cover)} />
                  <Row
                    label="Scene quality"
                    value={quality.data?.scene_quality_status ?? quality.data?.quality_status ?? scene?.status}
                  />
                  <Row
                    label="Calibration"
                    value={quality.data?.calibration_status
                      ?? (quality.data?.calibration?.validation_status as string | undefined)
                      ?? "—"}
                  />
                  {quality.data?.scene_quality_reasons?.length || quality.data?.reasons?.length ? (
                    <p className="text-xs text-slate-400">
                      {(quality.data.scene_quality_reasons?.length
                        ? quality.data.scene_quality_reasons
                        : quality.data.reasons).join(", ")}
                    </p>
                  ) : null}
                </MetadataGroup>
                <MetadataGroup title="Geometry">
                  <Row label="Native CRS" value={overlay.data?.native_crs ?? dataset.data?.target_grid?.crs} />
                  <Row
                    label="Pixel size"
                    value={overlay.data?.native_pixel_size_m
                      ? `${overlay.data.native_pixel_size_m.join(" × ")} m`
                      : dataset.data?.target_grid?.resolution
                        ? `${dataset.data.target_grid.resolution.join(" × ")} m`
                        : "—"}
                  />
                  <Row
                    label="Raster size"
                    value={overlay.data?.native_width
                      ? `${overlay.data.native_width} × ${overlay.data.native_height} px`
                      : "—"}
                  />
                  <Row
                    label="Footprint WGS84"
                    value={overlay.data?.geographic_extent
                      ? `${overlay.data.geographic_extent.west?.toFixed(5)}, ${overlay.data.geographic_extent.south?.toFixed(5)}, ${overlay.data.geographic_extent.east?.toFixed(5)}, ${overlay.data.geographic_extent.north?.toFixed(5)}`
                      : "—"}
                  />
                  <Row
                    label="Overlay render"
                    value={overlay.data?.rendered_width
                      ? `${overlay.data.rendered_width} × ${overlay.data.rendered_height} ${overlay.data.rendered_crs}`
                      : "—"}
                  />
                </MetadataGroup>
              </QueryState>
            </InspectorSection>

            <InspectorSection
              id="classification-legend-panel"
              title={mode === "scl" ? "SCL classes" : mode === "ndvi" ? "NDVI color scale" : "Classification"}
              open={legendOpen}
              onToggle={() => setLegendOpen((current) => !current)}
              summary={`${mode.toUpperCase()} overlay · ${mode === "scl" ? "categorical 10 m nearest-neighbor classes" : mode === "ndvi" ? "fixed −1 to 1 display scale" : "RGB is surface reflectance, not SCL"}`}
            >
              {mode === "ndvi" ? <NdviLegend scale={overlay.data?.ndvi_color_scale ?? []} /> : null}
              {mode === "scl" ? (
                <SclLegend legend={overlay.data?.scl_legend} provenance={overlay.data?.scl_provenance} />
              ) : null}
              {mode === "rgb" ? (
                <p className="text-xs text-slate-400">
                  RGB overlay is calibrated B04/B03/B02 reflectance for display. Switch to SCL for class colors.
                </p>
              ) : null}
            </InspectorSection>

            <section className="rounded-lg border border-ink-600/70 bg-ink-900/80 p-3">
              <h2 className="text-sm font-semibold tracking-wide text-slate-200">Study areas</h2>
              <p className="mt-1 text-xs text-slate-400">
                Operational datasets stay linked to existing imagery. Draft geometries are proposals only.
              </p>
              <ul className="mt-2 space-y-1 text-xs">
                {(aoiRegistry.data?.areas ?? []).map((item) => (
                  <li key={item.aoi_id} className="flex justify-between gap-2">
                    <span>{item.name}</span>
                    <span className="font-mono text-slate-500">{item.status}</span>
                  </li>
                ))}
              </ul>
              <Link className="mt-2 inline-flex text-xs text-moss-300 underline" to="/aoi">
                Propose another study area
              </Link>
            </section>
          </aside>
        )}
      </div>

      <Card title="Historical NDVI">
        <QueryState
          isLoading={series.isLoading}
          error={series.error}
          onRetry={() => void series.refetch()}
          empty={!series.data?.length}
          emptyMessage="No validated NDVI acquisitions are available."
        >
          <SeriesChart
            kind="scatter"
            unit="NDVI"
            color="#7dce9a"
            onPointClick={setScene}
            data={(series.data ?? []).map((item) => ({
              date: item.date ?? "",
              value: item.mean,
              extra: `${item.scene_id ?? ""} · ${qualityStatus(item.scene_id, scenes.data)}`,
              id: item.scene_id ?? undefined,
              selected: item.scene_id === activeSceneId,
            }))}
          />
          <p className="mt-2 text-xs text-slate-500">
            Points are individual Sentinel-2 acquisitions. Click a point to select that scene. Long gaps are not connected.
          </p>
        </QueryState>
      </Card>

      <SceneScientificPanels
        datasetId={activeId}
        sceneId={activeSceneId}
        overlayReady={Boolean(scene?.overlay_ready)}
      />
      <PlannedModules />
    </div>
  );
}

function scrollInspectorToTop(node: HTMLElement | null) {
  if (!node) return;
  if (typeof node.scrollTo === "function") {
    node.scrollTo({ top: 0 });
    return;
  }
  node.scrollTop = 0;
}

function parseMode(value: string | null): "rgb" | "ndvi" | "scl" {
  if (value === "rgb" || value === "scl") return value;
  return "ndvi";
}

function overlayFallback(modes?: string[]): "rgb" | "ndvi" | "scl" {
  if (modes?.includes("ndvi")) return "ndvi";
  if (modes?.includes("rgb")) return "rgb";
  if (modes?.includes("scl")) return "scl";
  return "ndvi";
}

function overlayImageUrl(
  mode: "rgb" | "ndvi" | "scl",
  datasetId: string,
  sceneId: string,
  cacheId?: string | null,
): string {
  if (mode === "rgb") return sceneMapRgbUrl(datasetId, sceneId, cacheId);
  if (mode === "scl") return sceneMapSclUrl(datasetId, sceneId, cacheId);
  return sceneMapNdviUrl(datasetId, sceneId, cacheId);
}

function sceneLabel(scene: SatelliteSceneRecord): string {
  return [
    scene.acquisition_date ?? "unknown date",
    scene.platform ?? "Sentinel-2",
    scene.status ?? "unknown",
    scene.scene_id,
  ].join(" · ");
}

function qualityStatus(sceneId: string | null, scenes?: SatelliteSceneRecord[]): string {
  return scenes?.find((item) => item.scene_id === sceneId)?.status ?? "unknown";
}

function MetadataGroup({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mb-3">
      <h3 className="mb-1 text-[11px] uppercase tracking-wide text-slate-500">{title}</h3>
      <dl className="space-y-1">{children}</dl>
    </section>
  );
}

function Row({ label, value }: { label: string; value?: string | number | null }) {
  return (
    <div className="flex justify-between gap-3 text-xs">
      <dt className="text-slate-400">{label}</dt>
      <dd className="text-right text-slate-200">{value ?? "—"}</dd>
    </div>
  );
}

function CopyRow({ label, value }: { label: string; value?: string }) {
  return (
    <div className="flex items-center justify-between gap-3 text-xs">
      <dt className="text-slate-400">{label}</dt>
      <dd>
        <button
          type="button"
          className="font-mono text-slate-200 underline-offset-2 hover:underline"
          onClick={() => {
            if (value) void navigator.clipboard?.writeText(value);
          }}
        >
          {value ?? "—"}
        </button>
      </dd>
    </div>
  );
}
