// Zero-dependency module (no `next/headers`, no server-only APIs) so it's
// safe to import from middleware.ts, Route Handlers, Server Actions, Server
// Components, and lib/session.ts alike without pulling in anything that
// breaks the Edge runtime middleware uses.
export const SESSION_COOKIE = "hotlead_session";
