/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  // NOTE: experimental.typedRoutes was disabled — it failed the build because
  // the "/jobs/[id]/prospects" link target has no page yet. Re-enable once that
  // route exists.
  // Security headers
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
