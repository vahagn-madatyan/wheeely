# S03: Next.js shell + auth flow — UAT

**Milestone:** M004
**Written:** 2026-03-16

## UAT Type

- UAT mode: mixed (artifact-driven build verification + live-runtime auth flow)
- Why this mode is sufficient: Build verification confirms all routes compile and TypeScript is correct. Live runtime with a real Supabase instance is needed to verify auth flows end-to-end (signup, login, session persistence, logout, route protection).

## Preconditions

1. `apps/web/.env.local` exists with valid Supabase credentials:
   - `NEXT_PUBLIC_SUPABASE_URL` — real Supabase project URL
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` — real Supabase anon key
2. Supabase project has email auth provider enabled (S02 prerequisite)
3. Dev server running: `cd apps/web && npm run dev` (port 3000)
4. FastAPI backend NOT required for this slice's UAT (API calls will 502 — that's expected, verifiable in S04+)

## Smoke Test

Visit `http://localhost:3000` in a browser. You should be redirected to `/login` and see a login form with "Sign in to Wheeely" heading.

## Test Cases

### 1. Unauthenticated redirect — protected routes

1. Open browser to `http://localhost:3000/dashboard`
2. **Expected:** Redirected to `/login` (URL changes to `/login`)
3. Navigate to `http://localhost:3000/screener/puts`
4. **Expected:** Redirected to `/login`
5. Navigate to `http://localhost:3000/screener/calls`
6. **Expected:** Redirected to `/login`
7. Navigate to `http://localhost:3000/settings`
8. **Expected:** Redirected to `/login`

### 2. Login page renders correctly

1. Navigate to `http://localhost:3000/login`
2. **Expected:** Page renders with:
   - "Sign in to Wheeely" heading
   - Email input with "you@example.com" placeholder
   - Password input with "••••••••" placeholder
   - "Sign in" submit button
   - "Don't have an account? Sign up" link at bottom

### 3. Signup page renders correctly

1. Click "Sign up" link on login page (or navigate to `/signup`)
2. **Expected:** Page renders with:
   - "Create your Wheeely account" heading
   - Email input with "you@example.com" placeholder
   - Password input with "••••••••" placeholder
   - "Sign up" submit button
   - "Already have an account? Sign in" link at bottom

### 4. Sign up with valid email

1. On `/signup`, enter a valid email and password (min 6 chars for Supabase default)
2. Click "Sign up"
3. **Expected:** Page changes to show "Check your email" heading with message: "Check your email for a confirmation link. Once confirmed, you can sign in to your account."
4. "Back to sign in" button appears

### 5. Login with valid credentials

1. Confirm the signup email (click link in email)
2. Navigate to `/login`
3. Enter the email and password used during signup
4. Click "Sign in"
5. **Expected:** Redirected to `/dashboard`. Sidebar is visible on the left.

### 6. Authenticated app shell renders correctly

1. After successful login (from test 5)
2. **Expected:** Left sidebar (dark background) shows:
   - "Wheeely" branding at top
   - 4 navigation links: Dashboard, Put Screener, Call Screener, Settings
   - "Dashboard" link is highlighted (active state)
3. Top bar shows user email on the right with "Sign out" button
4. Main content area shows "Dashboard" heading

### 7. Sidebar navigation works

1. Click "Put Screener" in sidebar
2. **Expected:** URL changes to `/screener/puts`, page shows "Put Screener" heading, "Put Screener" link is highlighted in sidebar
3. Click "Call Screener" in sidebar
4. **Expected:** URL changes to `/screener/calls`, page shows "Call Screener" heading
5. Click "Settings" in sidebar
6. **Expected:** URL changes to `/settings`, page shows "Settings" heading
7. Click "Dashboard" in sidebar
8. **Expected:** URL changes to `/dashboard`, page shows "Dashboard" heading

### 8. Logout flow

1. While authenticated, click "Sign out" button in top bar
2. **Expected:** Redirected to `/login`
3. Navigate to `/dashboard`
4. **Expected:** Redirected to `/login` (session is cleared)

### 9. Authenticated user redirected from auth pages

1. While authenticated (log in first), navigate to `/login`
2. **Expected:** Redirected to `/dashboard`
3. Navigate to `/signup`
4. **Expected:** Redirected to `/dashboard`

### 10. API client sends auth header

1. While authenticated, open browser DevTools → Network tab
2. In browser console, run: `import('/lib/api-client').then(m => m.apiFetch('/api/keys/status'))`
   (Or wait for S04 which calls apiFetch — alternatively verify in source code)
3. **Expected:** Network request to `/api/keys/status` includes `Authorization: Bearer <token>` header
4. Response will be 502 (FastAPI not running) — that's expected; verify the header was sent

## Edge Cases

### Login with invalid credentials

1. On `/login`, enter a non-existent email or wrong password
2. Click "Sign in"
3. **Expected:** Red error alert appears below heading with Supabase error message (e.g., "Invalid login credentials"). Form remains on page.

### Signup with existing email

1. On `/signup`, enter an email that already has an account
2. Click "Sign up"
3. **Expected:** Either error alert or success state (Supabase may silently succeed for security — both behaviors are acceptable)

### Login with empty form

1. On `/login`, click "Sign in" without entering email or password
2. **Expected:** Browser's native HTML validation prevents submission (inputs have `required` attribute)

### Root URL redirect

1. Navigate to `http://localhost:3000/`
2. **Expected:** Redirected to `/dashboard` (if authenticated) or `/login` (if not, via middleware chain)

### Auth callback without code

1. Navigate to `http://localhost:3000/auth/callback` (no `?code=` param)
2. **Expected:** Redirected to `/login`

### Auth callback with invalid code

1. Navigate to `http://localhost:3000/auth/callback?code=invalid`
2. **Expected:** Redirected to `/login?error=auth`

## Failure Signals

- Build fails: `npm run build` exits non-zero → TypeScript or import errors
- Middleware not working: navigating to `/dashboard` unauthenticated shows a blank page or error instead of redirecting to `/login`
- Auth pages crash: white screen or console errors on `/login` or `/signup`
- Sidebar missing: authenticated user sees content but no sidebar navigation
- Logout doesn't clear session: clicking "Sign out" doesn't redirect, or revisiting `/dashboard` after logout still works
- API client missing auth: network requests from apiFetch() lack `Authorization` header

## Requirements Proved By This UAT

- WEB-01 — Email signup/login via Supabase Auth, JWT-based session, protected routes redirect to login (proven when tests 1-5 and 8-9 pass with real Supabase)

## Not Proven By This UAT

- WEB-02 through WEB-13 — key storage, screener UI, positions, rate limiting, deployment (S04-S07)
- Multi-tenant isolation (WEB-10) — requires two separate user accounts in S07 UAT
- apiFetch integration with real FastAPI endpoints — requires S04+ with running backend

## Notes for Tester

- You need a real Supabase project with email auth enabled. If you completed S02, the project already exists — use those credentials.
- The "check your email" step in signup requires access to the email inbox. Supabase allows disabling email confirmation in project settings (Auth → Providers → Email → disable "Confirm email") for faster testing.
- Next.js 16 shows a middleware deprecation warning in the terminal — this is expected and does not affect functionality.
- FastAPI backend is not needed for this slice's UAT. API calls will return 502 (proxy target unavailable) — that's correct behavior.
- The 4 placeholder pages (Dashboard, Put Screener, Call Screener, Settings) show "coming soon" messages — this is intentional; real content arrives in S04-S06.
