import { Card } from "@/components/common/Card";
import { StatusBadge } from "@/components/common/StatusBadge";
import type { TrainingEvent } from "@/types/ml";
import { formatDurationMs, safeErrorSummary, timelineFromEvents } from "@/utils/runTelemetry";

interface Props {
  events: TrainingEvent[];
  status: string;
}

export function TrainingRunTimeline({ events, status }: Props) {
  const items = timelineFromEvents(events);
  const failure = events.find((event) => event.event_type === "run_failed");
  return (
    <Card title="Training timeline">
      {items.length === 0 ? (
        <p className="text-sm text-sand-200">No lifecycle events are recorded. A run directory alone is not treated as completed.</p>
      ) : (
        <ol className="space-y-2">
          {items.map((item) => (
            <li key={`${item.event_type}-${item.sequence}`} className="flex items-start justify-between gap-3 rounded border border-ink-700 px-3 py-2 text-sm">
              <span>
                <span className="font-medium text-slate-100">{item.label}</span>
                <span className="ml-2 font-mono text-[11px] text-slate-500">{item.timestamp_utc}</span>
                <span className="ml-2 text-[11px] text-slate-500">{formatDurationMs(item.elapsed_ms)}</span>
              </span>
              <StatusBadge value={item.failed ? "failed" : "complete"} label={item.failed ? "failed" : "recorded"} />
            </li>
          ))}
        </ol>
      )}
      {failure ? (
        <p className="mt-3 text-sm text-red-300" data-testid="run-failure-summary">
          Failed during {failure.phase}: {safeErrorSummary(failure.details)}
        </p>
      ) : null}
      <p className="mt-3 text-xs text-slate-500">Status from the run manifest: {status}. Stages are listed only when present in the event log.</p>
    </Card>
  );
}
