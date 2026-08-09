// Same-origin proxy for client-side polling (SWR in Client Components).
// The browser never sees the API key: it holds only the httpOnly session
// cookie, which never leaves this origin. This handler reads that cookie
// server-side and attaches it as the X-API-Key header the backend expects
// (audit AUDIT-2.md M1 — backend's require_api_key is unchanged, still a
// pure header check).
import { NextRequest, NextResponse } from "next/server";
import { getSessionApiKey, clearSessionCookie } from "@/lib/session";
import { resolveApiUrl } from "@/lib/api-url";

const API_URL = resolveApiUrl();

async function proxy(request: NextRequest, path: string[]): Promise<NextResponse> {
  const apiKey = await getSessionApiKey();
  if (!apiKey) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const target = `${API_URL}/${path.join("/")}${request.nextUrl.search}`;
  const init: RequestInit = {
    method: request.method,
    headers: {
      "X-API-Key": apiKey,
      ...(request.method === "POST" ? { "Content-Type": "application/json" } : {}),
    },
    ...(request.method === "POST" ? { body: await request.text() } : {}),
  };

  const res = await fetch(target, init);

  // Self-healing: a stale/rotated key means every proxied call 401s from here
  // on, so drop the cookie now instead of leaving the client stuck with a
  // cookie middleware treats as "logged in" but that never actually works.
  if (res.status === 401 || res.status === 403) {
    await clearSessionCookie();
  }

  const headers = new Headers();
  const contentType = res.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);
  const disposition = res.headers.get("content-disposition");
  if (disposition) headers.set("content-disposition", disposition);

  return new NextResponse(res.body, { status: res.status, headers });
}

type RouteParams = { params: Promise<{ path: string[] }> };

export async function GET(request: NextRequest, { params }: RouteParams) {
  const { path } = await params;
  return proxy(request, path);
}

export async function POST(request: NextRequest, { params }: RouteParams) {
  const { path } = await params;
  return proxy(request, path);
}

export async function DELETE(request: NextRequest, { params }: RouteParams) {
  const { path } = await params;
  return proxy(request, path);
}
