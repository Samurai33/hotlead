import { redirect } from "next/navigation";
import { backendFetch, ServerApiError } from "@/lib/server-api";
import type { Job } from "@/lib/types";
import JobDetailClient from "@/components/jobs/JobDetailClient";

// Server Component initial fetch (audit AUDIT-2.md L6). Pause/resume/delete
// are Server Actions in ./actions.ts (audit L10 — collapses the old
// hand-rolled useState(loading)/useState(error) trio into useActionState).
export default async function JobDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  let initialJob: Job | undefined;
  try {
    initialJob = await backendFetch<Job>(`/api/v1/jobs/${id}`);
  } catch (err) {
    if (err instanceof ServerApiError && (err.status === 401 || err.status === 403)) {
      redirect("/login");
    }
    // 404 or a transient backend hiccup — JobDetailClient's client-side SWR
    // poll will resolve it (and render the "não encontrado" state if it's
    // really gone).
  }

  return <JobDetailClient id={id} initialJob={initialJob} />;
}
