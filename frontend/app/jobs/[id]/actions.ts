"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { backendFetch, ServerApiError } from "@/lib/server-api";
import { clearSessionCookie } from "@/lib/session";

export type JobActionState = { error: string | null };

// A 401/403 here means the session cookie is stale/rotated (same signal the
// /api/proxy route handler and the page.tsx Server Components already act
// on) — clear it and bounce to /login instead of surfacing the backend's
// "unauthorized" detail as if it were a pause/resume/delete failure (audit
// FE-C1/F1).
async function handleAuthFailure(err: unknown): Promise<void> {
  if (err instanceof ServerApiError && (err.status === 401 || err.status === 403)) {
    await clearSessionCookie();
    redirect("/login");
  }
}

export async function pauseJobAction(_prev: JobActionState, formData: FormData): Promise<JobActionState> {
  const id = String(formData.get("id") ?? "");
  try {
    await backendFetch(`/api/v1/jobs/${id}/pause`, { method: "POST" });
  } catch (err) {
    await handleAuthFailure(err);
    return { error: err instanceof ServerApiError ? err.detail : "Erro ao pausar job" };
  }
  revalidatePath(`/jobs/${id}`);
  return { error: null };
}

export async function resumeJobAction(_prev: JobActionState, formData: FormData): Promise<JobActionState> {
  const id = String(formData.get("id") ?? "");
  try {
    await backendFetch(`/api/v1/jobs/${id}/resume`, { method: "POST" });
  } catch (err) {
    await handleAuthFailure(err);
    return { error: err instanceof ServerApiError ? err.detail : "Erro ao retomar job" };
  }
  revalidatePath(`/jobs/${id}`);
  return { error: null };
}

export async function deleteJobAction(_prev: JobActionState, formData: FormData): Promise<JobActionState> {
  const id = String(formData.get("id") ?? "");
  try {
    await backendFetch(`/api/v1/jobs/${id}`, { method: "DELETE" });
  } catch (err) {
    await handleAuthFailure(err);
    return { error: err instanceof ServerApiError ? err.detail : "Erro ao deletar job" };
  }
  revalidatePath("/");
  redirect("/");
}
