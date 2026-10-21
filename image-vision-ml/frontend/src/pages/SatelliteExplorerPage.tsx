import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Link, useOutletContext, useSearchParams } from "react-router-dom";
import { Card } from "@/components/common/Card";
import { QueryState } from "@/components/common/QueryState";
import { StatusBadge } from "@/components/common/StatusBadge";
import { SeriesChart } from "@/components/charts/SeriesChart";
import { SatelliteMap } from "@/components/maps/SatelliteMap";
import { NdviLegend } from "@/components/satellite/NdviLegend";
import {
  useSatelliteDataset,
  useSatelliteDatasets,
  useSatelliteScenes,
  useSatelliteTimeseries,
  useSceneMapMetadata,
  useSceneQuality,
  sampleNdviAt,
} from "@/hooks/useSatellite";
import { useIntegrationDatasets, useIntegrationObservations } from "@/hooks/useIntegration";
import { preferredIntegrationDataset } from "@/utils/format";
import { sceneMapNdviUrl, sceneMapRgbUrl } from "@/services/api";
import type { NdviSample, SatelliteSceneRecord } from "@/types/api";
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
  const requestedMode = params.get("mode") === "rgb" ? "rgb" : "ndvi";
  const [query, setQuery] = useState("");
  const [opacity, setOpacity] = useState(0.85);
  const [showAoi, setShowAoi] = useState(true);
  const [sample, setSample] = useState<NdviSample | null>(null);

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
    : overlay.data?.supported_modes[0] === "rgb" ? "rgb" : "ndvi";
  const overlayUrl = activeId && activeSceneId && overlay.data?.overlay_available
    ? mode === "rgb"
      ? sceneMapRgbUrl(activeId, activeSceneId, overlay.data.cache_id)
      : sceneMapNdviUrl(activeId, activeSceneId, overlay.data.cache_id)
    : null;

  useEffect(() => {
    setSample(null);
  }, [activeSceneId, mode]);

  const setScene = (sceneId: string) => {
    params.set("scene", sceneId);
    setParams(params, { replace: true });
  };
  const setMode = (next: "rgb" | "ndvi") => {
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

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_20rem]">
        <Card
          title="Georeferenced scene map"
          actions={(
            <div className="flex flex-wrap items-center gap-2">
              <div className="flex gap-1" role="tablist" aria-label="Visualization mode">
                {(["ndvi", "rgb"] as const).map((item) => (
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
            </div>
          )}
        >
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
            onInspect={async (longitude, latitude) => {
              if (!activeId || !activeSceneId || mode !== "ndvi") return;
              try {
                setSample(await sampleNdviAt(activeId, activeSceneId, longitude, latitude));
              } catch (error) {
                setSample({
                  scene_id: activeSceneId,
                  longitude,
                  latitude,
                  crs: "EPSG:4326",
                  inside_raster: false,
                  valid: false,
                  ndvi: null,
                  sampling: "nearest",
                  message: error instanceof Error ? error.message : "Sample failed",
                });
              }
            }}
          />
        </Card>

        <div className="space-y-4">
          <Card title="Scene information">
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
                <div className="pt-2">
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
                <Row label="Status" value={quality.data?.quality_status ?? scene?.status} />
                {quality.data?.reasons?.length ? (
                  <p className="text-xs text-slate-400">{quality.data.reasons.join(", ")}</p>
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
          </Card>
          {mode === "ndvi" ? <NdviLegend scale={overlay.data?.ndvi_color_scale ?? []} /> : null}
          {sample ? (
            <Card title="Pixel sample">
              <p className="font-mono text-xs">
                {sample.longitude.toFixed(5)}°E, {sample.latitude.toFixed(5)}°N
              </p>
              <p className="mt-1 text-sm">
                {sample.valid ? `NDVI ${formatNumber(sample.ndvi)}` : sample.message ?? "Invalid or outside raster"}
              </p>
              <p className="mt-1 text-[11px] text-slate-500">Nearest processed NDVI pixel. Not inferred from the PNG color.</p>
            </Card>
          ) : null}
        </div>
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
    </div>
  );
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
