// Same http->https upgrade resolveApiUrl() does in lib/api.ts: Coolify/Traefik
// serves the API over http (Cloudflare terminates TLS at the edge), so the
// baked NEXT_PUBLIC_API_URL can be an http:// origin even though the browser
// must reach it over https. connect-src needs the origin it'll actually hit.
const rawApiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const apiOrigin =
  rawApiUrl.startsWith("http://") && !/(localhost|127\.0\.0\.1)/.test(rawApiUrl)
    ? rawApiUrl.replace(/^http:\/\//, "https://")
    : rawApiUrl;

// 'unsafe-eval' is dev-only (Next's React Refresh/HMR needs it); production
// builds don't. No third-party scripts/styles/fonts are loaded anywhere in
// the app, so everything else stays 'self' (audit AUDIT-2.md M1 — the API
// key still lives in localStorage, but this closes the CSP gap noted
// alongside it as cheap defense-in-depth).
const csp = [
  "default-src 'self'",
  `script-src 'self'${process.env.NODE_ENV === "development" ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data:",
  "font-src 'self' data:",
  `connect-src 'self' ${apiOrigin}`,
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
