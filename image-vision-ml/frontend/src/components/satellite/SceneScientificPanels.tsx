import { useMemo, useState } from "react";
import { Card } from "@/components/common/Card";
import { Metric } from "@/components/common/Metric";
import { QueryState } from "@/components/common/QueryState";
import { StatusBadge } from "@/components/common/StatusBadge";
import { ProvenanceFooter } from "@/components/analysis/ProvenanceFooter";
import { HistogramChart } from "@/components/charts/HistogramChart";
import { useSceneHistograms } from "@/hooks/useSatellite";
import type { HistogramSeries } from "@/types/api";
import { formatNumber, formatPercent } from "@/utils/format";
import { autoZoomUpper, REFLECTANCE_DISPLAY_BINS, samplesOutsideViewport } from "@/utils/histogramZoom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface Props {
  datasetId?: string;
  sceneId?: string;
  overlayReady?: boolean;
}

const CHANNELS = [
  { key: "red", label: "Red B04", color: "#ef4444" },
  { key: "green", label: "Green B03", color: "#22c55e" },
  { key: "blue", label: "Blue B02", color: "#3b82f6" },
] as const;

export function SceneScientificPanels({ datasetId, sceneId, overlayReady }: Props) {
  const histograms = useSceneHistograms(datasetId, sceneId, REFLECTANCE_DISPLAY_BINS);
  const [yMode, setYMode] = useState<"count" | "percent">("count");
  const [channels, setChannels] = useState({ red: true, green: true, blue: true });
  const [rangeMode, setRangeMode] = useState<"auto" | "full">("auto");
  const data = histograms.data;
  const rejected = data?.scientific_use === "rejected_or_review";
  const ndviStats = data?.ndvi.statistics;

  const zoomHigh = useMemo(() => {
    if (rangeMode === "full") return 1;
    return autoZoomUpper(
      CHANNELS
        .filter((item) => channels[item.key])
        .map((item) => data?.reflectance.channels[item.key]?.statistics.p99),
    );
  }, [channels, data, rangeMode]);

  const reflectanceDomain: [number, number] = [0, zoomHigh];

  const outsideByChannel = useMemo(
    () => CHANNELS.map((item) => {
      const series = data?.reflectance.channels[item.key];
      return {
        key: item.key,
        label: item.label,
        ...samplesOutsideViewport(
          series?.histogram,
          zoomHigh,
          series?.in_range_count ?? series?.valid_pixel_count,
        ),
      };
    }),
    [data, zoomHigh],
  );

  const reflectanceSeries = useMemo(
    () => CHANNELS.map((item) => ({
      key: item.key,
      label: item.label,
      color: item.color,
      visible: channels[item.key],
      bins: data?.reflectance.channels[item.key]?.histogram ?? [],
    })),
    [channels, data],
  );

  if (!datasetId || !sceneId) {
    return (
      <Card title="Scene scientific analysis">
        <p className="text-sm text-slate-400">Select a processed scene to compute raster histograms.</p>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {rejected ? (
        <div className="rounded-lg border border-sand-400/50 bg-sand-400/10 p-3 text-sm text-sand-200" role="status">
          <p className="font-medium">Quality warning: this scene is not validated science.</p>
          <p className="mt-1 text-xs">
            Calibration status ({data?.calibration_status ?? "unknown"}) is independent of scene quality
            ({data?.scene_quality_status ?? "unknown"}). Histograms are shown for inspection only.
          </p>
          {data?.warnings?.length ? (
            <ul className="mt-2 list-disc pl-5 text-xs">
              {data.warnings.map((item) => <li key={item}>{item}</li>)}
            </ul>
          ) : null}
        </div>
      ) : null}

      <Card
        title="NDVI histogram"
        actions={(
          <div className="flex gap-1" role="tablist" aria-label="NDVI histogram units">
            {(["count", "percent"] as const).map((item) => (
              <button
                key={item}
                type="button"
                className={`rounded px-2 py-1 text-xs uppercase ${
                  yMode === item ? "bg-moss-600 text-ink-950" : "bg-ink-700"
                }`}
                onClick={() => setYMode(item)}
              >
                {item}
              </button>
            ))}
          </div>
        )}
      >
        <QueryState
          isLoading={histograms.isLoading}
          error={histograms.error}
          onRetry={() => void histograms.refetch()}
          empty={!overlayReady && !data}
          emptyMessage="Processed NDVI and valid-mask rasters are required. Catalog-only scenes have no histogram."
        >
          <HistogramChart
            series={[{
              key: "ndvi",
              label: "NDVI",
              color: "#7dce9a",
              visible: true,
              bins: data?.ndvi.histogram ?? [],
            }]}
            xLabel="NDVI"
            yMode={yMode}
            domain={[-1, 1]}
          />
          <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            <Metric label="Mean" value={formatNumber(ndviStats?.mean, 3)} />
            <Metric label="Median" value={formatNumber(ndviStats?.median, 3)} />
            <Metric label="Std. dev." value={formatNumber(ndviStats?.standard_deviation, 3)} />
            <Metric label="Min / max" value={`${formatNumber(ndviStats?.minimum, 3)} / ${formatNumber(ndviStats?.maximum, 3)}`} />
            <Metric label="P10 / P90" value={`${formatNumber(ndviStats?.p10, 3)} / ${formatNumber(ndviStats?.p90, 3)}`} />
            <Metric label="Valid pixels" value={`${formatNumber(data?.ndvi.valid_pixel_count, 0)} (${formatPercent(data?.ndvi.valid_percentage)})`} />
            <Metric label="Masked / nodata" value={formatNumber(data?.ndvi.masked_or_nodata_count, 0)} />
            <Metric label="Out of [−1, 1]" value={formatNumber(data?.ndvi.out_of_range_count, 0)} />
          </div>
          <ProvenanceFooter
            items={[
              { label: "Source", value: "Sentinel-2 L2A processed NDVI" },
              { label: "Dataset", value: datasetId },
              { label: "Scene", value: sceneId },
              { label: "Date", value: data?.acquisition_date },
              { label: "Units", value: "NDVI, domain −1 to +1" },
              { label: "Grid", value: "AOI 10 m target grid" },
              { label: "Mask", value: "valid_mask.tif; masked pixels excluded, never NDVI 0" },
              { label: "Quality", value: data?.scene_quality_status },
              { label: "Processing", value: data?.processing_version },
              { label: "Histogram version", value: data?.histogram_version },
            ]}
            note="Invalid NDVI is not clamped into [−1, 1]. Display PNG stretch is not used."
          />
        </QueryState>
      </Card>

      <Card
        title="RGB surface reflectance"
        actions={(
          <div className="flex gap-1" role="tablist" aria-label="Reflectance axis range">
            {(["auto", "full"] as const).map((item) => (
              <button
                key={item}
                type="button"
                role="tab"
                aria-selected={rangeMode === item}
                className={`rounded px-2 py-1 text-xs uppercase ${
                  rangeMode === item ? "bg-moss-600 text-ink-950" : "bg-ink-700"
                }`}
                onClick={() => setRangeMode(item)}
              >
                {item === "auto" ? "Auto Zoom" : "Full Range"}
              </button>
            ))}
          </div>
        )}
      >
        <QueryState
          isLoading={histograms.isLoading}
          error={histograms.error}
          onRetry={() => void histograms.refetch()}
          empty={data?.reflectance.available === false}
          emptyMessage="Calibrated B02/B03/B04 rasters are not available for this scene. Tone-mapped RGB preview is not a reflectance histogram."
        >
          <div className="mb-2 flex flex-wrap gap-3 text-xs">
            {CHANNELS.map((item) => (
              <label key={item.key} className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={channels[item.key]}
                  onChange={(event) => setChannels((current) => ({ ...current, [item.key]: event.target.checked }))}
                />
                {item.label}
              </label>
            ))}
          </div>
          <p className="mb-2 text-xs text-slate-400" data-testid="reflectance-axis-range">
            Displayed X-axis: 0.000 to {zoomHigh.toFixed(3)}
            {rangeMode === "auto" ? " (auto zoom from enabled-channel P99)" : " (full scientific domain [0, 1])"}
          </p>
          <HistogramChart
            series={reflectanceSeries}
            xLabel="BOA surface reflectance"
            yMode={yMode}
            domain={reflectanceDomain}
          />
          {rangeMode === "auto" ? (
            <p className="mt-2 text-xs text-slate-400" data-testid="viewport-outside">
              Valid samples outside zoomed viewport:{" "}
              {outsideByChannel
                .filter((item) => channels[item.key as "red" | "green" | "blue"])
                .map((item) => `${item.label} ${item.percent == null ? "—" : `${item.percent.toFixed(1)}%`}`)
                .join(" · ") || "no enabled channels"}
            </p>
          ) : null}
          <div className="mt-3 grid gap-2 lg:grid-cols-3">
            {CHANNELS.map((item) => (
              <ChannelStats key={item.key} label={item.label} series={data?.reflectance.channels[item.key]} />
            ))}
          </div>
          {data?.reflectance.band_count_agreement?.in_range_spread ? (
            <p className="mt-2 text-[11px] text-slate-500">
              {data.reflectance.band_count_agreement.note}
              {" "}Spread {data.reflectance.band_count_agreement.in_range_spread} histogrammed pixels.
            </p>
          ) : null}
          <ProvenanceFooter
            items={[
              { label: "Source", value: "Calibrated B04/B03/B02 reflectance, not 8-bit display RGB" },
              { label: "Scale/offset", value: channelScale(data?.reflectance.channels.red) },
              { label: "Units", value: "dimensionless BOA reflectance 0–1" },
              { label: "Mask", value: "same valid_mask as NDVI; masked never counted as 0" },
              { label: "Bins", value: `${data?.reflectance.channels.red?.bins ?? REFLECTANCE_DISPLAY_BINS} equal-width on [0, 1]; zoom is a viewport, not a rebin` },
              { label: "Statistics", value: "mean/P10/P90/P99 on full in-range samples, not the zoom window" },
            ]}
          />
        </QueryState>
      </Card>

      <Card title="Scene classification (10 m target grid)">
        <QueryState
          isLoading={histograms.isLoading}
          error={histograms.error}
          onRetry={() => void histograms.refetch()}
          empty={!data?.scl}
          emptyMessage="10 m SCL class counts are not available for this scene."
        >
          <div className="h-64 w-full min-w-0" data-testid="scl-chart">
            <ResponsiveContainer>
              <BarChart data={(data?.scl?.classes ?? []).filter((item) => item.count > 0)}>
                <CartesianGrid stroke="#1a3144" strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 10 }} interval={0} angle={-25} textAnchor="end" height={70} />
                <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} />
                <Tooltip contentStyle={{ background: "#122230", border: "1px solid #27445c" }} />
                <Bar dataKey="count" fill="#93c5fd" maxBarSize={18} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {(data?.scl?.groups ?? []).map((item) => (
              <Metric
                key={item.group}
                label={item.group.replaceAll("_", " ")}
                value={`${formatNumber(item.count, 0)} (${formatPercent(item.percent)})`}
              />
            ))}
          </div>
          <p className="mt-2 text-xs text-slate-500">
            Counts are on the 10 m AOI grid. Native 20 m SCL histograms are diagnostic only and are not mixed here.
          </p>
          <div className="mt-2 flex flex-wrap gap-2 text-xs">
            <StatusBadge value={data?.scene_quality_status} label={`scene ${data?.scene_quality_status ?? "unknown"}`} />
            <StatusBadge value={data?.calibration_status} label={`calibration ${data?.calibration_status ?? "unknown"}`} />
          </div>
        </QueryState>
      </Card>
    </div>
  );
}

