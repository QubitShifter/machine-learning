interface Props {
  label: string;
  value: string;
  hint?: string;
}

export function Metric({ label, value, hint }: Props) {
  return (
    <div className="rounded-lg border border-ink-600/60 bg-ink-800/50 px-3 py-2">
      <p className="text-[11px] uppercase tracking-wider text-slate-400">{label}</p>
      <p className="mt-1 break-all font-mono text-lg text-slate-100">{value}</p>
      {hint ? <p className="mt-1 text-xs text-slate-500">{hint}</p> : null}
    </div>
  );
}
