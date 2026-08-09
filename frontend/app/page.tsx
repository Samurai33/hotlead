import { redirect } from "next/navigation";
import { backendFetch, ServerApiError } from "@/lib/server-api";
import type { JobSummary } from "@/lib/types";
import DashboardClient from "@/components/dashboard/DashboardClient";

// Server Component: fetches the jobs list server-side using the httpOnly
// session cookie, so the initial paint streams real data instead of the
// old hydrate-then-fetch waterfall every route used to have (audit
// AUDIT-2.md L6 — a direct consequence of M1's localStorage-only key, which
// no Server Component could read). DashboardClient takes over client-side
// for the 5s live poll and the refresh/logout controls.
export default async function DashboardPage() {
  let jobs: JobSummary[] = [];
  try {
    jobs = await backendFetch<JobSummary[]>("/api/v1/jobs");
  } catch (err) {
    if (err instanceof ServerApiError && (err.status === 401 || err.status === 403)) {
      redirect("/login");
    }
    // Backend unreachable — render empty, client-side poll will retry.
  }

  return <DashboardClient initialJobs={jobs} />;
}
