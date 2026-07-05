import { getApiKey, redirectToLogin } from "@/lib/auth";

function resolveApiUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  // The origin is served over http (Coolify/Traefik) and Cloudflare terminates
  // TLS at the edge, so the baked value can be http://<public-host>. The app is
  // served over https, so upgrade any non-local http URL to https — otherwise
  // the browser blocks the API calls as mixed content.
  if (raw.startsWith("http://") && !/(localhost|127\.0\.0\.1)/.test(raw)) {
    return raw.replace(/^http:\/\//, "https://");
  }
  return raw;
}

const API_URL = resolveApiUrl();

class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": getApiKey(),
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

export type JobMode = "followers" | "following" | "commenters";
export type JobStatus = "pending" | "running" | "paused" | "done" | "error";

export interface Job {
  id: string;
  profile_username: string;
  mode: JobMode;
  status: JobStatus;
  total_count: number;
  scraped_count: number;
  emails_found: number;
  phones_found: number;
  target_post_url: string | null;
  celery_task_id: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface JobSummary {
  id: string;
  profile_username: string;
  mode: JobMode;
  status: JobStatus;
  scraped_count: number;
  emails_found: number;
  created_at: string;
}

export const jobsApi = {
  list: () => request<JobSummary[]>("/api/v1/jobs"),
  get: (id: string) => request<Job>(`/api/v1/jobs/${id}`),
  create: (data: { profile_username: string; mode?: JobMode; target_post_url?: string }) =>
    request<Job>("/api/v1/jobs", { method: "POST", body: JSON.stringify(data) }),
  pause: (id: string) =>
    request<Job>(`/api/v1/jobs/${id}/pause`, { method: "POST" }),
  resume: (id: string) =>
    request<Job>(`/api/v1/jobs/${id}/resume`, { method: "POST" }),
  delete: (id: string) =>
    request<void>(`/api/v1/jobs/${id}`, { method: "DELETE" }),
  exportUrl: (id: string, fmt: "csv" | "json" = "csv") => {
    const key = getApiKey();
    return `${API_URL}/api/v1/jobs/${id}/export?fmt=${fmt}${key ? `&api_key=${key}` : ""}`;
  },
};

// ─── Prospects ────────────────────────────────────────────────

export interface Prospect {
  id: string;
  username: string;
  full_name: string | null;
  email: string | null;
  phone: string | null;
  website: string | null;
  biography: string | null;
  followers: number;
  following: number;
  is_business: boolean;
  is_verified: boolean;
  created_at: string;
}

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

export type AccountStatus = "active" | "cooldown" | "banned";

export interface Account {
  id: string;
  username: string;
  proxy_url: string | null;
  status: AccountStatus;
  requests_today: number;
  last_used_at: string | null;
  cooldown_until: string | null;
  created_at: string;
}

export const accountsApi = {
  list: () => request<Account[]>("/api/v1/accounts"),
  add: (data: { username: string; session_json: string; proxy_url?: string }) =>
    request<Account>("/api/v1/accounts", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  remove: (id: string) =>
    request<void>(`/api/v1/accounts/${id}`, { method: "DELETE" }),
};

export { ApiError };
