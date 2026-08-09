"use server";

import { redirect } from "next/navigation";
import { setSessionCookie } from "@/lib/session";
import { resolveApiUrl } from "@/lib/api-url";

export type LoginState = { error: string | null };

// Validated against a real authenticated route (not /health, which has no
// auth at all — main.py mounts it outside api_v1_router's require_api_key
// dependency, so hitting it never actually proved the key was valid).
export async function loginAction(_prevState: LoginState, formData: FormData): Promise<LoginState> {
  const key = String(formData.get("key") ?? "").trim();
  if (!key) return { error: "Informe a API key." };

  let res: Response;
  try {
    res = await fetch(`${resolveApiUrl()}/api/v1/jobs`, {
      headers: { "X-API-Key": key },
      cache: "no-store",
    });
  } catch {
    return { error: "Não foi possível conectar ao backend. Tente novamente." };
  }

  if (res.status === 401 || res.status === 403) {
    return { error: "API key inválida. Verifique e tente novamente." };
  }
  if (!res.ok) {
    return { error: `Erro do backend: HTTP ${res.status}` };
  }

  await setSessionCookie(key);
  redirect("/");
}
