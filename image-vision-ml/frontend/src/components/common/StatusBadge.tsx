import { formatStatus } from "@/utils/format";

const TONES: Record<string, string> = {
  valid: "bg-moss-600/20 text-moss-400 border-moss-600/40",
  downloaded: "bg-moss-600/20 text-moss-400 border-moss-600/40",
  complete: "bg-moss-600/20 text-moss-400 border-moss-600/40",
  ready: "bg-moss-600/20 text-moss-400 border-moss-600/40",
  warning: "bg-sand-400/15 text-sand-300 border-sand-400/40",
  limited: "bg-sand-400/15 text-sand-300 border-sand-400/40",
  incomplete: "bg-sand-400/15 text-sand-300 border-sand-400/40",
  partial: "bg-sand-400/15 text-sand-300 border-sand-400/40",
  requires_review: "bg-rust-400/15 text-rust-400 border-rust-400/40",
  rejected: "bg-red-500/15 text-red-300 border-red-500/40",
  not_ready: "bg-red-500/15 text-red-300 border-red-500/40",
  missing: "bg-slate-700/60 text-slate-300 border-slate-500/40",
  missing_source: "bg-slate-700/60 text-slate-300 border-slate-500/40",
  pending: "bg-slate-700/60 text-slate-300 border-slate-500/40",
  failed: "bg-red-500/15 text-red-300 border-red-500/40",
};

interface Props {
  value: string | null | undefined;
  label?: string;
}

export function StatusBadge({ value, label }: Props) {
  const key = value ?? "unknown";
  const tone = TONES[key] ?? "bg-slate-700/60 text-slate-300 border-slate-500/40";
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium capitalize ${tone}`}
    >
      {label ?? formatStatus(key)}
    </span>
  );
}
