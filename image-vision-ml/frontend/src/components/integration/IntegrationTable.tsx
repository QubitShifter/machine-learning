import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Card } from "@/components/common/Card";
import { StatusBadge } from "@/components/common/StatusBadge";
import type { IntegrationObservation } from "@/types/integration";
import { formatNumber, formatUtcTimestamp } from "@/utils/format";
import { platformFromSceneId, weatherAvailabilityLabel } from "@/utils/integration";

interface Props {
  observations: IntegrationObservation[];
  selectedId?: string;
  onSelect: (sceneId: string) => void;
}

type SortKey = "date" | "ndvi" | "p7" | "p30" | "scene";

export function IntegrationTable({ observations, selectedId, onSelect }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("date");
  const [desc, setDesc] = useState(true);
  const rows = useMemo(() => {
    return [...observations].sort((a, b) => {
      let cmp = 0;
      if (sortKey === "ndvi") cmp = cmpNum(a.ndvi_mean, b.ndvi_mean);
      else if (sortKey === "p7") cmp = cmpNum(a.precip_prev_7d_mm, b.precip_prev_7d_mm);
      else if (sortKey === "p30") cmp = cmpNum(a.precip_prev_30d_mm, b.precip_prev_30d_mm);
      else if (sortKey === "scene") cmp = String(a.scene_id ?? "").localeCompare(String(b.scene_id ?? ""));
      else cmp = String(a.observation_date_utc ?? "").localeCompare(String(b.observation_date_utc ?? ""));
      if (cmp !== 0) return desc ? -cmp : cmp;
      return String(a.scene_id ?? "").localeCompare(String(b.scene_id ?? ""));
    });
  }, [observations, sortKey, desc]);

  const toggle = (key: SortKey) => {
    if (sortKey === key) setDesc((value) => !value);
    else {
      setSortKey(key);
      setDesc(key === "date");
    }
  };

  return (
    <Card title="Integrated acquisitions">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead>
            <tr className="text-xs uppercase tracking-wide text-slate-500">
              <Header label="Date" onClick={() => toggle("date")} active={sortKey === "date"} />
              <Header label="Scene / platform" onClick={() => toggle("scene")} active={sortKey === "scene"} />
              <Header label="Mean NDVI" onClick={() => toggle("ndvi")} active={sortKey === "ndvi"} />
              <Header label="7-day rain" onClick={() => toggle("p7")} active={sortKey === "p7"} />
              <Header label="30-day rain" onClick={() => toggle("p30")} active={sortKey === "p30"} />
              <th className="px-2 py-1 font-medium">Weather</th>
              <th className="px-2 py-1 font-medium">Satellite</th>
              <th className="px-2 py-1 font-medium">Explorer</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const selected = row.scene_id === selectedId;
              return (
                <tr
                  key={row.scene_id ?? row.observation_date_utc}
                  data-selected={String(selected)}
                  className={`cursor-pointer border-t border-ink-700 ${selected ? "bg-moss-600/10" : "hover:bg-ink-800"}`}
                  onClick={() => row.scene_id && onSelect(row.scene_id)}
                >
                  <td className="whitespace-nowrap px-2 py-2 text-slate-200">
                    {formatUtcTimestamp(row.observation_date_utc)}
                  </td>
                  <td className="px-2 py-2">
                    <span className="block font-mono text-xs text-slate-300">{row.scene_id}</span>
                    <span className="text-[11px] text-slate-500">{platformFromSceneId(row.scene_id) ?? "Sentinel-2"}</span>
                  </td>
                  <td className="px-2 py-2 font-mono">{formatNumber(row.ndvi_mean, 3)}</td>
                  <td className="px-2 py-2 font-mono">{numericOrUnavailable(row.precip_prev_7d_mm, "mm")}</td>
                  <td className="px-2 py-2 font-mono">{numericOrUnavailable(row.precip_prev_30d_mm, "mm")}</td>
                  <td className="px-2 py-2 text-xs text-slate-400">{weatherAvailabilityLabel(row)}</td>
                  <td className="px-2 py-2"><StatusBadge value={row.satellite_quality_status ?? row.quality_status} /></td>
                  <td className="px-2 py-2">
                    {row.scene_id ? (
                      <Link
                        className="text-xs text-moss-300 hover:underline"
                        to={`/satellite?scene=${encodeURIComponent(row.scene_id)}`}
                        onClick={(event) => event.stopPropagation()}
                      >
                        Map
                      </Link>
                    ) : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function Header({ label, onClick, active }: { label: string; onClick: () => void; active: boolean }) {
  return (
    <th className="px-2 py-1 font-medium">
      <button type="button" onClick={onClick} className={`text-left ${active ? "text-moss-300" : "text-slate-500"}`}>
        {label}
      </button>
    </th>
  );
}

function cmpNum(a: number | null | undefined, b: number | null | undefined): number {
  if (a === null || a === undefined) return b === null || b === undefined ? 0 : -1;
  if (b === null || b === undefined) return 1;
  return a - b;
}

function numericOrUnavailable(value: number | null | undefined, unit: string): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "Unavailable";
  return `${formatNumber(value, 3)} ${unit}`;
}
