import { useState } from "react";
import { Card } from "@/components/common/Card";
import { QueryState } from "@/components/common/QueryState";
import { SatelliteMap } from "@/components/maps/SatelliteMap";
import { useAoiRegistry, useCreateAoiDraft } from "@/hooks/useAoi";
import { bboxAreaKm2, type DraftGeometry, validateBbox } from "@/utils/aoiGeometry";
import { formatNumber } from "@/utils/format";

export function AoiPage() {
  const registry = useAoiRegistry();
  const createDraft = useCreateAoiDraft();
  const [drawMode, setDrawMode] = useState<"draw-bbox" | "draw-polygon">("draw-bbox");
  const [draft, setDraft] = useState<DraftGeometry | null>(null);
  const [name, setName] = useState("Proposed study area");
  const [error, setError] = useState<string | null>(null);
  const operational = registry.data?.areas ?? [];
  const selected = operational[0];
  const validation = draft ? validateBbox(draft.bbox) : null;
  const areaKm2 = draft
    ? bboxAreaKm2(draft.bbox[0], draft.bbox[1], draft.bbox[2], draft.bbox[3])
    : null;

  return (
    <div className="space-y-4">
      <Card title="Operational study areas">
        <QueryState
          isLoading={registry.isLoading}
          error={registry.error}
          onRetry={() => void registry.refetch()}
          empty={!operational.length}
        >
          <p className="text-sm text-slate-400">
            These areas already have satellite datasets. This page does not download imagery,
            weather, or soil archives, and it does not modify the Plovdiv dataset.
          </p>
          <ul className="mt-3 space-y-2 text-sm">
            {operational.map((item) => (
              <li key={item.aoi_id} className="rounded border border-ink-700 p-3">
                <p className="font-medium text-slate-200">{item.name}</p>
                <p className="font-mono text-xs text-slate-400">
                  {item.status} · {item.bbox.join(", ")}
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  Satellite {item.satellite_dataset_id ?? "none"} · weather {item.weather_dataset_id ?? "none"} · soil {item.soil_dataset_id ?? "none"}
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  Area {formatNumber(item.geometry?.area_km2, 3)} km² · ~{formatNumber(item.geometry?.approximate_10m_pixels, 0)} 10 m pixels
                </p>
              </li>
            ))}
          </ul>
        </QueryState>
      </Card>

      <Card
        title="Propose a draft AOI"
        actions={(
          <div className="flex gap-1">
            {(["draw-bbox", "draw-polygon"] as const).map((item) => (
              <button
                key={item}
                type="button"
                className={`rounded px-2 py-1 text-xs uppercase ${
                  drawMode === item ? "bg-moss-600 text-ink-950" : "bg-ink-700"
                }`}
                onClick={() => setDrawMode(item)}
              >
                {item === "draw-bbox" ? "Box" : "Polygon"}
              </button>
            ))}
          </div>
        )}
      >
        <SatelliteMap
          bbox={selected?.bbox}
          mode="ndvi"
          opacity={0.2}
          showAoi
          overlayAvailable={false}
          interaction={drawMode}
          draftGeometry={draft}
          onDraftGeometry={(geometry) => {
            setDraft(geometry);
            setError(validateBbox(geometry.bbox));
          }}
        />
        {draft ? (
          <div className="mt-3 space-y-2 text-sm" data-testid="draft-aoi-summary">
            <p className="font-mono text-xs">
              {draft.type} · {draft.bbox.map((value) => value.toFixed(5)).join(", ")}
            </p>
            <p>Approximate area {formatNumber(areaKm2, 3)} km²</p>
            <p className="text-xs text-slate-400">
              Scope is a proposal only: Sentinel-2 would be a new dataset later; ERA5 cells are ~0.1°.
              No CDS or STAC request is made from this form.
            </p>
            <label className="block text-xs text-slate-300">
              Draft name
              <input
                className="mt-1 w-full rounded border border-ink-600 bg-ink-800 px-2 py-1"
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
            </label>
            {validation ? <p className="text-xs text-rust-400" role="alert">{validation}</p> : null}
            <button
              type="button"
              className="rounded bg-moss-600 px-3 py-1 text-sm text-ink-950 disabled:opacity-40"
              disabled={Boolean(validation) || createDraft.isPending}
              onClick={async () => {
                try {
                  await createDraft.mutateAsync({
                    name,
                    geometry_type: draft.type,
                    bbox: draft.type === "bbox" ? draft.bbox : undefined,
                    coordinates: draft.coordinates,
                  });
                  setError(null);
                } catch (cause) {
                  setError(cause instanceof Error ? cause.message : "Draft was not saved.");
                }
              }}
            >
              Save draft proposal
            </button>
            {error && !validation ? <p className="text-xs text-rust-400" role="alert">{error}</p> : null}
            {createDraft.isSuccess ? (
              <p className="text-xs text-moss-300" role="status">Draft saved. No satellite or soil download was started.</p>
            ) : null}
          </div>
        ) : (
          <p className="mt-2 text-xs text-slate-500">Draw a box or polygon on the map. Drafts stay separate from operational datasets.</p>
        )}
      </Card>

      <Card title="Saved drafts">
        {(registry.data?.drafts ?? []).length ? (
          <ul className="space-y-2 text-xs">
            {registry.data?.drafts.map((item) => (
              <li key={item.draft_id} className="rounded border border-ink-700 p-2">
                <p className="font-medium text-slate-200">{item.name} · {item.status}</p>
                <p className="font-mono text-slate-400">{item.geometry.bbox.join(", ")}</p>
                <p className="text-slate-500">{item.note}</p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-slate-400">No draft AOIs yet.</p>
        )}
      </Card>
    </div>
  );
}
