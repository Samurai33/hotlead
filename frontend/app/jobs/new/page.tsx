"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { jobsApi, type JobMode } from "@/lib/api";
import { ArrowLeft, Loader2 } from "lucide-react";
import Link from "next/link";

const MODES: { value: JobMode; label: string; description: string }[] = [
  { value: "followers",  label: "Seguidores",   description: "Extrai quem segue o perfil" },
  { value: "following",  label: "Seguindo",      description: "Extrai quem o perfil segue" },
  { value: "commenters", label: "Comentadores",  description: "Extrai quem comentou nos posts" },
];

export default function NewJobPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [mode, setMode]         = useState<JobMode>("followers");
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!username.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const job = await jobsApi.create({ profile_username: username, mode });
      router.push(`/jobs/${job.id}`);
    } catch (err: any) {
      setError(err.detail ?? "Erro ao criar job");
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-background px-6 py-6 max-w-lg mx-auto">
      <Link href="/" className="inline-flex items-center gap-1.5 text-text-muted hover:text-text text-sm mb-6">
        <ArrowLeft size={14} /> Voltar
      </Link>

      <h1 className="text-xl font-semibold mb-1">Novo Job de Scraping</h1>
      <p className="text-text-muted text-sm mb-6">
        Informe o perfil e o tipo de extração.
      </p>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Username */}
        <div>
          <label className="block text-sm font-medium mb-1.5">Perfil Instagram</label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted font-mono text-sm">@</span>
            <input
              className="input pl-7"
              placeholder="cozinha4e20"
              value={username}
              onChange={(e) => setUsername(e.target.value.replace(/^@/, ""))}
              required
              autoFocus
            />
          </div>
        </div>

        {/* Mode */}
        <div>
          <label className="block text-sm font-medium mb-1.5">Modo</label>
          <div className="space-y-2">
            {MODES.map((m) => (
              <label
                key={m.value}
                className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                  mode === m.value
                    ? "border-brand bg-brand/5"
                    : "border-border hover:border-border/80"
                }`}
              >
                <input
                  type="radio"
                  name="mode"
                  value={m.value}
                  checked={mode === m.value}
                  onChange={() => setMode(m.value)}
                  className="mt-0.5 accent-brand"
                />
                <div>
                  <p className="text-sm font-medium">{m.label}</p>
                  <p className="text-xs text-text-muted">{m.description}</p>
                </div>
              </label>
            ))}
          </div>
        </div>

        {error && (
          <p className="text-status-error text-sm bg-status-error/10 px-3 py-2 rounded-md">
            {error}
          </p>
        )}

        <button type="submit" disabled={loading || !username.trim()} className="btn-primary w-full justify-center flex items-center gap-2">
          {loading && <Loader2 size={14} className="animate-spin" />}
          {loading ? "Iniciando..." : "Iniciar Scraping"}
        </button>
      </form>
    </div>
  );
}
