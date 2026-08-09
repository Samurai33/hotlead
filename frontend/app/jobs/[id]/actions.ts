"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { backendFetch, ServerApiError } from "@/lib/server-api";

export type JobActionState = { error: string | null };

export async function pauseJobAction(_prev: JobActionState, formData: FormData): Promise<JobActionState> {
  const id = String(formData.get("id") ?? "");
  try {
    await backendFetch(`/api/v1/jobs/${id}/pause`, { method: "POST" });
  } catch (err) {
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
    return { error: err instanceof ServerApiError ? err.detail : "Erro ao deletar job" };
  }
  revalidatePath("/");
  redirect("/");
}
