"use client";

import { use, useState } from "react";
import Link from "next/link";
import useSWR from "swr";
import { prospectsApi, jobsApi, type Prospect } from "@/lib/api";
import { formatDate, formatNumber } from "@/lib/utils";
import { ArrowLeft, Download, Mail, Phone, Globe, Filter, ChevronLeft, ChevronRight } from "lucide-react";

const PAGE_SIZE = 100;

export default function ProspectsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: jobId } = use(params);
  const [hasEmail, setHasEmail] = useState<boolean | null>(null);
  const [hasPhone, setHasPhone] = useState<boolean | null>(null);
  const [page, setPage] = useState(0);

  const { data: job }       = useSWR(`job-${jobId}`, () => jobsApi.get(jobId));
  const { data: prospects, isLoading } = useSWR(
    `prospects-${jobId}-${hasEmail}-${hasPhone}-${page}`,
    () => prospectsApi.list(jobId, {
      has_email: hasEmail ?? undefined,
      has_phone: hasPhone ?? undefined,
      limit: PAGE_SIZE,
      offset: page * PAGE_SIZE,
    }),
    { keepPreviousData: true },
  );

  const exportUrl = (fmt: "csv" | "json") => {
    const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const key  = typeof window !== "undefined" ? localStorage.getItem("hotlead_api_key") ?? "" : "";
    let url = `${base}/api/v1/jobs/${jobId}/export?fmt=${fmt}`;
    if (hasEmail) url += "&has_email=true";
    return url;
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href={`/jobs/${jobId}`} className="btn-ghost p-1.5">
            <ArrowLeft size={15} />
          </Link>
          <div>
            <h1 className="text-sm font-semibold font-mono">
              Prospects — @{job?.profile_username ?? "…"}
            </h1>
            <p className="text-xs text-text-muted">
              {formatNumber(job?.scraped_count ?? 0)} encontrados ·{" "}
              {formatNumber(job?.emails_found ?? 0)} com e-mail
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <a href={exportUrl("csv")} download className="btn-ghost text-xs flex items-center gap-1.5">
            <Download size={12} /> CSV
          </a>
          <a href={exportUrl("json")} download className="btn-ghost text-xs flex items-center gap-1.5">
            <Download size={12} /> JSON
          </a>
        </div>
      </header>

      <main className="px-6 py-4 max-w-7xl mx-auto">
        {/* Filters */}
        <div className="flex items-center gap-3 mb-4">
          <Filter size={13} className="text-text-muted" />
          <span className="text-xs text-text-muted">Filtrar:</span>
          {[
            { label: "Com e-mail", active: hasEmail === true, onClick: () => { setHasEmail(v => v === true ? null : true); setPage(0); } },
            { label: "Com telefone", active: hasPhone === true, onClick: () => { setHasPhone(v => v === true ? null : true); setPage(0); } },
          ].map(({ label, active, onClick }) => (
            <button
              key={label}
              onClick={onClick}
              className={`text-xs px-3 py-1 rounded-full border transition-colors ${
                active
                  ? "border-brand bg-brand/10 text-brand"
                  : "border-border text-text-secondary hover:border-brand/50"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Table */}
        <div className="card overflow-hidden p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-surface-elevated/50">
                {["Usuário", "Nome", "E-mail", "Telefone", "Website", "Seguidores", "Extraído"].map(h => (
                  <th key={h} className="px-3 py-2.5 text-left text-xs text-text-muted font-medium whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan={7} className="px-3 py-8 text-center text-text-muted text-xs">Carregando...</td></tr>
              ) : !prospects?.length ? (
                <tr><td colSpan={7} className="px-3 py-8 text-center text-text-muted text-xs">Nenhum prospect encontrado.</td></tr>
              ) : (
                prospects.map((p: Prospect) => (
                  <tr key={p.id} className="border-b border-border/40 hover:bg-surface-elevated/30 transition-colors">
                    <td className="px-3 py-2 font-mono text-xs text-brand">@{p.username}</td>
                    <td className="px-3 py-2 text-xs text-text-secondary max-w-[160px] truncate">{p.full_name ?? "—"}</td>
                    <td className="px-3 py-2 text-xs">
                      {p.email ? (
                        <a href={`mailto:${p.email}`} className="flex items-center gap-1 text-brand hover:underline">
                          <Mail size={10} /> {p.email}
                        </a>
                      ) : <span className="text-text-muted">—</span>}
                    </td>
                    <td className="px-3 py-2 text-xs">
                      {p.phone ? (
                        <span className="flex items-center gap-1 text-text-secondary">
                          <Phone size={10} /> {p.phone}
                        </span>
                      ) : <span className="text-text-muted">—</span>}
                    </td>
                    <td className="px-3 py-2 text-xs max-w-[180px] truncate">
                      {p.website ? (
                        <a href={p.website} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-text-secondary hover:text-brand">
                          <Globe size={10} /> {p.website.replace(/^https?:\/\//, "")}
                        </a>
                      ) : <span className="text-text-muted">—</span>}
                    </td>
                    <td className="px-3 py-2 text-xs font-mono text-text-secondary text-right">{formatNumber(p.followers)}</td>
                    <td className="px-3 py-2 text-xs text-text-muted whitespace-nowrap">{formatDate(p.created_at)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between mt-4">
          <p className="text-xs text-text-muted">
            Página {page + 1} · {PAGE_SIZE} por página
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage(p => Math.max(0, p - 1))}
              disabled={page === 0}
              className="btn-ghost p-1.5 disabled:opacity-30"
            >
              <ChevronLeft size={14} />
            </button>
            <button
              onClick={() => setPage(p => p + 1)}
              disabled={!prospects || prospects.length < PAGE_SIZE}
              className="btn-ghost p-1.5 disabled:opacity-30"
            >
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
