// Server-only: reads/writes the httpOnly cookie that replaced localStorage
// as the API key's storage (audit AUDIT-2.md M1). Only importable from
// Server Components, Server Actions, and Route Handlers — `next/headers`
// throws if this ends up in a Client Component bundle.
import { cookies } from "next/headers";
import { SESSION_COOKIE } from "@/lib/constants";

export async function getSessionApiKey(): Promise<string | null> {
  const store = await cookies();
  return store.get(SESSION_COOKIE)?.value ?? null;
}

/** Server Actions / Route Handlers only — Server Components can't write cookies. */
export async function setSessionCookie(apiKey: string): Promise<void> {
  const store = await cookies();
  store.set(SESSION_COOKIE, apiKey, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 30,
  });
}

export async function clearSessionCookie(): Promise<void> {
  const store = await cookies();
  store.delete(SESSION_COOKIE);
}
