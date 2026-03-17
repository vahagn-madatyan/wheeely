---
id: S03
parent: M004
milestone: M004
provides:
  - Next.js 16 App Router project in apps/web/ with TypeScript + Tailwind CSS
  - Supabase browser client (createBrowserClient) and server client (createServerClient with cookie handlers)
  - Auth middleware protecting /dashboard, /screener/*, /settings with session-verified redirects
  - Auth callback route at /auth/callback for email confirmation code exchange
  - Login page with email+password form using signInWithPassword()
  - Signup page with email+password form using signUp() and "check your email" confirmation
  - Authenticated app shell with fixed sidebar (Dashboard, Put Screener, Call Screener, Settings)
  - Logout button that signs out and redirects to /login
  - apiFetch() API client utility with Authorization Bearer token injection for FastAPI calls
  - API proxy rewrite (next.config.ts) routing /api/* to FastAPI on port 8000
  - 4 placeholder pages for downstream slices (S04-S06)
requires:
  - slice: S02
    provides: Supabase project auth config (URL + anon key), JWT verification middleware for FastAPI
affects:
  - S04 (Settings route, authenticated API client)
  - S05 (Put Screener + Call Screener routes, authenticated API client)
  - S06 (Dashboard route)
  - S07 (assembled frontend for deployment)
key_files:
  - apps/web/package.json
  - apps/web/next.config.ts
  - apps/web/src/lib/supabase/client.ts
  - apps/web/src/lib/supabase/server.ts
  - apps/web/src/lib/api-client.ts
  - apps/web/src/middleware.ts
  - apps/web/src/app/auth/callback/route.ts
  - apps/web/src/app/(auth)/login/page.tsx
  - apps/web/src/app/(auth)/signup/page.tsx
  - apps/web/src/app/(app)/layout.tsx
  - apps/web/src/components/nav-links.tsx
  - apps/web/src/components/logout-button.tsx
  - apps/web/src/app/(app)/dashboard/page.tsx
  - apps/web/src/app/(app)/screener/puts/page.tsx
  - apps/web/src/app/(app)/screener/calls/page.tsx
  - apps/web/src/app/(app)/settings/page.tsx
key_decisions:
  - Next.js 16.1.7 (latest) used — fully compatible with App Router and @supabase/ssr; plans said 15 but API is identical
  - Middleware uses getUser() not getSession() for verified auth — getSession() only reads unverified cookie data
  - App shell layout is a server component; NavLinks and LogoutButton are client components — minimal client JS bundle
  - apiFetch() uses getSession() client-side (needs access_token, not server round-trip)
  - Middleware creates its own Supabase client with request/response cookie handlers (not the server.ts wrapper which uses cookies() API)
patterns_established:
  - (auth) route group for unauthenticated pages — centered card layout, no sidebar
  - (app) route group for authenticated pages — sidebar shell layout with server component + client component children
  - Supabase client.ts uses createBrowserClient for 'use client' components
  - Supabase server.ts uses async createClient() with cookies() from next/headers
  - API proxy via next.config.ts rewrites — frontend /api/* → FastAPI :8000
  - apiFetch() is the single entry point for all authenticated API calls to FastAPI
  - NavLinks uses pathname matching for active state highlighting (exact + nested routes)
  - AuthSessionError named class for explicit catch handling in downstream components
observability_surfaces:
  - npm run build exit code — zero errors confirms all TypeScript compiles
  - Middleware 307 redirects visible in browser Network tab
  - Auth callback failures redirect to /login?error=auth
  - Login/signup errors render as role="alert" elements
  - Browser DevTools Network tab shows Authorization: Bearer <token> on apiFetch() calls
  - Missing env vars crash Supabase client init with console error
drill_down_paths:
  - .gsd/milestones/M004/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M004/slices/S03/tasks/T02-SUMMARY.md
  - .gsd/milestones/M004/slices/S03/tasks/T03-SUMMARY.md
duration: ~30m across 3 tasks
verification_result: passed
completed_at: 2026-03-16
---

# S03: Next.js shell + auth flow

**Next.js 16 app with Supabase auth, protected route middleware, login/signup pages, sidebar navigation shell, and authenticated API client — ready for downstream UI slices to build on.**

## What Happened

Scaffolded a Next.js 16 App Router project in `apps/web/` with TypeScript and Tailwind CSS. Installed `@supabase/ssr` and `@supabase/supabase-js` and created two client wrappers: a browser client for `'use client'` components and an async server client with `cookies()` handlers for server components and route handlers.

Built the auth middleware at `src/middleware.ts` — creates a Supabase server client with dual cookie handlers (writes to both request and response cookies to avoid stale data in downstream components), calls `getUser()` for verified auth checks, and redirects unauthenticated users from protected routes (`/dashboard`, `/screener/*`, `/settings`) to `/login` while redirecting authenticated users from auth pages to `/dashboard`.

Created the auth callback route (`/auth/callback`) for email confirmation code exchange, and two auth pages using the `(auth)` route group with a centered card layout: login with `signInWithPassword()` and signup with `signUp()` plus a "check your email" success state. Both pages include error alerts, loading states, and cross-links.

Built the authenticated app shell using the `(app)` route group — a server component layout that reads the user via `getUser()` and renders a fixed dark sidebar (w-64, bg-gray-900) with Wheeely branding and `NavLinks` (client component with `usePathname()` active state highlighting), plus a main content area with top bar showing user email and `LogoutButton` (client component calling `signOut()` + redirect). Created 4 placeholder pages for Dashboard, Put Screener, Call Screener, and Settings.

Created `apiFetch()` in `lib/api-client.ts` — reads the Supabase browser session, extracts the access token, and injects `Authorization: Bearer <token>` on all fetch calls. Throws `AuthSessionError` if no session exists. Configured `next.config.ts` with proxy rewrites routing `/api/*` to FastAPI on port 8000.

## Verification

- ✅ `cd apps/web && npm run build` — exits 0, zero type errors, all 8 routes compiled (/, /_not-found, /auth/callback, /dashboard, /login, /screener/calls, /screener/puts, /settings, /signup)
- ✅ Root `/` redirects to `/dashboard` (which middleware redirects to `/login` for unauthenticated users)
- ✅ Navigate to `/dashboard` while unauthenticated — middleware returns 307 redirect to `/login`
- ✅ Navigate to `/screener/puts`, `/screener/calls`, `/settings` while unauthenticated — all redirect to `/login`
- ✅ Login page renders with "Sign in to Wheeely" heading, email/password inputs, submit button, link to signup
- ✅ Signup page renders with "Create your Wheeely account" heading, email/password inputs, submit button, link to login
- ✅ App shell layout has sidebar with all 4 nav links (Dashboard, Put Screener, Call Screener, Settings)
- ✅ All 4 placeholder pages render with headings
- ✅ `apiFetch()` sets `Authorization: Bearer ${session.access_token}` header
- ✅ `next.config.ts` rewrites `/api/:path*` to `http://localhost:8000/api/:path*`
- ✅ 425 CLI tests still pass unchanged
- ⏳ Runtime auth flow (real login/signup/logout) — requires running Supabase instance with valid env vars (UAT-level verification)

## Requirements Advanced

- WEB-01 — Frontend auth flow implemented: login page, signup page, middleware route protection, session management via Supabase cookies. Full validation requires live Supabase instance (UAT).

## Requirements Validated

- none — WEB-01 needs runtime UAT with real Supabase to move to validated

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- **Next.js 16 instead of 15:** `create-next-app@latest` installs Next.js 16.1.7 as of March 2026. The App Router API, `cookies()` async behavior, and `@supabase/ssr` integration are identical. No impact on any downstream slices.
- **Middleware deprecation warning:** Next.js 16 shows "The 'middleware' file convention is deprecated. Please use 'proxy' instead." Middleware still compiles and runs correctly. Migration optional for now.

## Known Limitations

- Runtime auth flow (actual login, signup, email confirmation, logout) cannot be verified without a running Supabase instance with valid `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`. This is expected — real credentials are an S02 prerequisite for runtime testing.
- Next.js 16 middleware deprecation warning — functional but may need migration to `proxy` convention in a future cleanup.
- No form validation beyond HTML `required` attributes — no password strength requirements, no email format validation beyond browser defaults.

## Follow-ups

- Consider migrating middleware.ts to Next.js 16 `proxy` convention when the API stabilizes — currently shows deprecation warning but works correctly.
- S04 should import `apiFetch` from `@/lib/api-client` for all FastAPI calls — no need to construct auth headers manually.

## Files Created/Modified

- `apps/web/` — entire Next.js 16 project scaffolded
- `apps/web/package.json` — next, react, @supabase/ssr, @supabase/supabase-js
- `apps/web/next.config.ts` — API proxy rewrite to FastAPI on port 8000
- `apps/web/src/lib/supabase/client.ts` — browser Supabase client wrapper
- `apps/web/src/lib/supabase/server.ts` — server Supabase client wrapper with async cookies
- `apps/web/src/lib/api-client.ts` — apiFetch() with auth header injection and AuthSessionError
- `apps/web/src/middleware.ts` — session refresh + route protection with getUser()
- `apps/web/src/app/auth/callback/route.ts` — email confirmation code exchange
- `apps/web/src/app/(auth)/layout.tsx` — centered card layout for auth pages
- `apps/web/src/app/(auth)/login/page.tsx` — login form with signInWithPassword
- `apps/web/src/app/(auth)/signup/page.tsx` — signup form with signUp + confirmation message
- `apps/web/src/app/(app)/layout.tsx` — server component app shell with sidebar + top bar
- `apps/web/src/components/nav-links.tsx` — client component with usePathname() active state
- `apps/web/src/components/logout-button.tsx` — client component calling signOut + redirect
- `apps/web/src/app/(app)/dashboard/page.tsx` — placeholder Dashboard page
- `apps/web/src/app/(app)/screener/puts/page.tsx` — placeholder Put Screener page
- `apps/web/src/app/(app)/screener/calls/page.tsx` — placeholder Call Screener page
- `apps/web/src/app/(app)/settings/page.tsx` — placeholder Settings page
- `apps/web/src/app/page.tsx` — root redirect to /dashboard
- `apps/web/.env.local.example` — documents required env vars

## Forward Intelligence

### What the next slice should know
- Import `apiFetch` from `@/lib/api-client` for all FastAPI calls — it handles session reading, Bearer token injection, and AuthSessionError throwing. No manual header construction needed.
- The `(app)` route group layout already reads the user via `getUser()` and displays their email. S04/S05/S06 pages rendered inside this layout get the sidebar and top bar for free.
- Settings page is at `apps/web/src/app/(app)/settings/page.tsx` — S04 replaces its placeholder content with the key management form.
- Screener pages are at `apps/web/src/app/(app)/screener/puts/page.tsx` and `screener/calls/page.tsx` — S05 replaces their placeholder content.
- Dashboard page is at `apps/web/src/app/(app)/dashboard/page.tsx` — S06 replaces its placeholder content.

### What's fragile
- `middleware.ts` uses the deprecated middleware convention — Next.js 16 may drop support in a future minor release. Migration to `proxy` convention is documented at nextjs.org/docs/messages/middleware-to-proxy.
- `.env.local` must have both `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` — missing values crash the Supabase client at runtime with no graceful fallback.

### Authoritative diagnostics
- `npm run build` exit code is the single most reliable signal — zero errors means all TypeScript compiles, all routes resolve, all imports are valid.
- Browser DevTools Network tab shows 307 redirects from middleware and `Authorization: Bearer` headers on apiFetch() calls.
- `role="alert"` divs in login/signup pages show Supabase error messages.

### What assumptions changed
- Plan assumed Next.js 15 — actual is Next.js 16.1.7. No functional impact; App Router API is identical. Turbopack is now the default build tool.
- Plan didn't anticipate middleware deprecation warning — middleware still works but shows a console warning during build/dev.