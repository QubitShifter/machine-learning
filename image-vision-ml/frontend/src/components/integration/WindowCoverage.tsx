import { Card } from "@/components/common/Card";
import type { IntegrationObservation, WeatherWindowDays } from "@/types/integration";
import { coverageKind, windowField, WINDOW_LOOKBACK_RULE } from "@/utils/integration";

interface Props {
  row: IntegrationObservation;
  rule?: string | null;
}

const WINDOWS: WeatherWindowDays[] = [7, 14, 30];

export function WindowCoverage({ row, rule }: Props) {
  return (
    <Card title="Feature-window coverage">
      <p className="mb-3 text-xs text-slate-400">{rule || WINDOW_LOOKBACK_RULE}</p>
      <ul className="space-y-2">
        {WINDOWS.map((days) => {
          const observed = windowField<number>(row, days, "observed") ?? 0;
          const expected = windowField<number>(row, days, "expected") ?? days;
          const start = windowField<string>(row, days, "start");
          const end = windowField<string>(row, days, "end");
          const kind = coverageKind(observed, expected);
          const pct = expected > 0 ? Math.min(100, Math.round((observed / expected) * 100)) : 0;
          const tone = kind === "complete" ? "bg-moss-500" : kind === "partial" ? "bg-sand-400" : "bg-slate-600";
          return (
            <li key={days} data-testid={`coverage-${days}d`} data-coverage={kind}>
              <div className="flex items-baseline justify-between gap-2 text-sm">
                <span className="text-slate-300">{days} days: {observed}/{expected}</span>
                <span className="text-xs capitalize text-slate-500">{kind}</span>
              </div>
              <div className="mt-1 h-2 overflow-hidden rounded bg-ink-700" aria-hidden="true">
                <div className={`h-full ${tone}`} style={{ width: `${kind === "missing" ? 0 : pct}%` }} />
              </div>
              <p className="mt-1 text-[11px] text-slate-500">UTC {start ?? "—"} … {end ?? "—"}</p>
            </li>
          );
        })}
      </ul>
      <p className="mt-3 text-[11px] text-slate-500">
        Coverage counts reported daily observations. Values are not interpolated.
      </p>
    </Card>
  );
}
