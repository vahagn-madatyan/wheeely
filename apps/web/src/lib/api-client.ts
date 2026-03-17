import { createClient } from "@/lib/supabase/client";

/**
 * Authenticated fetch wrapper for the FastAPI backend.
 *
 * Reads the Supabase session from the browser client, injects the
 * `Authorization: Bearer <access_token>` header, and delegates to
 * `fetch()`. The path should be relative (e.g. `/api/keys/status`) —
 * Next.js rewrites proxy it to the FastAPI backend.
 *
 * @throws {AuthSessionError} if no active session exists
 */
export class AuthSessionError extends Error {
  constructor() {
    super("No active session — user must log in");
    this.name = "AuthSessionError";
  }
}

export async function apiFetch(
  path: string,
  options?: RequestInit
): Promise<Response> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) {
    throw new AuthSessionError();
  }

  const headers = new Headers(options?.headers);
  headers.set("Authorization", `Bearer ${session.access_token}`);

  return fetch(path, {
    ...options,
    headers,
  });
}
