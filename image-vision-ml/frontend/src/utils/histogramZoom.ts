import type { HistogramBin } from "@/types/api";

export const AUTO_ZOOM_PADDING = 0.15;
export const AUTO_ZOOM_FLOOR = 0.05;
export const AUTO_ZOOM_CAP = 1;
export const REFLECTANCE_DISPLAY_BINS = 100;

export function autoZoomUpper(
  p99Values: Array<number | null | undefined>,
  padding = AUTO_ZOOM_PADDING,
): number {
  const peaks = p99Values.filter((value): value is number => value != null && Number.isFinite(value));
  if (!peaks.length) return AUTO_ZOOM_CAP;
  return Math.min(AUTO_ZOOM_CAP, Math.max(AUTO_ZOOM_FLOOR, Math.max(...peaks) * (1 + padding)));
}

export function samplesOutsideViewport(
  bins: HistogramBin[] | undefined,
  zoomHigh: number,
  inRangeCount: number | undefined,
): { outsideCount: number; percent: number | null } {
  const histogram = bins ?? [];
  const outsideCount = histogram
    .filter((bin) => bin.edge_left >= zoomHigh)
    .reduce((sum, bin) => sum + bin.count, 0);
  const total = inRangeCount ?? 0;
  return {
    outsideCount,
    percent: total === 0 ? null : (100 * outsideCount) / total,
  };
}

export function binsOverlappingDomain(
  bins: HistogramBin[] | undefined,
  domain: [number, number],
): HistogramBin[] {
  const [low, high] = domain;
  return (bins ?? []).filter((bin) => bin.edge_right > low && bin.edge_left < high);
}
