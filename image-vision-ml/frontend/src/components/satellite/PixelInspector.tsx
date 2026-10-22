import { StatusBadge } from "@/components/common/StatusBadge";
import type { PixelInspect } from "@/types/api";
import { formatNumber } from "@/utils/format";

interface Props {
  sample: PixelInspect | null;
  loading?: boolean;
  pending?: { longitude: number; latitude: number } | null;
}

export function PixelInspector({ sample, loading = false, pending = null }: Props) {
  if (!sample && !loading) {
    return (
      <div data-testid="pixel-inspector-empty" className="text-sm text-slate-400">
        Click inside the satellite overlay to read the processed raster at that location.
        Values come from GeoTIFFs, not from display PNG colors.
      </div>
    );
  }

  const outside = Boolean(
    sample && (sample.coverage_state === "out_of_coverage" || !sample.inside_raster),
  );
  const excluded = Boolean(sample && sample.inside_raster && sample.valid_mask === false);
  const longitude = sample?.longitude ?? pending?.longitude;
  const latitude = sample?.latitude ?? pending?.latitude;

  return (
    <div data-testid="pixel-inspector" aria-live="polite" className="space-y-3 text-xs">
      {loading ? (
        <p className="rounded border border-moss-600/40 bg-moss-600/10 px-2 py-1 text-moss-300" role="status">
          Reading processed rasters
          {longitude != null && latitude != null
            ? ` at ${longitude.toFixed(5)}°E, ${latitude.toFixed(5)}°N`
            : ""}
          …
        </p>
      ) : null}
      {outside ? (
        <p className="rounded border border-sand-400/40 bg-sand-400/10 p-2 text-sand-200" role="status">
          Out of coverage. {sample?.message ?? "Clicked location is outside the processed raster footprint."}
        </p>
      ) : null}
      {excluded && !outside ? (
        <p className="rounded border border-sand-400/40 bg-sand-400/10 p-2 text-sand-200" role="status">
          Excluded by quality controls. {sample?.exclusion_reason ?? sample?.message ?? "Pixel is not valid land NDVI."}
        </p>
      ) : null}

      <dl className="grid grid-cols-1 gap-1">
        <Row label="Coordinates" value={
          longitude == null || latitude == null
            ? "—"
            : `${longitude.toFixed(6)}°E, ${latitude.toFixed(6)}°N`
        } />
        <Row
          label="Raster pixel"
          value={sample?.row == null || sample?.col == null ? "—" : `row ${sample.row}, col ${sample.col}`}
        />
        <Row
          label="SCL"
          value={sample?.scl_class == null
            ? sample?.missing_reasons.scl ?? (loading ? "loading" : "unavailable")
            : `${sample.scl_class} · ${sample.scl_class_name}`}
        />
        <ValueRow label="NDVI" value={sample?.ndvi ?? null} reason={sample?.missing_reasons.ndvi} />
        <Row
          label="Valid mask"
          value={sample?.valid_mask == null ? (loading ? "loading" : "—") : sample.valid_mask ? "valid land" : "excluded"}
        />
        <Row
          label="Exclusion reason"
          value={sample?.exclusion_reason ?? (sample?.valid ? "none (valid NDVI)" : sample ? "—" : "—")}
        />
      </dl>

      <table className="w-full border-collapse text-[11px]" data-testid="pixel-reflectance-table">
        <caption className="mb-1 text-left text-[11px] uppercase tracking-wide text-slate-500">
          BOA surface reflectance
        </caption>
        <tbody>
          <BandRow label="Red B04" value={sample?.red_b04 ?? null} reason={sample?.missing_reasons.red_b04} />
          <BandRow label="Green B03" value={sample?.green_b03 ?? null} reason={sample?.missing_reasons.green_b03} />
          <BandRow label="Blue B02" value={sample?.blue_b02 ?? null} reason={sample?.missing_reasons.blue_b02} />
          <BandRow label="NIR B08" value={sample?.nir_b08 ?? null} reason={sample?.missing_reasons.nir_b08} />
        </tbody>
      </table>

      <div className="flex flex-wrap gap-2">
        <StatusBadge value={sample?.scene_quality_status} label={`scene ${sample?.scene_quality_status ?? "unknown"}`} />
        <StatusBadge value={sample?.calibration_status} label={`calibration ${sample?.calibration_status ?? "unknown"}`} />
      </div>
      {sample ? (
        <p className="text-[11px] text-slate-500">
          {sample.sampling}. Source: {sample.source}.
          {sample.estimated_from_display_rgb ? " Estimated from display RGB." : " Not estimated from displayed RGB colors."}
          Masked pixels are null, not measured zero.
        </p>
      ) : null}
    </div>
  );
}

function Row({ label, value }: { label: string; value?: string | number | null }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-slate-400">{label}</dt>
      <dd className="text-right font-mono text-slate-200">{value ?? "—"}</dd>
    </div>
  );
}

function ValueRow({
  label,
  value,
  reason,
}: {
  label: string;
  value: number | null;
  reason?: string;
}) {
  return (
    <Row
      label={label}
      value={value == null ? (reason ? `null (${reason})` : "null") : formatNumber(value, 4)}
    />
  );
}

function BandRow({
  label,
  value,
  reason,
}: {
  label: string;
  value: number | null;
  reason?: string;
}) {
  return (
    <tr className="border-t border-ink-700">
      <th scope="row" className="py-1 pr-2 text-left font-normal text-slate-400">{label}</th>
      <td className="py-1 text-right font-mono text-slate-200">
        {value == null ? (reason ? `null (${reason})` : "null") : formatNumber(value, 4)}
      </td>
    </tr>
  );
}
