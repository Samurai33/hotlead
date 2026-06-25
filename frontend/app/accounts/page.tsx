"use client";

import Link from "next/link";
import useSWR from "swr";
import { accountsApi, type Account } from "@/lib/api";
import { formatDate, formatNumber } from "@/lib/utils";
import { ArrowLeft, Trash2, RefreshCw, AlertCircle, CheckCircle, Clock } from "lucide-react";
import { useState } from "react";

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: typeof CheckCircle }> = {
  active:   { label: "Ativo",     color: "text-green-400",  icon: CheckCircle },
  cooldown: { label: "Cooldown",  color: "text-yellow-400", icon: Clock },
  banned:   { label: "Banido",    color: "text-red-400",    icon: AlertCircle },
};

function AccountCard({ account, onDelete }: { account: Account; onDelete: () => void }) {
  const [deleting, setDeleting] = useState(false);
  const cfg = STATUS_CONFIG[account.status] ?? STATUS_CONFIG.active;
  const Icon = cfg.icon;

  async function handleDelete() {
    if (!confirm(`Remover @${account.username} do pool?`)) return;
    setDeleting(true);
    try {
      await accountsApi.remove(account.id);
      onDelete();
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="card flex items-center justify-between gap-4">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-full bg-surface-elevated flex items-center justify-center font-mono text-sm text-brand font-semibold">
          {account.username[0].toUpperCase()}
        </div>
        <div>
          <p className="font-mono text-sm font-medium text-text">@{account.username}</p>
          <p className="text-xs text-text-muted mt-0.5">
            {account.last_used_at ? `Último uso: ${formatDate(account.last_used_at)}` : "Nunca usado"}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <div className="text-right">
          <p className="text-xs text-text-muted">Requests hoje</p>
          <p className="text-sm font-mono font-medium text-text">{formatNumber(account.requests_today)}</p>
        </div>

        {account.cooldown_until && account.status === "cooldown" && (
          <div className="text-right">
            <p className="text-xs text-text-muted">Cooldown até</p>
            <p className="text-xs font-mono text-yellow-400">{formatDate(account.cooldown_until)}</p>
          </div>
        )}

        <div className="flex items-center gap-1.5">
          <Icon size={13} className={cfg.color} />
          <span className={`text-xs font-medium ${cfg.color}`}>{cfg.label}</span>
        </div>

        {account.proxy_url && (
          <span className="text-xs text-text-muted bg-surface-elevated px-2 py-0.5 rounded font-mono">
            proxy
          </span>
        )}

        <button
          onClick={handleDelete}
          disabled={deleting}
          className="btn-ghost text-status-error hover:text-status-error p-1.5"
          title="Remover conta"
        >
          <Trash2 size={13} />
        </button>
      </div>
    </div>
  );
}

export default function AccountsPage() {
  const { data: accounts, isLoading, mutate } = useSWR(
    "accounts",
    accountsApi.list,
    { refreshInterval: 10000 },
  );

  const active   = accounts?.filter(a => a.status === "active").length ?? 0;
  const cooldown = accounts?.filter(a => a.status === "cooldown").length ?? 0;
  const banned   = accounts?.filter(a => a.status === "banned").length ?? 0;

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/" className="btn-ghost p-1.5">
            <ArrowLeft size={15} />
          </Link>
          <div>
            <h1 className="text-sm font-semibold font-mono">Contas Instagram</h1>
            <p className="text-xs text-text-muted">Pool de contas para scraping</p>
          </div>
        </div>
        <button onClick={() => mutate()} className="btn-ghost text-xs flex items-center gap-1.5">
          <RefreshCw size={12} /> Atualizar
        </button>
      </header>

      <main className="px-6 py-6 max-w-3xl mx-auto">
        {/* Stats */}
        <div className="grid grid-cols-3 gap-3 mb-6">
          {[
            { label: "Ativas",    value: active,   color: "text-green-400" },
            { label: "Cooldown",  value: cooldown, color: "text-yellow-400" },
            { label: "Banidas",   value: banned,   color: "text-red-400" },
          ].map(({ label, value, color }) => (
            <div key={label} className="card-elevated text-center">
              <p className={`text-2xl font-mono font-semibold ${color}`}>{value}</p>
              <p className="text-xs text-text-muted mt-0.5">{label}</p>
            </div>
          ))}
        </div>

        {/* Empty state */}
        {!isLoading && (!accounts || accounts.length === 0) && (
          <div className="card border-yellow-500/30 bg-yellow-500/5 mb-6">
            <div className="flex gap-3">
              <AlertCircle size={16} className="text-yellow-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-yellow-400">Nenhuma conta no pool</p>
                <p className="text-xs text-text-muted mt-1">
                  Sem contas ativas, o scraping não funciona. Adicione uma conta com:
                </p>
                <code className="block mt-2 text-xs bg-surface px-3 py-2 rounded font-mono text-text-secondary">
                  docker compose exec api python scripts/add_account.py seu_username
                </code>
              </div>
            </div>
          </div>
        )}

        {/* Accounts list */}
        <div className="space-y-2">
          {isLoading ? (
            <p className="text-text-muted text-sm text-center py-8">Carregando...</p>
          ) : (
            accounts?.map(account => (
              <AccountCard key={account.id} account={account} onDelete={mutate} />
            ))
          )}
        </div>

        {/* Instructions */}
        <div className="card mt-6">
          <p className="text-xs font-medium text-text-secondary mb-2">Como adicionar conta</p>
          <div className="space-y-1.5 text-xs text-text-muted font-mono">
            <p className="text-text-secondary"># Via script (recomendado — senha não fica em logs)</p>
            <p>docker compose exec api python scripts/add_account.py @username</p>
            <p className="text-text-secondary mt-2"># Com proxy</p>
            <p>docker compose exec api python scripts/add_account.py @username --proxy http://user:pass@host:port</p>
          </div>
        </div>
      </main>
    </div>
  );
}
