"use client";

import { useActionState, useState } from "react";
import { loginAction, type LoginState } from "./actions";
import { Flame, Loader2, Eye, EyeOff } from "lucide-react";

const initialState: LoginState = { error: null };

export default function LoginPage() {
  const [show, setShow] = useState(false);
  const [state, formAction, pending] = useActionState(loginAction, initialState);

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

        <form action={formAction} className="card space-y-4">
          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1.5">
              API Key
            </label>
            <div className="relative">
              <input
                name="key"
                type={show ? "text" : "password"}
                className="input pr-10 font-mono text-xs"
                placeholder="sua-api-key-aqui"
                autoFocus
                required
              />
              <button
                type="button"
                onClick={() => setShow((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text transition-colors"
                aria-label={show ? "Ocultar API key" : "Mostrar API key"}
                aria-pressed={show}
              >
                {show ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
            <p className="text-xs text-text-muted mt-1.5">
              Definida em <code className="font-mono bg-surface px-1 rounded-sm">API_KEY</code> no seu <code className="font-mono bg-surface px-1 rounded-sm">.env</code>
            </p>
          </div>

          {state.error && (
            <p className="text-xs text-status-error bg-status-error/10 px-3 py-2 rounded-md">
              {state.error}
            </p>
          )}

          <button
            type="submit"
            disabled={pending}
            className="btn-primary w-full flex items-center justify-center gap-2"
          >
            {pending && <Loader2 size={14} className="animate-spin" />}
            {pending ? "Verificando..." : "Entrar"}
          </button>
        </form>
      </div>
    </div>
  );
}
