"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useJob } from "@/hooks/use-job";
import { jobsApi } from "@/lib/api";
import {
  formatDate, formatNumber, progressPct, STATUS_LABELS,
} from "@/lib/utils";
import {
  ArrowLeft, Pause, Play, Trash2, Download, Users, Mail, Phone,
} from "lucide-react";

const STATUS_COLORS: Record<string, string> = {
  pending: "text-status-pending",
  running: "text-status-running",
  paused:  "text-status-paused",
  done:    "text-status-done",
  error:   "text-status-error",
};

export default function JobDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { job, isLoading, mutate } = useJob(id);
  const [acting, setActing] = useState(false);

  async function handlePause() {
    setActing(true);
    await jobsApi.pause(id);
    await mutate();
    setActing(false);
  }

  async function handleResume() {
    setActing(true);
    await jobsApi.resume(id);
    await mutate();
    setActing(false);
  }

  async function handleDelete() {
    if (!confirm("Deletar este job e todos os prospects? Esta ação não pode ser desfeita.")) return;
    await jobsApi.delete(id);
    window.location.href = "/";
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <p className="text-text-muted text-sm">Carregando...</p>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <p className="text-status-error text-sm">Job não encontrado.</p>
      </div>
    );
  }

  const pct = progressPct(job.scraped_count, job.total_count);

  return (
    <div className="min-h-screen bg-background px-6 py-6 max-w-3xl mx-auto">
      <Link href="/" className="inline-flex items-center gap-1.5 text-text-muted hover:text-text text-sm mb-6">
        <ArrowLeft size={14} /> Dashboard
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-mono font-semibold text-brand">@{job.profile_username}</h1>
          <div className="flex items-center gap-3 mt-1">
            <span className="text-xs text-text-muted capitalize">{job.mode}</span>
            <span className={`text-xs font-medium ${STATUS_COLORS[job.status]}`}>
              ● {STATUS_LABELS[job.status]}
            </span>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          {job.status === "running" && (
            <button onClick={handlePause} disabled={acting} className="btn-ghost text-sm flex items-center gap-1.5">
              <Pause size={13} /> Pausar
            </button>
          )}
          {job.status === "paused" && (
            <button onClick={handleResume} disabled={acting} className="btn-ghost text-sm flex items-center gap-1.5">
              <Play size={13} /> Retomar
            </button>
          )}
          {job.status === "done" && (
            <Link
              href={`/jobs/${id}/prospects`}
              className="btn-primary text-sm flex items-center gap-1.5"
            >
              <Download size={13} /> Ver Prospects
            </Link>
          )}
          <button onClick={handleDelete} className="btn-ghost text-sm text-status-error hover:text-status-error">
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      {/* Progress */}
      <div className="card mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-text-muted">Progresso</span>
          <span className="text-xs font-mono text-text-secondary">{pct}%</span>
        </div>
        <div className="w-full bg-surface-elevated h-2 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              job.status === "error" ? "bg-status-error" : "bg-brand"
            }`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <p className="text-xs text-text-muted mt-2 font-mono">
          {formatNumber(job.scraped_count)}
          {job.total_count > 0 && ` / ${formatNumber(job.total_count)}`}
          {" "}perfis analisados
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        {[
          { icon: Users, label: "Prospects", value: job.scraped_count },
          { icon: Mail,  label: "E-mails",   value: job.emails_found },
          { icon: Phone, label: "Telefones", value: job.phones_found },
        ].map(({ icon: Icon, label, value }) => (
          <div key={label} className="card-elevated text-center">
            <Icon size={16} className="text-text-muted mx-auto mb-1" />
            <p className="text-xl font-mono font-semibold text-text">{formatNumber(value)}</p>
            <p className="text-xs text-text-muted">{label}</p>
          </div>
        ))}
      </div>

      {/* Error */}
      {job.error_message && (
        <div className="card border-status-error/30 bg-status-error/5 mb-4">
          <p className="text-xs font-medium text-status-error mb-1">Erro</p>
          <p className="text-xs text-text-muted font-mono">{job.error_message}</p>
        </div>
      )}

      {/* Meta */}
      <div className="card text-xs text-text-muted space-y-1">
        <div className="flex justify-between">
          <span>ID</span>
          <span className="font-mono">{job.id}</span>
        </div>
        <div className="flex justify-between">
          <span>Criado</span>
          <span>{formatDate(job.created_at)}</span>
        </div>
        <div className="flex justify-between">
          <span>Atualizado</span>
          <span>{formatDate(job.updated_at)}</span>
        </div>
      </div>
    </div>
  );
}
