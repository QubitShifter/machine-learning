import { useEffect, useMemo, useState } from "react";
import { Card } from "@/components/common/Card";
import type { TrainingEvent } from "@/types/ml";
import { PLAYBACK_LABEL, eventsThrough, metricHistoryPoints } from "@/utils/runTelemetry";

interface Props {
  events: TrainingEvent[];
}

export function TrainingPlayback({ events }: Props) {
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const last = Math.max(events.length - 1, 0);

  useEffect(() => {
    setIndex(0);
    setPlaying(false);
  }, [events]);

  useEffect(() => {
    if (!playing || events.length === 0) return undefined;
    const handle = window.setInterval(() => {
      setIndex((current) => {
        if (current >= events.length - 1) {
          setPlaying(false);
          return current;
        }
        return current + 1;
      });
    }, Math.max(150, 800 / speed));
    return () => window.clearInterval(handle);
  }, [playing, speed, events.length]);

  const visible = eventsThrough(events, events.length ? index : -1);
  const current = events[index];
  const metrics = useMemo(() => metricHistoryPoints(visible), [visible]);

  return (
    <Card title={PLAYBACK_LABEL}>
      <p className="mb-3 text-sm text-sand-200">
        Replays stored events. This is not live monitoring and does not retrain a model.
      </p>
      {events.length === 0 ? (
        <p className="text-sm text-slate-400">No events are available to play back.</p>
      ) : (
        <>
          <div className="flex flex-wrap gap-2">
            <button type="button" className={buttonClass} onClick={() => setPlaying(true)} aria-label="Play historical playback">Play</button>
            <button type="button" className={buttonClass} onClick={() => setPlaying(false)} aria-label="Pause historical playback">Pause</button>
            <button type="button" className={buttonClass} onClick={() => setIndex((value) => Math.max(0, value - 1))} aria-label="Step backward">Step back</button>
            <button type="button" className={buttonClass} onClick={() => setIndex((value) => Math.min(last, value + 1))} aria-label="Step forward">Step forward</button>
            <button type="button" className={buttonClass} onClick={() => { setPlaying(false); setIndex(0); }} aria-label="Reset historical playback">Reset</button>
            <label className="text-xs text-slate-400">
              Speed
              <select
                aria-label="Playback speed"
                className="ml-2 rounded border border-ink-600 bg-ink-800 px-2 py-1 text-sm text-slate-100"
                value={String(speed)}
                onChange={(event) => setSpeed(Number(event.target.value))}
              >
                <option value="0.5">0.5×</option>
                <option value="1">1×</option>
                <option value="2">2×</option>
                <option value="4">4×</option>
              </select>
            </label>
          </div>
          <p className="mt-3 text-sm text-slate-200" data-testid="playback-cursor">
            Event {index + 1} / {events.length}: {current?.event_type} · phase {current?.phase}
            {current?.iteration != null ? ` · iteration ${current.iteration}` : ""}
          </p>
          <p className="text-xs text-slate-500">{current?.timestamp_utc} · elapsed {current?.elapsed_ms} ms</p>
          <p className="mt-2 text-xs text-slate-400">
            Metrics recorded up to this event: {metrics.length ? metrics.map((item) => `${item.metric_name}=${item.value}`).slice(-6).join(", ") : "none yet"}
          </p>
        </>
      )}
    </Card>
  );
}

const buttonClass = "rounded border border-ink-600 px-3 py-1.5 text-xs text-slate-200 hover:bg-ink-800";
