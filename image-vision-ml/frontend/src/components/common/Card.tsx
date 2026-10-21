import type { ReactNode } from "react";

interface Props {
  title?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function Card({ title, actions, children, className = "" }: Props) {
  return (
    <section className={`rounded-xl border border-ink-600/70 bg-ink-900/80 p-4 ${className}`}>
      {(title || actions) && (
        <header className="mb-3 flex items-start justify-between gap-3">
          {title ? <h2 className="text-sm font-semibold tracking-wide text-slate-200">{title}</h2> : <span />}
          {actions}
        </header>
      )}
      {children}
    </section>
  );
}
