import { Card } from "@/components/common/Card";
import type { IntegrationObservation, ObservationFilter } from "@/types/integration";
import { formatUtcTimestamp } from "@/utils/format";
import {
  filterObservations,
  platformFromSceneId,
  sortObservations,
  weatherAvailabilityLabel,
} from "@/utils/integration";

interface Props {
  observations: IntegrationObservation[];
  selectedId?: string;
  filter: ObservationFilter;
  onFilter: (value: ObservationFilter) => void;
  onSelect: (sceneId: string) => void;
  invalidRequested?: boolean;
  requestedScene?: string | null;
}

export function ObservationSelector({
  observations,
  selectedId,
  filter,
  onFilter,
  onSelect,
  invalidRequested,
  requestedScene,
}: Props) {
  const visible = sortObservations(filterObservations(observations, filter));

  return (
    <Card title="Acquisition selector">
      {invalidRequested && requestedScene ? (
        <p className="mb-3 rounded border border-sand-400/40 bg-sand-400/10 px-2 py-1 text-xs text-sand-200" role="status">
          Scene {requestedScene} is not in the integrated table. Showing a fallback acquisition.
        </p>
      ) : null}
      <div className="grid gap-3 lg:grid-cols-[16rem_minmax(0,1fr)]">
        <fieldset className="text-sm text-slate-300">
          <legend className="mb-1 text-xs uppercase tracking-wide text-slate-500">Weather windows</legend>
          {([
            ["all", "All observations"],
            ["complete", "Complete weather windows"],
            ["incomplete", "Incomplete weather windows"],
          ] as const).map(([value, label]) => (
            <label key={value} className="flex items-center gap-2 py-0.5">
              <input
                type="radio"
                name="integration-filter"
                value={value}
                checked={filter === value}
                onChange={() => onFilter(value)}
              />
              {label}
            </label>
          ))}
        </fieldset>
        <label className="text-sm text-slate-300" htmlFor="integration-scene">
          Integrated acquisition
          <select
            id="integration-scene"
            className="mt-1 w-full rounded border border-ink-600 bg-ink-800 px-2 py-1 font-mono text-xs"
            value={selectedId ?? ""}
            onChange={(event) => onSelect(event.target.value)}
          >
            {visible.map((row) => (
              <option key={row.scene_id ?? ""} value={row.scene_id ?? ""}>
                {formatUtcTimestamp(row.acquisition_timestamp_utc ?? row.observation_date_utc)}
                {" · "}
                {platformFromSceneId(row.scene_id) ?? "Sentinel-2"}
                {" · "}
                {row.scene_id}
                {" · "}
                {weatherAvailabilityLabel(row)}
              </option>
            ))}
          </select>
        </label>
      </div>
      {visible.length === 0 ? (
        <p className="mt-2 text-sm text-slate-400">No integrated observations match this filter.</p>
      ) : null}
    </Card>
  );
}
