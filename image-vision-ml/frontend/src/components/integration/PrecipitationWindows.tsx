import { Card } from "@/components/common/Card";
import type { IntegrationObservation, WeatherWindowDays } from "@/types/integration";
import { formatNumber } from "@/utils/format";
import { coverageKind, precipForWindow, windowField } from "@/utils/integration";

interface Props {
  row: IntegrationObservation;
}

const WINDOWS: WeatherWindowDays[] = [7, 14, 30];

export function PrecipitationWindows({ row }: Props) {
  const values = WINDOWS.map((days) => precipForWindow(row, days));
  const scale = Math.max(0, ...values.filter((value): value is number => value !== null && value > 0));

  return (
    <Card title="Preceding rainfall">
      <p className="mb-3 text-xs text-slate-500">
        Nested lookback totals from the integration API. Do not add the 7-, 14- and 30-day values together.
      </p>
      <div className="grid gap-3 md:grid-cols-3">
        {WINDOWS.map((days, index) => {
          const value = values[index];
          const observed = windowField<number>(row, days, "observed");
          const expected = windowField<number>(row, days, "expected") ?? days;
          const missing = windowField<number>(row, days, "missing");
          const start = windowField<string>(row, days, "start");
          const end = windowField<string>(row, days, "end");
          const kind = coverageKind(observed, expected);
          const available = value !== null;
          const width = !available || scale === 0
            ? 0
            : Math.max(value === 0 ? 2 : 8, Math.round((value / scale) * 100));
          return (
            <div
              key={days}
              data-testid={`precip-${days}d`}
              data-available={String(available)}
              data-coverage={kind}
              className="rounded-lg border border-ink-600 bg-ink-800/50 p-3"
            >
              <p className="text-[11px] uppercase tracking-wide text-slate-500">Prior {days}-day rainfall</p>
              <p className="mt-1 font-mono text-lg text-slate-100">
                {available ? `${formatNumber(value, 3)} mm` : "Unavailable"}
              </p>
              <div className="mt-2 h-2 overflow-hidden rounded bg-ink-700" aria-hidden="true">
                {available ? (
                  <div
                    className={`h-full ${kind === "complete" ? "bg-sky-400" : "bg-sand-400"}`}
                    style={{ width: `${width}%` }}
                  />
                ) : (
                  <div className="h-full w-full bg-[repeating-linear-gradient(45deg,#1a3144,#1a3144_6px,#27445c_6px,#27445c_12px)]" />
                )}
              </div>
              <p className="mt-2 text-xs text-slate-400">
                {observed ?? 0}/{expected} days
                {missing ? ` · ${missing} missing` : ""}
                {" · "}
                {kind === "complete" ? "complete" : kind === "partial" ? "partial" : "missing"}
              </p>
              <p className="text-[11px] text-slate-500">
                UTC {start ?? "—"} to {end ?? "—"}
              </p>
              {!available ? (
                <p className="mt-1 text-[11px] text-sand-300">
                  Aggregate withheld because the window is not fully observed. Missing days are not treated as zero rainfall.
                </p>
              ) : null}
            </div>
          );
        })}
      </div>
    </Card>
  );
}
