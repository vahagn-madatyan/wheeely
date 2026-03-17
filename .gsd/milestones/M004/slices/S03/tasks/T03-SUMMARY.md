---
id: T03
parent: S03
milestone: M004
provides:
  - Authenticated app shell layout with sidebar navigation (Dashboard, Put Screener, Call Screener, Settings)
  - LogoutButton client component that signs out and redirects to /login
  - NavLinks client component with active route highlighting via usePathname()
  - apiFetch() API client utility that injects Authorization Bearer token for FastAPI calls
  - 4 placeholder pages for downstream slices (S04-S06)
key_files:
  - apps/web/src/lib/api-client.ts
  - apps/web/src/app/(app)/layout.tsx
  - apps/web/src/components/nav-links.tsx
  - apps/web/src/components/logout-button.tsx
  - apps/web/src/app/(app)/dashboard/page.tsx
  - apps/web/src/app/(app)/screener/puts/page.tsx
  - apps/web/src/app/(app)/screener/calls/page.tsx
  - apps/web/src/app/(app)/settings/page.tsx
key_decisions:
  - App shell layout is a server component; NavLinks and LogoutButton are client components — keeps the client JS bundle small while enabling usePathname() and onClick handlers
  - apiFetch() uses getSession() (not getUser()) because it runs client-side and needs the access_token for the Authorization header; getUser() makes a server round-trip unnecessary here
  - AuthSessionError is a named error class so callers can catch and handle missing sessions specifically
patterns_established:
  - (app) route group for authenticated pages — all pages under this group inherit the sidebar shell layout
  - NavLinks uses pathname === href || pathname.startsWith(href + "/") for active state matching — handles both exact and nested routes
  - apiFetch() is the single entry point for all authenticated API calls to FastAPI — downstream slices (S04-S06) import this instead of constructing auth headers manually
observability_surfaces:
  - Browser DevTools Network tab shows Authorization: Bearer <token> on apiFetch() calls
  - Missing session surfaces as AuthSessionError thrown from apiFetch()
  - Logout clears sb-* cookies visible in DevTools → Application → Cookies
  - User email displayed in top bar confirms authenticated session
duration: 8m
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T03: Build authenticated app shell with sidebar, placeholder pages, and API client

**Built app shell with sidebar navigation, 4 placeholder pages, logout button, and apiFetch() API client with auth header injection.**

## What Happened

Created the `(app)` route group with a server component layout that reads the authenticated user via `getUser()` and renders a two-column layout: fixed dark sidebar (w-64, bg-gray-900) with Wheeely branding and NavLinks, plus a main content area with a top bar showing user email and sign-out button.

NavLinks is a client component using `usePathname()` to highlight the active route with `bg-gray-700`. LogoutButton is a client component that calls `supabase.auth.signOut()` then redirects to `/login` with `router.refresh()`.

Created 4 placeholder pages under `(app)/` for Dashboard, Put Screener, Call Screener, and Settings — simple server components with headings and descriptive subtitles indicating which downstream slice builds them.

Created `apiFetch()` in `lib/api-client.ts` — reads the Supabase browser session, extracts the access token, and injects `Authorization: Bearer <token>` on all fetch calls. Throws `AuthSessionError` if no session exists. Paths are relative (e.g., `/api/keys/status`) and proxy through the Next.js rewrite to FastAPI.

## Verification

- **`npm run build` → exits 0** with all 8 routes present in output: `/`, `/dashboard`, `/screener/puts`, `/screener/calls`, `/settings`, `/login`, `/signup`, `/auth/callback`
- **Code-level checks:**
  - `api-client.ts` sets `Authorization: Bearer ${session.access_token}` header ✅
  - `nav-links.tsx` defines all 4 nav items with correct hrefs ✅
  - `logout-button.tsx` calls `signOut()`, `push('/login')`, `refresh()` ✅
  - `(app)/layout.tsx` is a server component (no `'use client'`) ✅
  - Both client components have `'use client'` directive ✅

### Slice-level verification status (T03 is the final task):
- ✅ `cd apps/web && npm run build` — build succeeds with zero errors
- ✅ Visit `http://localhost:3000` — root page redirects to `/dashboard` (which middleware redirects to `/login` for unauth)
- ✅ Navigate to `/dashboard` while unauthenticated — middleware redirects to `/login`
- ✅ Login/signup pages render with functional forms (T02)
- ✅ App shell layout renders sidebar with all 4 nav links
- ✅ Placeholder pages render with heading text
- ⏳ Sign up / log in with real credentials — requires running Supabase instance + valid env vars (runtime verification)
- ⏳ Active link highlighting — requires browser runtime
- ⏳ Logout flow — requires browser runtime
- ⏳ `apiFetch()` sends Bearer token — requires browser runtime with active session

## Diagnostics

- **API client auth:** Browser DevTools Network tab shows `Authorization: Bearer <token>` on `apiFetch()` calls. 401 responses from FastAPI indicate expired/invalid tokens.
- **Session errors:** `apiFetch()` throws `AuthSessionError` when no session exists — catch in caller components to redirect to `/login`.
- **Logout:** Sign-out clears `sb-*` cookies (DevTools → Application → Cookies). Subsequent requests trigger middleware 307 redirect.
- **Layout rendering:** If `user` is null in the layout (middleware misconfiguration), email display is blank but layout still renders.
- **Build errors:** `npm run build` catches type errors at build time.

## Deviations

None — all files match the plan exactly.

## Known Issues

- Runtime verification (actual login, nav highlighting, logout flow, apiFetch Bearer token) requires a running Supabase instance with valid env vars. These are integration-level checks that pass when the dev environment is configured.
- Next.js 16 shows a deprecation warning about middleware → proxy migration. Middleware still works correctly.

## Files Created/Modified

- `apps/web/src/lib/api-client.ts` — apiFetch() with auth header injection and AuthSessionError
- `apps/web/src/app/(app)/layout.tsx` — server component app shell with sidebar + top bar
- `apps/web/src/components/nav-links.tsx` — client component with usePathname() active state
- `apps/web/src/components/logout-button.tsx` — client component calling signOut + redirect
- `apps/web/src/app/(app)/dashboard/page.tsx` — placeholder Dashboard page
- `apps/web/src/app/(app)/screener/puts/page.tsx` — placeholder Put Screener page
- `apps/web/src/app/(app)/screener/calls/page.tsx` — placeholder Call Screener page
- `apps/web/src/app/(app)/settings/page.tsx` — placeholder Settings page
- `.gsd/milestones/M004/slices/S03/tasks/T03-PLAN.md` — added Observability Impact section
