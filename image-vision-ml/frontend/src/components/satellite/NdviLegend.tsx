import type { MapOverlayMetadata } from "@/types/api";

interface Props {
  scale: MapOverlayMetadata["ndvi_color_scale"];
}

export function NdviLegend({ scale }: Props) {
  if (!scale.length) return null;
  const gradient = scale
    .map((stop) => `rgb(${stop.color_rgb.join(",")})`)
    .join(", ");
  return (
    <div data-testid="ndvi-legend" className="rounded-lg border border-ink-600 bg-ink-800/70 p-3">
      <p className="text-xs uppercase tracking-wide text-slate-400">NDVI color scale</p>
      <div
        className="mt-2 h-3 rounded"
        style={{ background: `linear-gradient(to right, ${gradient})` }}
        aria-hidden
      />
      <div className="mt-1 flex justify-between font-mono text-[10px] text-slate-400">
        {scale.filter((item) => [-1, 0, 0.5, 1].includes(item.value)).map((item) => (
          <span key={item.value}>{item.value.toFixed(1)}</span>
        ))}
      </div>
      <p className="mt-2 text-[11px] text-slate-500">
        Fixed display scale from −1 to 1. Colors are not scene-normalized.
      </p>
    </div>
  );
}
