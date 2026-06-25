"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useJobs } from "@/hooks/use-job";
import { jobsApi } from "@/lib/api";
import { clearApiKey } from "@/lib/auth";
import { formatDate, formatNumber, progressPct, STATUS_LABELS } from "@/lib/utils";
import { Plus, RefreshCw, Mail, Users, LogOut } from "lucide-react";

const STATUS_COLORS: Record<string, string> = {
  pending: "text-status-pending bg-status-pending/10",
  running: "text-status-running bg-status-running/10",
  paused:  "text-status-paused  bg-status-paused/10",
  done:    "text-status-done    bg-status-done/10",
  error:   "text-status-error   bg-status-error/10",
};

export default function DashboardPage() {
  const router = useRouter();
  const { jobs, isLoading, mutate } = useJobs();

  function handleLogout() {
    clearApiKey();
    router.replace("/login");
  }

  const stats = {
    total: jobs.length,
    running: jobs.filter((j) => j.status === "running").length,
    emails: jobs.reduce((s, j) => s + j.emails_found, 0),
    prospects: jobs.reduce((s, j) => s + j.scraped_count, 0),
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold font-mono text-brand">HotLead</h1>
          <p className="text-xs text-text-muted mt-0.5">Instagram Lead Extractor</p>
        </div>
        <nav className="flex items-center gap-3">
          <Link href="/accounts" className="btn-ghost text-sm">Contas IG</Link>
          <Link href="/jobs/new" className="btn-primary text-sm flex items-center gap-1.5">
            <Plus size={14} /> Novo Job
          </Link>
          <button
            onClick={handleLogout}
            className="btn-ghost text-sm p-2 text-text-muted hover:text-status-error"
            title="Sair"
          >
            <LogOut size={14} />
          </button>
        </nav>
      </header>

      <main className="px-6 py-6 max-w-6xl mx-auto">
        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          {[
            { label: "Jobs totais", value: stats.total, icon: RefreshCw },
            { label: "Executando",  value: stats.running, icon: RefreshCw },
            { label: "Prospects",   value: formatNumber(stats.prospects), icon: Users },
            { label: "E-mails",     value: formatNumber(stats.emails), icon: Mail },
          ].map(({ label, value, icon: Icon }) => (
            <div key={label} className="card-elevated">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-text-muted">{label}</span>
                <Icon size={14} className="text-text-muted" />
              </div>
              <p className="text-2xl font-mono font-semibold text-text">{value}</p>
            </div>
          ))}
        </div>

        {/* Jobs table */}
        <div className="card overflow-hidden p-0">
          <div className="px-4 py-3 border-b border-border flex items-center justify-between">
            <h2 className="text-sm font-medium text-text-secondary">Jobs</h2>
            <button onClick={() => mutate()} className="btn-ghost text-xs">
              Atualizar
            </button>
          </div>

          {isLoading ? (
            <div className="px-4 py-8 text-center text-text-muted text-sm">
              Carregando...
            </div>
          ) : jobs.length === 0 ? (
            <div className="px-4 py-12 text-center">
              <p className="text-text-muted text-sm mb-3">Nenhum job ainda.</p>
              <Link href="/jobs/new" className="btn-primary text-sm inline-flex items-center gap-1.5">
                <Plus size={14} /> Criar primeiro job
              </Link>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  {["Perfil", "Modo", "Status", "Progresso", "E-mails", "Criado"].map((h) => (
                    <th key={h} className="px-4 py-2.5 text-left text-xs text-text-muted font-medium">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr
                    key={job.id}
                    className="border-b border-border/50 hover:bg-surface-elevated/50 cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3">
                      <Link href={`/jobs/${job.id}`} className="font-mono text-brand hover:underline">
                        @{job.profile_username}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-text-secondary capitalize">{job.mode}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[job.status]}`}>
                        {STATUS_LABELS[job.status]}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-surface h-1.5 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-brand rounded-full transition-all"
                            style={{ width: `${progressPct(job.scraped_count, job.scraped_count)}%` }}
                          />
                        </div>
                        <span className="text-xs text-text-muted font-mono">
                          {formatNumber(job.scraped_count)}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 font-mono text-brand">{formatNumber(job.emails_found)}</td>
                    <td className="px-4 py-3 text-text-muted text-xs">{formatDate(job.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </main>
    </div>
  );
}
