# S03: Next.js shell + auth flow — Research

**Date:** 2026-03-16
**Depth:** Targeted

## Summary

S03 is a greenfield Next.js 15 App Router setup in `apps/web/` with Supabase cookie-based auth. No frontend code exists yet — `apps/web/` does not exist. The backend API (`apps/api/`) is fully wired with auth middleware, key CRUD, screening endpoints, and positions/account endpoints. The frontend needs to: create Supabase browser/server clients via `@supabase/ssr`, protect routes via Next.js middleware, provide login/signup pages, render an authenticated app shell with sidebar nav (Dashboard, Put Screener, Call Screener, Settings), and expose an API client that injects the Supabase access token into FastAPI requests.

This is well-understood work — `@supabase/ssr` + Next.js App Router has a canonical pattern (middleware refreshes session, server components read cookies, browser client handles login/signup). The only integration surface is the API client forwarding the Supabase JWT to the FastAPI backend. The FastAPI `get_current_user` dependency already verifies HS256 JWTs with `SUPABASE_JWT_SECRET` (D060), so the frontend just needs to pass the access token as a Bearer header.

## Recommendation

Use `create-next-app` with TypeScript + Tailwind + App Router. Use `@supabase/ssr` (not the deprecated `@supabase/auth-helpers-nextjs`) for server/browser/middleware client creation. Implement a standard Supabase auth flow: middleware at `middleware.ts` refreshes the session cookie on every request and redirects unauthenticated users away from protected routes. Login/signup are simple email+password forms using `supabase.auth.signInWithPassword()` and `supabase.auth.signUp()`. Auth callback route at `app/auth/callback/route.ts` exchanges the email confirmation code for a session. Shell layout uses a sidebar with nav links — placeholder pages for Dashboard, Put Screener, Call Screener, Settings. API client utility wraps `fetch` with the Supabase access token as `Authorization: Bearer <token>`.

## Implementation Landscape

### Key Files

