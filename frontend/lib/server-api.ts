// Server-only direct backend client, used from Server Components and
// Server Actions (which already have the httpOnly cookie via next/headers,
// so there's no need to round-trip through the /api/proxy Route Handler
// that exists for client-side polling instead).
import { getSessionApiKey } from "@/lib/session";
import { resolveApiUrl } from "@/lib/api-url";

const API_URL = resolveApiUrl();

export class ServerApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(detail);
    this.name = "ServerApiError";
  }
}

export async function backendFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const apiKey = await getSessionApiKey();
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(apiKey ? { "X-API-Key": apiKey } : {}),
      ...init.headers,
    },
    cache: "no-store",
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {}
    throw new ServerApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}
