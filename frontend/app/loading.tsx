import { Loader2 } from "lucide-react";

export default function Loading() {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <div className="flex items-center gap-2 text-text-muted text-sm">
        <Loader2 size={16} className="animate-spin" aria-hidden="true" />
        Carregando...
      </div>
    </div>
  );
}
