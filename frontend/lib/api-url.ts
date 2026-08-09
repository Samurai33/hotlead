// Shared by lib/server-api.ts and the app/api/proxy route — both make the
// actual server-to-server call to the FastAPI backend.
export function resolveApiUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  // The origin is served over http (Coolify/Traefik) and Cloudflare terminates
  // TLS at the edge, so the baked value can be http://<public-host>. Upgrade
  // any non-local http URL to https to match how the backend is actually
  // reachable.
  if (raw.startsWith("http://") && !/(localhost|127\.0\.0\.1)/.test(raw)) {
    return raw.replace(/^http:\/\//, "https://");
  }
  return raw;
}
