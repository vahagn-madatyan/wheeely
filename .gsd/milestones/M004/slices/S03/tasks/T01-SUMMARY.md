---
id: T01
parent: S03
milestone: M004
provides:
  - apps/web/ Next.js 16 project with TypeScript + Tailwind CSS
  - Supabase browser client wrapper (createBrowserClient)
  - Supabase server client wrapper (createServerClient with cookie handlers)
  - API proxy rewrite to FastAPI on port 8000
  - Root redirect to /dashboard
key_files:
  - apps/web/package.json
  - apps/web/next.config.ts
  - apps/web/src/lib/supabase/client.ts
  - apps/web/src/lib/supabase/server.ts
  - apps/web/src/app/page.tsx
  - apps/web/.env.local.example
key_decisions:
  - Used Next.js 16.1.7 (latest from create-next-app) — fully compatible with App Router patterns and @supabase/ssr
patterns_established:
  - Supabase client.ts uses createBrowserClient for 'use client' components
  - Supabase server.ts uses async createClient() with cookies() from next/headers and getAll/setAll handlers
  - API proxy via next.config.ts rewrites — frontend calls /api/* which proxies to FastAPI on :8000
observability_surfaces:
  - npm run build exit code — zero errors confirms all TypeScript and imports are correct
  - Browser console errors on missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY
  - Network tab 502/504 when FastAPI backend not running (proxy target unavailable)
duration: ~5m
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T01: Scaffold Next.js project and create Supabase client utilities

**Scaffolded Next.js 16 App Router project in apps/web/ with Supabase browser+server client wrappers, API proxy rewrite, and root redirect to /dashboard.**

## What Happened

1. Ran `npx create-next-app@latest apps/web` — got Next.js 16.1.7 with TypeScript, Tailwind CSS, App Router, src/ directory.
2. Installed `@supabase/ssr@^0.9.0` and `@supabase/supabase-js@^2.99.2`.
3. Created `src/lib/supabase/client.ts` — exports `createClient()` using `createBrowserClient` with `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` env vars.
4. Created `src/lib/supabase/server.ts` — exports async `createClient()` using `createServerClient` with `await cookies()` (Next.js 15+ async cookies) and `getAll`/`setAll` cookie handlers. The `setAll` try/catch handles the Server Component case where cookies can't be set.
5. Configured `next.config.ts` with `rewrites()` proxying `/api/:path*` → `http://localhost:8000/api/:path*`.
6. Created `.env.local.example` documenting both required env vars.
7. Replaced default `page.tsx` with server-side redirect to `/dashboard`.

## Verification

- `cd apps/web && npm run build` — exits 0, compiled successfully in 2.9s, zero type errors
- `cd apps/web && npm run dev` — starts successfully, listens on port 3000
- All 6 must-have checks pass:
  - ✓ package.json has next, react, @supabase/ssr, @supabase/supabase-js
  - ✓ client.ts exports createClient() using createBrowserClient
  - ✓ server.ts exports async createClient() using createServerClient with getAll/setAll
  - ✓ next.config.ts rewrites /api/* to localhost:8000
  - ✓ page.tsx redirects to /dashboard
  - ✓ .env.local.example documents both env vars
- Slice-level: only `npm run build` passes (1/8) — remaining checks depend on T02/T03

## Diagnostics

- **Build check:** `cd apps/web && npm run build` — must exit 0 with no type errors
- **Client wiring:** `cat apps/web/src/lib/supabase/client.ts` — should import from `@supabase/ssr`
- **Server wiring:** `cat apps/web/src/lib/supabase/server.ts` — should use `cookies()` from `next/headers`
- **Proxy config:** `grep -A3 'rewrites' apps/web/next.config.ts` — should show localhost:8000
- **Missing env vars:** Browser console will show Supabase client init errors if env vars not set

## Deviations

- Got Next.js 16.1.7 instead of 15 — `create-next-app@latest` installs the current latest. API is fully compatible (same App Router, same `cookies()` async behavior). No impact on downstream tasks.

## Known Issues

- Port 3000 had a pre-existing process during testing — Next.js dev server may auto-pick another port. Not a project issue.

## Files Created/Modified

- `apps/web/` — entire Next.js project scaffolded via create-next-app
- `apps/web/package.json` — includes next, react, @supabase/ssr, @supabase/supabase-js
- `apps/web/next.config.ts` — API proxy rewrite to FastAPI on port 8000
- `apps/web/src/lib/supabase/client.ts` — browser Supabase client wrapper
- `apps/web/src/lib/supabase/server.ts` — server Supabase client wrapper with cookie handlers
- `apps/web/src/app/page.tsx` — root redirect to /dashboard
- `apps/web/.env.local.example` — documents NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY
- `.gsd/milestones/M004/slices/S03/tasks/T01-PLAN.md` — added Observability Impact section
