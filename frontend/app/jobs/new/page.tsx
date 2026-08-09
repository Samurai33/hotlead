"use client";

import { useActionState, useState } from "react";
import { createJobAction, type CreateJobState } from "./actions";
import type { JobMode } from "@/lib/types";
import { ArrowLeft, Loader2, Link as LinkIcon } from "lucide-react";
import Link from "next/link";

const MODES: { value: JobMode; label: string; description: string }[] = [
  { value: "followers",  label: "Seguidores",   description: "Extrai quem segue o perfil" },
  { value: "following",  label: "Seguindo",      description: "Extrai quem o perfil segue" },
  { value: "commenters", label: "Comentadores",  description: "Extrai quem comentou em um post específico" },
];

function isInstagramMediaUrl(value: string) {
  try {
    const url = new URL(value.trim());
    const host = url.hostname;
    const parts = url.pathname.split("/").filter(Boolean);

    return (
      ["http:", "https:"].includes(url.protocol) &&
      (host === "instagram.com" || host.endsWith(".instagram.com")) &&
      parts.length >= 2 &&
      ["p", "reel", "tv"].includes(parts[0] ?? "")
    );
  } catch {
    return false;
  }
}

const initialState: CreateJobState = { error: null };

export default function NewJobPage() {
  const [username, setUsername] = useState("");
  const [mode, setMode]         = useState<JobMode>("followers");
  const [postUrl, setPostUrl]   = useState("");
  const [state, formAction, pending] = useActionState(createJobAction, initialState);

  const isCommenters = mode === "commenters";
  const postUrlIsValid = !isCommenters || isInstagramMediaUrl(postUrl);
  const showPostUrlError = isCommenters && Boolean(postUrl.trim()) && !postUrlIsValid;
  const isValid = Boolean(username.trim()) && postUrlIsValid;

  return (
    <div className="min-h-screen bg-background px-6 py-6 max-w-lg mx-auto">
      <Link href="/" className="inline-flex items-center gap-1.5 text-text-muted hover:text-text text-sm mb-6">
        <ArrowLeft size={14} /> Voltar
      </Link>

      <h1 className="text-xl font-semibold mb-1">Novo Job de Scraping</h1>
      <p className="text-text-muted text-sm mb-6">
        Informe o perfil e o tipo de extração.
      </p>

      <form action={formAction} className="space-y-5">
        {/* Username */}
        <div>
          <label className="block text-sm font-medium mb-1.5">Perfil Instagram</label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted font-mono text-sm">@</span>
            <input
              name="username"
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

        {/* Post URL — only shown for commenters mode */}
        {isCommenters && (
          <div>
            <label className="block text-sm font-medium mb-1.5">URL do Post</label>
            <div className="relative">
              <LinkIcon size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
              <input
                name="postUrl"
                className="input pl-8"
                placeholder="https://www.instagram.com/p/ABC123/"
                value={postUrl}
                onChange={(e) => setPostUrl(e.target.value)}
                required={isCommenters}
                type="url"
              />
            </div>
            <p className="text-xs text-text-muted mt-1.5">
              Cole a URL de um post público do Instagram
            </p>
            {showPostUrlError && (
              <p className="text-xs text-status-error mt-1.5">
                Use uma URL do Instagram em /p/, /reel/ ou /tv/.
              </p>
            )}
          </div>
        )}

        {/* Optional cap on how many profiles to scrape */}
        <div>
          <label className="block text-sm font-medium mb-1.5">Limite de perfis (opcional)</label>
          <input
            name="maxCount"
            className="input"
            type="number"
            min={1}
            placeholder="Sem limite"
          />
          <p className="text-xs text-text-muted mt-1.5">
            Deixe em branco para extrair sem limite.
          </p>
        </div>

        {state.error && (
          <p className="text-status-error text-sm bg-status-error/10 px-3 py-2 rounded-md">
            {state.error}
          </p>
        )}

        <button
          type="submit"
          disabled={pending || !isValid}
          className="btn-primary w-full justify-center flex items-center gap-2"
        >
          {pending && <Loader2 size={14} className="animate-spin" />}
          {pending ? "Iniciando..." : "Iniciar Scraping"}
        </button>
      </form>
    </div>
  );
}
