// 'unsafe-eval' is dev-only (Next's React Refresh/HMR needs it); production
// builds don't. No third-party scripts/styles/fonts are loaded by the app
// itself, so everything else stays 'self' — except Cloudflare's own Web
// Analytics beacon, which the edge injects into every HTML response for
// real browser traffic regardless of what this app serves (verify with
// `curl -A "Mozilla/5.0 ..."` vs a bare curl: only the browser-UA response
// gets a `<script type="module" src="https://static.cloudflareinsights.com/...">`
// tag appended). A strict `script-src 'self'` blocks that injected tag,
// which is expected — but it's also exactly what breaks Server Component
// hydration on every route once there's real RSC payload data to hydrate
// (not an issue back when every route was 100% client with near-empty
// flight data). connect-src needs the same origin for the beacon's own
// reporting call. No backend origin needed in connect-src: the browser
// talks only to this origin now (the /api/proxy Route Handler and Server
// Actions do the actual backend calls server-side, attaching the API key
// from the httpOnly session cookie — audit AUDIT-2.md M1's full
// localStorage-to-cookie migration, on top of the CSP header this same
// finding already got).
const csp = [
  "default-src 'self'",
  `script-src 'self' https://static.cloudflareinsights.com${process.env.NODE_ENV === "development" ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data:",
  "font-src 'self' data:",
  "connect-src 'self' https://cloudflareinsights.com",
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "object-src 'none'",
].join("; ");

/** @type {import("next").NextConfig} */
const nextConfig = {
  output: "standalone",
  typedRoutes: true,
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
          { key: "Content-Security-Policy", value: csp },
        ],
      },
    ];
  },
};

export default nextConfig;
