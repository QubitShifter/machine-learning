import type { ReactNode } from "react";

interface Props {
  id: string;
  title: string;
  summary?: ReactNode;
  open: boolean;
  onToggle: () => void;
  children: ReactNode;
  defaultExpandedHint?: string;
}

export function InspectorSection({
  id,
  title,
  summary,
  open,
  onToggle,
  children,
}: Props) {
  return (
    <section className="rounded-lg border border-ink-600/70 bg-ink-900/80" data-open={String(open)}>
      <h2 className="m-0">
        <button
          type="button"
          className="flex w-full items-start justify-between gap-2 px-3 py-2 text-left"
          aria-expanded={open}
          aria-controls={id}
          onClick={onToggle}
        >
          <span>
            <span className="block text-sm font-semibold tracking-wide text-slate-200">{title}</span>
            {summary ? <span className="mt-1 block text-[11px] font-normal text-slate-400">{summary}</span> : null}
          </span>
          <span className="mt-0.5 text-[10px] uppercase tracking-wide text-slate-500">
            {open ? "Collapse" : "Expand"}
          </span>
        </button>
      </h2>
      {open ? (
        <div id={id} className="border-t border-ink-700 px-3 py-3">
          {children}
        </div>
      ) : null}
    </section>
  );
}
