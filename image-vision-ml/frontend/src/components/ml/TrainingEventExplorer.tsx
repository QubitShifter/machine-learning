import { useMemo, useState } from "react";
import { Card } from "@/components/common/Card";
import type { TrainingEvent } from "@/types/ml";

interface Props {
  events: TrainingEvent[];
}

export function TrainingEventExplorer({ events }: Props) {
  const types = useMemo(() => [...new Set(events.map((item) => item.event_type))], [events]);
  const [eventType, setEventType] = useState("");
  const filtered = eventType ? events.filter((item) => item.event_type === eventType) : events;
  return (
    <Card title="Event explorer">
      <label className="mb-2 block text-xs text-slate-400">
        Event type
        <select
          aria-label="Event type filter"
          className="mt-1 w-full rounded border border-ink-600 bg-ink-800 px-2 py-1.5 text-sm text-slate-100 md:w-64"
          value={eventType}
          onChange={(event) => setEventType(event.target.value)}
        >
          <option value="">All recorded events</option>
          {types.map((item) => (
            <option key={item} value={item}>{item}</option>
          ))}
        </select>
      </label>
      <div className="max-h-80 overflow-auto rounded border border-ink-700">
        <table className="min-w-full text-left text-xs text-slate-300">
          <thead className="sticky top-0 bg-ink-900 text-slate-400">
            <tr>
              <th className="px-2 py-1">seq</th>
              <th className="px-2 py-1">type</th>
              <th className="px-2 py-1">phase</th>
              <th className="px-2 py-1">iter</th>
              <th className="px-2 py-1">metric</th>
              <th className="px-2 py-1">elapsed</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((event) => (
              <tr key={event.sequence} className="border-t border-ink-800">
                <td className="px-2 py-1 font-mono">{event.sequence}</td>
                <td className="px-2 py-1">{event.event_type}</td>
                <td className="px-2 py-1">{event.phase}</td>
                <td className="px-2 py-1">{event.iteration ?? "—"}</td>
                <td className="break-all px-2 py-1">
                  {event.metric_name ? `${event.metric_name}=${event.metric_value}` : "—"}
                </td>
                <td className="px-2 py-1">{event.elapsed_ms} ms</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-xs text-slate-500">{filtered.length} recorded events. Incomplete final JSONL lines are omitted by the API.</p>
    </Card>
  );
}
