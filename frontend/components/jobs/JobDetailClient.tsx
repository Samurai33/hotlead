"use client";

import { useActionState, useEffect, useRef } from "react";
import Link from "next/link";
import { useJob } from "@/hooks/use-job";
import { pauseJobAction, resumeJobAction, deleteJobAction, type JobActionState } from "@/app/jobs/[id]/actions";
import {
  formatDate, formatNumber, progressPct, STATUS_LABELS,
} from "@/lib/utils";
import type { Job } from "@/lib/types";
import {
  ArrowLeft, Pause, Play, Trash2, Download, Users, Mail, Phone, ExternalLink, Loader2,
} from "lucide-react";

const STATUS_COLORS: Record<string, string> = {
  pending: "text-status-pending",
  running: "text-status-running",
  paused:  "text-status-paused",
  done:    "text-status-done",
  error:   "text-status-error",
};

const initialActionState: JobActionState = { error: null };

/** Fires `mutate()` on the falling edge of `pending` so the SWR-backed view
 * refreshes right after a Server Action completes, instead of waiting for
 * the next poll tick. */
function useMutateOnSettle(pending: boolean, mutate: () => void) {
  const wasPending = useRef(false);
  useEffect(() => {
    if (pending) {
      wasPending.current = true;
    } else if (wasPending.current) {
      wasPending.current = false;
      mutate();
    }
  }, [pending, mutate]);
}

export default function JobDetailClient({ id, initialJob }: { id: string; initialJob?: Job }) {
  const { job, isLoading, mutate } = useJob(id, initialJob);

  const [pauseState, pauseAction, pausePending] = useActionState(pauseJobAction, initialActionState);
  const [resumeState, resumeAction, resumePending] = useActionState(resumeJobAction, initialActionState);
  const [deleteState, deleteAction, deletePending] = useActionState(deleteJobAction, initialActionState);

  useMutateOnSettle(pausePending, mutate);
  useMutateOnSettle(resumePending, mutate);

  const actionError = pauseState.error ?? resumeState.error ?? deleteState.error;

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
            <form action={pauseAction}>
              <input type="hidden" name="id" value={id} />
              <button type="submit" disabled={pausePending} className="btn-ghost text-sm flex items-center gap-1.5">
                {pausePending ? <Loader2 size={13} className="animate-spin" /> : <Pause size={13} />} Pausar
              </button>
            </form>
          )}
          {job.status === "paused" && (
            <form action={resumeAction}>
              <input type="hidden" name="id" value={id} />
              <button type="submit" disabled={resumePending} className="btn-ghost text-sm flex items-center gap-1.5">
                {resumePending ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />} Retomar
              </button>
            </form>
          )}
          {job.status === "done" && (
            <Link
              href={`/jobs/${id}/prospects`}
              className="btn-primary text-sm flex items-center gap-1.5"
            >
              <Download size={13} /> Ver Prospects
            </Link>
          )}
          <form
            action={deleteAction}
            onSubmit={(e) => {
              if (!confirm("Deletar este job e todos os prospects? Esta ação não pode ser desfeita.")) {
                e.preventDefault();
              }
            }}
          >
            <input type="hidden" name="id" value={id} />
            <button
              type="submit"
              disabled={deletePending}
              className="btn-ghost text-sm text-status-error hover:text-status-error"
              aria-label="Deletar job"
              title="Deletar job"
            >
              {deletePending ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
            </button>
          </form>
        </div>
      </div>

      {actionError && (
        <div className="card border-status-error/30 bg-status-error/5 mb-4">
          <p className="text-xs text-status-error">{actionError}</p>
        </div>
      )}

      {/* Progress */}
      <div className="card mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-text-muted">Progresso</span>
          <span className="text-xs font-mono text-text-secondary">{pct}%</span>
        </div>
        <div
          className="w-full bg-surface-elevated h-2 rounded-full overflow-hidden"
          role="progressbar"
          aria-label="Progresso do job"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={pct}
        >
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
        {job.mode === "commenters" && job.target_post_url && (
          <div className="flex justify-between gap-4">
            <span>Post</span>
            <a
              href={job.target_post_url}
              target="_blank"
              rel="noreferrer"
              className="min-w-0 inline-flex items-center gap-1 font-mono text-brand hover:underline"
            >
              <span className="truncate">{job.target_post_url}</span>
              <ExternalLink size={12} className="shrink-0" />
            </a>
          </div>
        )}
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