**Existing (backend — consume, don't modify):**
- `apps/api/services/auth.py` — `get_current_user()` verifies HS256 JWTs, returns `user_id` string. Expects `Authorization: Bearer <supabase_access_token>`.
- `apps/api/main.py` — CORS already allows all origins for dev. FastAPI on port 8000.
- `apps/api/routers/keys.py` — `GET /api/keys/status` returns `{providers: [{provider, connected, is_paper, key_names}]}` — frontend needs this to show key connection state.
- `apps/api/schemas.py` — Full Pydantic models for all API responses. Source of truth for TypeScript types.

**To create (`apps/web/`):**
- `apps/web/package.json` — Next.js 15, `@supabase/ssr`, `@supabase/supabase-js`, Tailwind CSS
- `apps/web/next.config.ts` — Minimal config. API rewrites to FastAPI backend for dev (`/api/:path*` → `http://localhost:8000/api/:path*`)
- `apps/web/middleware.ts` — Supabase session refresh + route protection. Unauthenticated users hitting `/dashboard`, `/screener/*`, `/settings` get redirected to `/login`. Authenticated users hitting `/login` or `/signup` get redirected to `/dashboard`.
- `apps/web/lib/supabase/client.ts` — `createBrowserClient()` wrapper (singleton, uses `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_ANON_KEY`)
- `apps/web/lib/supabase/server.ts` — `createServerClient()` wrapper for server components and middleware (cookie handlers via `next/headers`)
- `apps/web/lib/api-client.ts` — `apiFetch(path, options)` utility that reads the Supabase session, injects `Authorization: Bearer <access_token>`, and calls the FastAPI backend
- `apps/web/app/layout.tsx` — Root layout with HTML shell, Tailwind globals, font
- `apps/web/app/(auth)/login/page.tsx` — Login form (email + password), calls `supabase.auth.signInWithPassword()`, redirects to `/dashboard` on success
- `apps/web/app/(auth)/signup/page.tsx` — Signup form (email + password + confirm), calls `supabase.auth.signUp()`, shows "check your email" message
- `apps/web/app/(auth)/layout.tsx` — Centered card layout for auth pages (no sidebar)
- `apps/web/app/auth/callback/route.ts` — Exchanges Supabase auth code for session cookie, redirects to `/dashboard`
- `apps/web/app/(app)/layout.tsx` — Authenticated shell with sidebar nav (Dashboard, Put Screener, Call Screener, Settings) and top bar with user email + logout button
- `apps/web/app/(app)/dashboard/page.tsx` — Placeholder "Dashboard" page (content built in S06)
- `apps/web/app/(app)/screener/puts/page.tsx` — Placeholder "Put Screener" page (content built in S05)
- `apps/web/app/(app)/screener/calls/page.tsx` — Placeholder "Call Screener" page (content built in S05)
- `apps/web/app/(app)/settings/page.tsx` — Placeholder "Settings" page (content built in S04)

### Build Order

1. **Project scaffolding** — `create-next-app` in `apps/web/`, install deps, verify `npm run dev` works. This is the foundation everything else depends on.
2. **Supabase client utilities** — `client.ts` (browser) and `server.ts` (server/middleware). These are consumed by middleware and all auth pages.
3. **Middleware + auth callback** — `middleware.ts` for session refresh + route protection, `auth/callback/route.ts` for email confirmation. This proves the auth plumbing works end-to-end with a real Supabase project.
4. **Auth pages** — Login and signup forms in `(auth)` route group. Client components using `createBrowserClient`.
5. **App shell + placeholder pages** — `(app)` route group with sidebar layout, placeholder pages for Dashboard/Put Screener/Call Screener/Settings.
6. **API client** — `apiFetch()` utility that injects the Supabase access token. Proves the frontend can call the FastAPI backend with auth.

### Verification Approach

1. `cd apps/web && npm run build` — build succeeds with zero errors
2. Run `npm run dev` (port 3000) alongside `uvicorn apps.api.main:app` (port 8000)
3. Visit `http://localhost:3000` — redirected to `/login`
4. Navigate to `/signup` — signup form renders
5. Navigate to `/dashboard` while unauthenticated — redirected to `/login`
6. Log in with valid Supabase credentials — redirected to `/dashboard`, sidebar visible with all nav links
7. Click sidebar nav links — Dashboard, Put Screener, Call Screener, Settings pages render
8. Click logout — redirected to `/login`
9. Verify `apiFetch()` sends Bearer token by inspecting network request headers in browser devtools against the FastAPI backend

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Supabase cookie auth in App Router | `@supabase/ssr` | Handles cookie chunking, token refresh, server/client boundary automatically |
| CSS framework | Tailwind CSS (via `create-next-app`) | Already decided in M004 context; fast iteration for shell layout |
| Project scaffolding | `create-next-app --typescript --tailwind --app --src-dir` | Generates correct App Router structure with TS + Tailwind pre-configured |

## Constraints

- `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` are required env vars — without them the Supabase client crashes at runtime
- The FastAPI backend runs on port 8000; Next.js dev on port 3000. Dev-time API calls need a proxy rewrite in `next.config.ts` or an explicit `NEXT_PUBLIC_API_URL` env var
- `get_current_user` in FastAPI expects the raw Supabase access token as `Bearer <token>` — the frontend must read `session.access_token` from `supabase.auth.getSession()` (for client-side) or extract it from cookies (for SSR API calls)
- `@supabase/ssr` requires `getAll` / `setAll` cookie handlers — older `get/set/remove` pattern is deprecated
- Next.js middleware must not block on heavy computation — it only refreshes the session and checks auth state, no DB calls
- S03 owns only the shell + auth flow — Dashboard, Screener, Settings page *content* is built by S04-S06. S03 creates the routes with placeholder content.

## Common Pitfalls

- **Using `getSession()` for auth checks in server components** — `getSession()` reads unverified cookie data; always use `getUser()` which makes a verified API call to Supabase. Middleware already calls `getUser()` so server components within the protected route group can trust the session exists, but any server component that needs the user object should call `getUser()`.
- **Forgetting the auth callback route** — Supabase email confirmation redirects to `/auth/callback?code=...`. Without this route, signup email links break silently. The callback must exchange the code for a session via `supabase.auth.exchangeCodeForSession(code)`.
- **Cookie stale after token refresh** — The middleware's `setAll` handler must write cookies to *both* the request and the response object. If only the response is updated, downstream server components read stale cookies. The `@supabase/ssr` docs show the pattern explicitly.
- **CORS with credentials** — FastAPI's CORS middleware already has `allow_credentials=True` and `allow_origins=["*"]`. For dev this works. Note: in production (S07), `allow_origins` must be set to the actual Render domain — wildcard + credentials is a browser error.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Next.js + Supabase Auth | sickn33/antigravity-awesome-skills@nextjs-supabase-auth | installed |
| Next.js App Router | wshobson/agents@nextjs-app-router-patterns | installed |

## Sources

- `@supabase/ssr` cookie-based auth pattern for Next.js App Router (source: [Context7 supabase/ssr docs](https://context7.com/supabase/ssr/llms.txt))
- Next.js middleware route protection pattern (source: [Next.js auth guide](https://github.com/vercel/next.js/blob/canary/docs/01-app/02-guides/authentication.mdx))
