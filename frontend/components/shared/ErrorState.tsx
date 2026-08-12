"use client";

import { AlertCircle, RefreshCw } from "lucide-react";

/**
 * Inline error + retry block for SWR-backed views. Distinguishes a real
 * fetch failure (network down, backend 5xx, etc.) from "no data yet" so
 * callers stop mislabeling it as an empty state or a 404 (audit FE-C1).
 *
 * Mirrors the `card border-status-error/30 bg-status-error/5` treatment
 * already used for job/account error blocks elsewhere in this codebase.
 */
export function ErrorState({
  message = "Não foi possível carregar os dados.",
  onRetry,
}: {
  message?: string;
  onRetry: () => void;
}) {
  return (
    <div className="card border-status-error/30 bg-status-error/5 flex items-center justify-between gap-4">
      <div className="flex items-center gap-2 min-w-0">
        <AlertCircle size={14} className="text-status-error shrink-0" />
        <p className="text-xs text-status-error">{message}</p>
      </div>
      <button
        onClick={onRetry}
        className="btn-ghost text-xs flex items-center gap-1.5 shrink-0"
      >
        <RefreshCw size={12} /> Tentar novamente
      </button>
    </div>
  );
}
