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

export function middleware(request: NextRequest) {
  if (!request.cookies.has(SESSION_COOKIE)) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|login).*)"],
};
