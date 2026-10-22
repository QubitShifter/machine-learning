import { StatusBadge } from "@/components/common/StatusBadge";

const MONTHS = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"];
const YEARS = ["2023", "2024", "2025"];

interface Props {
  availability?: Record<string, string>;
  monthlyQuality?: Record<string, string>;
  satelliteStatuses?: Record<string, string>;
  onSelect?: (month: string) => void;
}

const SATELLITE_TONE: Record<string, string> = {
  validated_observation: "bg-moss-600",
  processed_warning: "bg-sand-400",
  requires_calibration_review: "bg-sand-400",
  processed_rejected: "bg-red-500",
  downloaded_not_processed: "bg-slate-500",
  discovered_not_downloaded: "bg-slate-600",
  no_scene_discovered: "bg-ink-700",
  unknown_discovery_evidence: "bg-slate-800 ring-1 ring-inset ring-slate-500",
};

export function CoverageMatrix({
  availability = {},
  monthlyQuality = {},
  satelliteStatuses,
  onSelect,
}: Props) {
  return (
    <div>
      <div className="mb-3 grid grid-cols-[3rem_repeat(12,minmax(0,1fr))] gap-1 text-[10px] uppercase text-slate-500">
        <span />
        {MONTHS.map((month) => (
          <span key={month} className="text-center">{month}</span>
        ))}
      </div>
      {YEARS.map((year) => (
        <div key={year} className="mb-1 grid grid-cols-[3rem_repeat(12,minmax(0,1fr))] gap-1">
          <span className="text-xs text-slate-400">{year}</span>
          {MONTHS.map((month) => {
            const key = `${year}-${month}`;
            const satellite = satelliteStatuses?.[key];
            const download = availability[key] ?? "missing_source";
            const quality = monthlyQuality[key];
            const tone = satellite
              ? (SATELLITE_TONE[satellite] ?? "bg-slate-700")
              : download === "downloaded" && (!quality || quality === "valid")
                ? "bg-moss-600"
                : download === "partial" || quality === "requires_review"
                  ? "bg-sand-400"
                  : quality === "rejected" || download === "failed"
                    ? "bg-red-500"
                    : "bg-slate-700";
            const label = satellite ?? `${download}${quality ? `, ${quality}` : ""}`;
            return (
              <button
                key={key}
                type="button"
                title={`${key}: ${label}`}
                onClick={() => onSelect?.(key)}
                className={`h-7 rounded ${tone} focus-visible:outline`}
                aria-label={`${key} ${label}`}
              />
            );
          })}
        </div>
      ))}
      <div className="mt-3 flex flex-wrap gap-2 text-xs">
        {satelliteStatuses ? (
          <>
            <StatusBadge value="valid" label="Validated observation" />
            <StatusBadge value="requires_review" label="Calibration review" />
            <StatusBadge value="discovered" label="Discovered, not downloaded" />
            <StatusBadge value="unknown" label="Unknown discovery evidence" />
            <StatusBadge value="rejected" />
          </>
        ) : (
          <>
            <StatusBadge value="downloaded" label="Downloaded / complete" />
            <StatusBadge value="missing_source" />
            <StatusBadge value="partial" label="Incomplete / review" />
            <StatusBadge value="rejected" />
          </>
        )}
      </div>
    </div>
  );
}
