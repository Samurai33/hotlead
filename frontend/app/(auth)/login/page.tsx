"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { setApiKey, hasApiKey } from "@/lib/auth";
import { Flame, Loader2, Eye, EyeOff } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const [key, setKey]         = useState("");
  const [show, setShow]       = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState<string | null>(null);

  useEffect(() => {
    if (hasApiKey()) router.replace("/");
  }, [router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!key.trim()) return;
    setLoading(true);
    setError(null);

    // Validate the key against the backend before saving
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/health`,
        { headers: { "X-API-Key": key.trim() } },
      );
      if (res.status === 401 || res.status === 403) {
        setError("API key inválida. Verifique e tente novamente.");
        setLoading(false);
        return;
      }
      setApiKey(key.trim());
      router.replace("/");
    } catch {
      // If backend is unreachable, save the key anyway — will fail on first request
      setApiKey(key.trim());
      router.replace("/");
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-brand/10 border border-brand/20 mb-4">
            <Flame size={24} className="text-brand" />
          </div>
          <h1 className="text-2xl font-mono font-semibold text-text">HotLead</h1>
          <p className="text-sm text-text-muted mt-1">Insira sua API key para continuar</p>
        </div>

        <form onSubmit={handleSubmit} className="card space-y-4">
          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1.5">
              API Key
            </label>
            <div className="relative">
              <input
                type={show ? "text" : "password"}
                className="input pr-10 font-mono text-xs"
                placeholder="sua-api-key-aqui"
                value={key}
                onChange={(e) => setKey(e.target.value)}
                autoFocus
                required
              />
              <button
                type="button"
                onClick={() => setShow((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text transition-colors"
                tabIndex={-1}
              >
                {show ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
            <p className="text-xs text-text-muted mt-1.5">
              Definida em <code className="font-mono bg-surface px-1 rounded-sm">API_KEY</code> no seu <code className="font-mono bg-surface px-1 rounded-sm">.env</code>
            </p>
          </div>

          {error && (
            <p className="text-xs text-status-error bg-status-error/10 px-3 py-2 rounded-md">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading || !key.trim()}
            className="btn-primary w-full flex items-center justify-center gap-2"
          >
            {loading && <Loader2 size={14} className="animate-spin" />}
            {loading ? "Verificando..." : "Entrar"}
          </button>
        </form>
      </div>
    </div>
  );
}
