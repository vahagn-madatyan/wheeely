---
estimated_steps: 6
estimated_files: 8
---

# T01: Scaffold Next.js project and create Supabase client utilities

**Slice:** S03 — Next.js shell + auth flow
**Milestone:** M004

## Description

Create the `apps/web/` Next.js 15 App Router project with TypeScript + Tailwind CSS. Install `@supabase/ssr` and `@supabase/supabase-js`. Create Supabase browser and server client utility wrappers that T02 and T03 consume. Configure `next.config.ts` with an API proxy rewrite to FastAPI on port 8000.

**Skills to load:** `nextjs-supabase-auth` (at `~/.agents/skills/nextjs-supabase-auth/SKILL.md`), `nextjs-app-router-patterns` (at `~/.agents/skills/nextjs-app-router-patterns/SKILL.md`).

## Steps

1. **Scaffold the Next.js project** — Run `npx create-next-app@latest apps/web --typescript --tailwind --app --src-dir --no-import-alias --use-npm` from the repo root. Accept defaults (no ESLint prompt if asked, App Router yes, `src/` directory yes, Turbopack yes). Verify `apps/web/package.json` exists.

2. **Install Supabase dependencies** — `cd apps/web && npm install @supabase/ssr @supabase/supabase-js`. These are the only additional runtime deps needed for S03.

3. **Create Supabase browser client** — Create `apps/web/src/lib/supabase/client.ts`:
   - Export a `createClient()` function that calls `createBrowserClient` from `@supabase/ssr`
   - Use `process.env.NEXT_PUBLIC_SUPABASE_URL!` and `process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!`
   - This is used in Client Components (`'use client'`) for login, signup, logout

4. **Create Supabase server client** — Create `apps/web/src/lib/supabase/server.ts`:
   - Export an async `createClient()` function that calls `createServerClient` from `@supabase/ssr`
   - Import `cookies` from `next/headers` and call `await cookies()` (Next.js 15 makes cookies() async)
   - Pass `getAll` and `setAll` cookie handlers to `createServerClient` options — the `setAll` handler must iterate cookies and call `cookieStore.set(name, value, options)` for each
   - This is used in Server Components, middleware, and the auth callback route

5. **Configure next.config.ts** — Add a `rewrites()` function that proxies `/api/:path*` to `http://localhost:8000/api/:path*`. This lets the frontend call `/api/keys/status` which gets proxied to the FastAPI backend at port 8000 during development. Example:
   ```typescript
   async rewrites() {
     return [
       {
         source: '/api/:path*',
         destination: 'http://localhost:8000/api/:path*',
       },
     ]
   }
   ```

6. **Create env var example and root redirect** — Create `apps/web/.env.local.example` with:
   ```
   NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
   ```
   Update `apps/web/src/app/page.tsx` to redirect to `/dashboard` using `redirect()` from `next/navigation` (server-side redirect). This ensures the root URL enters the auth flow.

## Must-Haves

- [ ] `apps/web/package.json` exists with `next`, `react`, `@supabase/ssr`, `@supabase/supabase-js` as dependencies
- [ ] `apps/web/src/lib/supabase/client.ts` exports `createClient()` using `createBrowserClient` from `@supabase/ssr`
- [ ] `apps/web/src/lib/supabase/server.ts` exports async `createClient()` using `createServerClient` from `@supabase/ssr` with `getAll`/`setAll` cookie handlers
- [ ] `apps/web/next.config.ts` rewrites `/api/:path*` to `http://localhost:8000/api/:path*`
- [ ] Root `app/page.tsx` redirects to `/dashboard`
- [ ] `npm run build` succeeds with zero errors (inside `apps/web/`)

## Verification

- `cd apps/web && npm run build` — exits 0, no type errors
- `cd apps/web && npm run dev` — starts on port 3000
- `apps/web/src/lib/supabase/client.ts` and `server.ts` exist and import correctly from `@supabase/ssr`
- `apps/web/.env.local.example` documents `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`

## Inputs

- No prior task output — this is the first task in S03
- S02 provides: Supabase project URL and anon key (env vars, not hardcoded)
- `apps/api/main.py` — FastAPI runs on port 8000 with CORS allowing all origins

## Expected Output

- `apps/web/` — complete Next.js 15 project with TypeScript + Tailwind
- `apps/web/src/lib/supabase/client.ts` — browser Supabase client wrapper
- `apps/web/src/lib/supabase/server.ts` — server Supabase client wrapper with cookie handlers
- `apps/web/next.config.ts` — API proxy rewrite configured
- `apps/web/.env.local.example` — documents required env vars
- `apps/web/src/app/page.tsx` — redirects to `/dashboard`
