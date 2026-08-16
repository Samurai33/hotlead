// Real server-side route protection (audit AUDIT-2.md L8) — replaces
// AuthGuard.tsx's useEffect + localStorage check, which only hid the UI
// after a client-side render and was trivially bypassable in devtools. This
// runs before any page renders and only checks cookie *presence*; the
// backend's require_api_key (X-API-Key + constant-time compare) remains the
// actual authorization check on every request made through /api/proxy,
// Server Actions, or Server Components.
//
// Deliberately does NOT redirect away from /login when the cookie is
// present — the cookie's value isn't validated here (that would mean a
// backend round-trip on every navigation), so a stale/rotated key must
// still be able to reach the login form to fix itself instead of bouncing
// in a redirect loop.
import { NextRequest, NextResponse } from "next/server";
import { SESSION_COOKIE } from "@/lib/constants";

// CSP also lives here, not in next.config.mjs, because a per-request nonce
// can't be a static header. A first attempt at this (see git history)
// generated the nonce here but only set it on the outgoing *response*
// headers, then read it back via headers() in the root layout — and on
// this exact toolchain (Next 16.3, Turbopack `next build`) none of Next's
// own framework/RSC-hydration <script> tags ever picked up a matching
// `nonce=` attribute, so 'strict-dynamic' blocked every one of them
// (verified via curl on the built output, not just browser console
// errors). That looked like a Next/Turbopack bug but wasn't: Next reads the
// nonce off the incoming *request's* Content-Security-Policy header
// (next/dist/server/app-render/get-script-nonce-from-header.js), a header
// that only exists if this middleware clones the request headers and
// forwards them via `NextResponse.next({ request: { headers } })` — setting
// it only on the response, as the first attempt did, leaves that header
// absent from what the framework actually reads. With the request-header
// forward in place below, every framework script gets nonced correctly and
// no 'unsafe-inline'/'strict-dynamic' tradeoff is needed — plain nonce +
// the existing host allowlist (for Cloudflare's injected beacon script,
// which never carries our nonce) is enough.
//
// Cost: a route that reads the nonce can no longer be statically rendered
// (the HTML differs every request) — this flips /login and /jobs/new from
// static to dynamic. Both are low-traffic, auth-adjacent pages, so that's
// an accepted tradeoff for dropping 'unsafe-inline' entirely.
function buildCsp(nonce: string, isDev: boolean) {
  return [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' https://static.cloudflareinsights.com${isDev ? " 'unsafe-eval'" : ""}`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data:",
    "font-src 'self' data:",
    "connect-src 'self' https://cloudflareinsights.com",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "object-src 'none'",
  ].join("; ");
}

export function proxy(request: NextRequest) {
  const nonce = btoa(crypto.randomUUID());
  const csp = buildCsp(nonce, process.env.NODE_ENV === "development");

  if (
    request.nextUrl.pathname !== "/login" &&
    !request.cookies.has(SESSION_COOKIE)
  ) {
    const response = NextResponse.redirect(new URL("/login", request.url));
    response.headers.set("Content-Security-Policy", csp);
    return response;
  }

  // Forward on the *request* headers (not just the response) — this is the
  // step the first attempt missed. See the comment above.
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("Content-Security-Policy", csp);

  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.headers.set("Content-Security-Policy", csp);
  return response;
}

export const config = {
  // Runs on /login too now (it needs the CSP nonce like every other page);
  // the pathname check above handles skipping the cookie redirect there.
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
