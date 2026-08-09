// 'unsafe-eval' is dev-only (Next's React Refresh/HMR needs it); production
// builds don't. No third-party scripts/styles/fonts are loaded anywhere in
// the app, so everything else stays 'self'. connect-src no longer needs the
// backend origin: the browser talks only to this origin now (the /api/proxy
// Route Handler and Server Actions do the actual backend calls server-side,
// attaching the API key from the httpOnly session cookie — audit
// AUDIT-2.md M1's full localStorage-to-cookie migration, on top of the CSP
// header this same finding already got).
const csp = [
  "default-src 'self'",
  `script-src 'self'${process.env.NODE_ENV === "development" ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data:",
  "font-src 'self' data:",
  "connect-src 'self'",
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
