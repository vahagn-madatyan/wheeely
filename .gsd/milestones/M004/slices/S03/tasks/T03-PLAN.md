---
estimated_steps: 5
estimated_files: 7
---

# T03: Build authenticated app shell with sidebar, placeholder pages, and API client

**Slice:** S03 — Next.js shell + auth flow
**Milestone:** M004

## Description

Create the authenticated app shell layout with sidebar navigation, placeholder pages for downstream slices (Dashboard, Put Screener, Call Screener, Settings), a working logout button, and the `apiFetch()` API client utility that S04-S06 consume to call the FastAPI backend with auth headers.

**Skills to load:** `nextjs-app-router-patterns` (at `~/.agents/skills/nextjs-app-router-patterns/SKILL.md`).

**Key context from S02:**
- FastAPI's `get_current_user` expects `Authorization: Bearer <supabase_access_token>`
- `GET /api/keys/status` returns `{"providers": [{"provider": "alpaca", "connected": true, ...}]}`
- The Next.js API proxy rewrite in `next.config.ts` forwards `/api/:path*` to `http://localhost:8000/api/:path*`

## Steps

1. **Create the API client utility** — Create `apps/web/src/lib/api-client.ts`:
   - Export an async `apiFetch(path: string, options?: RequestInit)` function
   - Import `createClient` from `@/lib/supabase/client` (browser client)
   - Get the session: `const { data: { session } } = await supabase.auth.getSession()`
   - If no session, throw an error or redirect to `/login` (caller handles this)
   - Set `Authorization: Bearer ${session.access_token}` header
   - Call `fetch(path, { ...options, headers: { ...options?.headers, Authorization: ... } })`
   - Return the Response object (caller handles JSON parsing)
   - The path should be relative (e.g., `/api/keys/status`) — Next.js rewrites proxy it to FastAPI

2. **Create the app shell layout** — Create `apps/web/src/app/(app)/layout.tsx`:
   - This is a **server component** (no `'use client'`)
   - Import `createClient` from `@/lib/supabase/server` (server client)
   - Call `const { data: { user } } = await supabase.auth.getUser()` to get the authenticated user
   - Render a two-column layout with Tailwind:
     - **Left sidebar** (fixed width, e.g., `w-64`): app name "Wheeely" at top, navigation links using Next.js `<Link>`:
       - Dashboard → `/dashboard`
       - Put Screener → `/screener/puts`
       - Call Screener → `/screener/calls`
       - Settings → `/settings`
     - **Main content area**: top bar showing user email (`user?.email`), a `<LogoutButton />` client component, and `{children}` below
   - Style the sidebar with a dark background (e.g., `bg-gray-900 text-white`) for visual contrast
   - Active link highlighting: pass `pathname` from layout is not possible in server components, so create a `<NavLinks />` client component that uses `usePathname()` to highlight the active route

3. **Create the NavLinks client component** — Create `apps/web/src/components/nav-links.tsx`:
   - `'use client'` directive
   - Import `usePathname` from `next/navigation` and `Link` from `next/link`
   - Define nav items array: `[{ label: 'Dashboard', href: '/dashboard' }, { label: 'Put Screener', href: '/screener/puts' }, { label: 'Call Screener', href: '/screener/calls' }, { label: 'Settings', href: '/settings' }]`
   - Render each as a `<Link>` with active state styling (e.g., `bg-gray-700` when `pathname === href` or `pathname.startsWith(href)`)
   - Use icons or simple text — keep it clean and functional

4. **Create the LogoutButton client component** — Create `apps/web/src/components/logout-button.tsx`:
   - `'use client'` directive
   - Import `createClient` from `@/lib/supabase/client` and `useRouter` from `next/navigation`
   - On click: call `await supabase.auth.signOut()`, then `router.push('/login')`, then `router.refresh()`
   - Render as a button with "Sign out" text, styled with Tailwind

5. **Create placeholder pages** — Create 4 placeholder pages in `apps/web/src/app/(app)/`:
   - `dashboard/page.tsx`: heading "Dashboard", subtitle "Your positions and account overview will appear here." (content built in S06)
   - `screener/puts/page.tsx`: heading "Put Screener", subtitle "Screen for cash-secured puts. Coming soon." (content built in S05)
   - `screener/calls/page.tsx`: heading "Call Screener", subtitle "Screen for covered calls. Coming soon." (content built in S05)
   - `settings/page.tsx`: heading "Settings", subtitle "Manage your API keys and preferences. Coming soon." (content built in S04)
   - Each page is a simple server component with a heading and description text. Use consistent Tailwind styling.

## Must-Haves

- [ ] `apiFetch()` utility reads Supabase session and injects `Authorization: Bearer <token>` header
- [ ] App shell layout renders sidebar with all 4 nav links (Dashboard, Put Screener, Call Screener, Settings)
- [ ] Active nav link is visually highlighted
- [ ] User email displayed in top bar
- [ ] Logout button signs out and redirects to `/login`
- [ ] All 4 placeholder pages render with heading text
- [ ] `npm run build` succeeds with zero errors

## Verification

- `cd apps/web && npm run build` — exits 0
- Authenticated user sees sidebar with 4 nav links
- Clicking each nav link renders the corresponding placeholder page
- Active link is highlighted in the sidebar
- User email visible in the top bar
- Click "Sign out" → redirected to `/login`
- In browser devtools: `apiFetch('/api/keys/status')` sends `Authorization: Bearer <token>` header on network request

## Inputs

- `apps/web/src/lib/supabase/client.ts` — browser client (T01)
- `apps/web/src/lib/supabase/server.ts` — server client (T01)
- `apps/web/src/middleware.ts` — route protection (T02) ensures only authenticated users reach `(app)` routes
- `apps/web/next.config.ts` — API proxy rewrite (T01)
- FastAPI `get_current_user` (S02) expects `Authorization: Bearer <supabase_access_token>` — this is what `apiFetch()` must send

## Expected Output

- `apps/web/src/lib/api-client.ts` — API client with auth header injection
- `apps/web/src/app/(app)/layout.tsx` — authenticated app shell with sidebar
- `apps/web/src/components/nav-links.tsx` — sidebar nav with active state
- `apps/web/src/components/logout-button.tsx` — logout button component
- `apps/web/src/app/(app)/dashboard/page.tsx` — placeholder Dashboard page
- `apps/web/src/app/(app)/screener/puts/page.tsx` — placeholder Put Screener page
- `apps/web/src/app/(app)/screener/calls/page.tsx` — placeholder Call Screener page
- `apps/web/src/app/(app)/settings/page.tsx` — placeholder Settings page
