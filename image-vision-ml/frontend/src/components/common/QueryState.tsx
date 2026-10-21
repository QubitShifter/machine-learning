import type { ReactNode } from "react";

interface Props {
  isLoading: boolean;
  error: Error | null;
  onRetry?: () => void;
  empty?: boolean;
  emptyMessage?: string;
  children: ReactNode;
  skeleton?: ReactNode;
}

export function QueryState({
  isLoading,
  error,
  onRetry,
  empty,
  emptyMessage = "No records are available yet.",
  children,
  skeleton,
}: Props) {
  if (isLoading) {
    return (
      skeleton ?? (
        <div className="animate-pulse space-y-3" data-testid="loading-skeleton">
          <div className="h-6 rounded bg-ink-700" />
          <div className="h-24 rounded bg-ink-700" />
        </div>
      )
    );
  }
  if (error) {
    return (
      <div className="rounded-lg border border-rust-500/40 bg-rust-500/10 p-3 text-sm text-sand-300" role="alert">
        <p>{error.message}</p>
        {onRetry ? (
          <button
            type="button"
            onClick={onRetry}
            className="mt-2 rounded border border-sand-400/50 px-2 py-1 text-xs text-sand-300 hover:bg-ink-700"
          >
            Retry
          </button>
        ) : null}
      </div>
    );
  }
  if (empty) {
    return <p className="text-sm text-slate-400">{emptyMessage}</p>;
  }
  return <>{children}</>;
}
