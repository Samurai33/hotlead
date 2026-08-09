"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { backendFetch, ServerApiError } from "@/lib/server-api";
import type { Job, JobMode } from "@/lib/types";

export type CreateJobState = { error: string | null };

export async function createJobAction(_prev: CreateJobState, formData: FormData): Promise<CreateJobState> {
  const profile_username = String(formData.get("username") ?? "").trim();
  const mode = String(formData.get("mode") ?? "followers") as JobMode;
  const target_post_url = String(formData.get("postUrl") ?? "").trim();
  const maxCountRaw = String(formData.get("maxCount") ?? "").trim();

  if (!profile_username) {
    return { error: "Informe o perfil do Instagram." };
  }
  if (mode === "commenters" && !target_post_url) {
    return { error: "Informe a URL de um post, reel ou tv do Instagram." };
  }

  let job: Job;
  try {
    job = await backendFetch<Job>("/api/v1/jobs", {
      method: "POST",
      body: JSON.stringify({
        profile_username,
        mode,
        ...(mode === "commenters" ? { target_post_url } : {}),
        ...(maxCountRaw ? { max_count: Number(maxCountRaw) } : {}),
      }),
    });
  } catch (err) {
    return { error: err instanceof ServerApiError ? err.detail : "Erro ao criar job" };
  }

  revalidatePath("/");
  redirect(`/jobs/${job.id}`);
}
