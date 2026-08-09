import Link from "next/link";
import { SearchX } from "lucide-react";

export default function NotFound() {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-6">
      <div className="card-elevated text-center max-w-sm">
        <SearchX size={24} className="text-text-muted mx-auto mb-3" aria-hidden="true" />
        <p className="text-sm font-medium text-text mb-1">Página não encontrada</p>
        <p className="text-xs text-text-muted mb-4">
          O endereço acessado não existe ou foi removido.
        </p>
        <Link href="/" className="btn-ghost text-xs inline-block">
          Voltar ao início
        </Link>
      </div>
    </div>
  );
}
