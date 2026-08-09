"use client";

import { useEffect } from "react";
import { AlertCircle } from "lucide-react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-6">
      <div className="card border-status-error/30 bg-status-error/5 text-center max-w-sm">
        <AlertCircle size={24} className="text-status-error mx-auto mb-3" aria-hidden="true" />
        <p className="text-sm font-medium text-status-error mb-1">Algo deu errado</p>
        <p className="text-xs text-text-muted mb-4 break-words">{error.message || "Erro inesperado."}</p>
        <button onClick={reset} className="btn-ghost text-xs">
          Tentar novamente
        </button>
      </div>
    </div>
  );
}