function ChannelStats({ label, series }: { label: string; series?: HistogramSeries }) {
  const conservation = series?.pixel_conservation_ok;
  return (
    <div className="rounded border border-ink-700 p-2 text-xs" data-testid={`channel-accounting-${label}`}>
      <p className="mb-1 font-medium text-slate-200">{label}</p>
      <p>total {formatNumber(series?.total_pixels, 0)}</p>
      <p>masked {formatNumber(series?.masked_count ?? series?.masked_or_nodata_count, 0)}</p>
      <p>histogrammed {formatNumber(series?.histogrammed_count ?? series?.valid_pixel_count, 0)}</p>
      <p>nonfinite {formatNumber(series?.nonfinite_count ?? series?.nonfinite_unmasked_count, 0)}</p>
      <p>out of domain {formatNumber(series?.out_of_domain_count ?? series?.out_of_range_count, 0)}</p>
      <p>conservation {conservation == null ? "—" : conservation ? "ok" : "fail"}</p>
      <p className="mt-1 text-slate-400">
        mean {formatNumber(series?.statistics.mean, 4)} · P99 {formatNumber(series?.statistics.p99, 4)}
      </p>
      <p>P10/P90 {formatNumber(series?.statistics.p10, 4)}/{formatNumber(series?.statistics.p90, 4)}</p>
    </div>
  );
}

function channelScale(series?: HistogramSeries): string {
  const scale = series?.calibration?.scale;
  const offset = series?.calibration?.offset;
  const source = series?.calibration?.source;
  if (scale == null) return source ? String(source) : "—";
  return `reflectance = DN × ${scale} + ${offset ?? 0}${source ? ` (${source})` : ""}`;
}
