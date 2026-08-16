// Content-Security-Policy lives entirely in proxy.ts now, not here — a
// per-request nonce can't be a static header. See proxy.ts for the full
// account of the nonce-forwarding fix and why 'unsafe-inline' isn't needed.
/** @type {import("next").NextConfig} */
const nextConfig = {
  output: "standalone",
  typedRoutes: true,
  experimental: {
    // Server Actions validate the request's Origin against Host as a CSRF
    // guard. Traefik reports scheme=http here (TLS terminates at the
    // Cloudflare edge, outside Coolify's reach — see CLAUDE.md), which makes
    // that same-origin inference quirky through the proxy chain. Pin the
    // known-good production origin explicitly instead of relying on it.
    serverActions: {
      allowedOrigins: ["hotlead.n3xus.dev"],
    },
  },
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
        ],
      },
    ];
  },
};

export default nextConfig;
