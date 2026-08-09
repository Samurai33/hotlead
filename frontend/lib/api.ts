// Client-side fetcher for the Client Components that still poll live data
// (job detail, jobs list refresh, accounts list refresh, prospects
// filtering). Goes through the same-origin /api/proxy Route Handler instead
// of the backend directly — the browser holds only the httpOnly session
// cookie (sent automatically, same-origin default), never the raw API key
// (audit AUDIT-2.md M1). Mutations (create/pause/resume/delete) moved to
// Server Actions — see app/jobs/new/actions.ts and app/jobs/[id]/actions.ts.
import type {
  Job,
  JobSummary,
  JobMode,
  Prospect,
  Account,
} from "@/lib/types";

const PROXY_PREFIX = "/api/proxy";

class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

function redirectToLogin(): void {
  if (typeof window !== "undefined") {
    window.location.href = "/login";
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${PROXY_PREFIX}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!res.ok) {
    if (res.status === 401 || res.status === 403) {
      redirectToLogin();
    }
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {}
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

// ─── Jobs ─────────────────────────────────────────────────────

export const jobsApi = {
  list: () => request<JobSummary[]>("/api/v1/jobs"),
  get: (id: string) => request<Job>(`/api/v1/jobs/${id}`),
};

/**
 * Plain URL for the export download — hit with a normal `<a href>` so the
 * browser handles the save-as natively using the backend's
 * Content-Disposition header. The proxy route attaches X-API-Key from the
 * httpOnly cookie server-side; the browser's same-origin GET carries the
 * cookie automatically, same as any other /api/proxy call (audit H4: still
 * header-only auth, never a `?api_key=` query param).
 */
export function exportHref(
  id: string,
  fmt: "csv" | "json",
  filters?: { has_email?: boolean; has_phone?: boolean },
): string {
  const qs = new URLSearchParams({ fmt });
  if (filters?.has_email) qs.set("has_email", "true");
  if (filters?.has_phone) qs.set("has_phone", "true");
  return `${PROXY_PREFIX}/api/v1/jobs/${id}/export?${qs}`;
}

// ─── Prospects ────────────────────────────────────────────────

export const prospectsApi = {
  list: (
    jobId: string,
    params?: { has_email?: boolean; has_phone?: boolean; limit?: number; offset?: number },
  ) => {
    const qs = new URLSearchParams();
    if (params?.has_email != null) qs.set("has_email", String(params.has_email));
    if (params?.has_phone != null) qs.set("has_phone", String(params.has_phone));
    if (params?.limit != null) qs.set("limit", String(params.limit));
    if (params?.offset != null) qs.set("offset", String(params.offset));
    return request<Prospect[]>(`/api/v1/jobs/${jobId}/prospects?${qs}`);
  },
};

// ─── Accounts ─────────────────────────────────────────────────

export const accountsApi = {
  list: () => request<Account[]>("/api/v1/accounts"),
  remove: (id: string) =>
    request<void>(`/api/v1/accounts/${id}`, { method: "DELETE" }),
};

export { ApiError };
export type { JobMode, Prospect, Account };
