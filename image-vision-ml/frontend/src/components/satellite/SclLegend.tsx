import type { MapOverlayMetadata } from "@/types/api";

interface Props {
  legend?: MapOverlayMetadata["scl_legend"];
  provenance?: MapOverlayMetadata["scl_provenance"];
}

export function SclLegend({ legend, provenance }: Props) {
  if (!legend?.length) return null;
  return (
    <div data-testid="scl-legend" className="rounded-lg border border-ink-600 bg-ink-800/70 p-3">
      <p className="text-xs uppercase tracking-wide text-slate-400">SCL classes</p>
      <ul className="mt-2 grid grid-cols-1 gap-1 text-[11px] text-slate-300">
        {legend.map((item) => (
          <li key={item.code} className="flex items-center gap-2">
            <span
              className="inline-block h-3 w-3 rounded-sm border border-ink-500"
              style={{ background: `rgb(${item.color_rgb.join(",")})` }}
              aria-hidden
            />
            <span>{item.code} · {item.name}{item.transparent ? " (transparent)" : ""}</span>
          </li>
        ))}
      </ul>
      <p className="mt-2 text-[11px] text-slate-500">
        Native {provenance?.native_resolution_m ?? 20} m SCL aligned to the{" "}
        {provenance?.target_grid_resolution_m ?? 10} m grid by{" "}
        {(provenance?.alignment ?? "nearest_neighbor").replaceAll("_", " ")}.
        Bilinear interpolation is not used. Native 20 m counts are not mixed with 10 m counts.
      </p>
    </div>
  );
}
