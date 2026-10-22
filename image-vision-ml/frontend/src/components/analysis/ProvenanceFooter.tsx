interface Item {
  label: string;
  value?: string | number | null;
}

interface Props {
  items: Item[];
  note?: string;
}

export function ProvenanceFooter({ items, note }: Props) {
  return (
    <footer className="mt-3 border-t border-ink-700 pt-2">
      <dl className="grid gap-x-4 gap-y-1 text-[11px] text-slate-400 sm:grid-cols-2">
        {items.map((item) => (
          <div key={item.label} className="flex justify-between gap-3">
            <dt>{item.label}</dt>
            <dd className="text-right text-slate-300">{item.value ?? "—"}</dd>
          </div>
        ))}
      </dl>
      {note ? <p className="mt-2 text-[11px] text-slate-500">{note}</p> : null}
    </footer>
  );
}
