# S05: Screener UI — UAT

**Milestone:** M004
**Written:** 2026-03-17

## UAT Type

- UAT mode: mixed (artifact-driven for compilation + tests; live-runtime for full browser flow)
- Why this mode is sufficient: TypeScript build + 67 API tests prove contracts and type safety. Live-runtime UAT against running dev server proves the user-facing flow. Full end-to-end against deployed instance is deferred to S07.

## Preconditions

1. FastAPI dev server running: `cd apps/api && uvicorn apps.api.main:app --reload --port 8000`
2. Next.js dev server running: `cd apps/web && npm run dev` (defaults to port 3000)
3. Supabase project accessible with `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_JWT_SECRET` configured in `apps/web/.env.local` and `apps/api/.env`
4. `APP_ENCRYPTION_SECRET` and `DATABASE_URL` configured for the API
5. A test user account exists (sign up at `/signup` if needed)
6. The test user has Alpaca API keys stored (add via `/settings` if needed)
7. Alpaca paper trading keys with a funded account (for real screening results)
8. `.venv` activated with dependencies installed

## Smoke Test

Navigate to `/screener/puts` while logged in with connected Alpaca keys → form with Preset, Symbols, and Buying Power fields renders. If keys are not connected, a "Connect your Alpaca API keys" message with a link to Settings appears instead.

## Test Cases

### 1. Put Screener — full submit-to-results flow

1. Log in and navigate to `/screener/puts`
2. Confirm form renders with Preset (defaulting to "moderate"), Symbols textarea, Buying Power input, and "Run Screener" button
3. Select "conservative" preset
4. Enter `AAPL` and `MSFT` in Symbols (one per line)
5. Enter `50000` in Buying Power
6. Click "Run Screener"
7. **Expected:** Button text changes to "Screening…", form inputs become disabled, a spinning progress indicator and "Screening in progress…" text appear below the form
8. Wait for screening to complete (30-60s)
9. **Expected:** Results table appears with header "Results (N)" where N > 0, showing columns: Symbol, Underlying, Strike, DTE, Premium, Delta, OI, Spread, Ann. Return
10. Click the "Strike" column header
11. **Expected:** Rows sort by strike ascending, ▲ indicator appears next to "Strike"
12. Click "Strike" again
13. **Expected:** Rows sort descending, ▼ indicator appears
14. Click "Strike" a third time
15. **Expected:** Sort resets to original order, no indicator

### 2. Call Screener — full submit-to-results flow

1. Navigate to `/screener/calls`
2. Confirm form renders with Preset (defaulting to "moderate"), Symbol input, Cost Basis input, and "Run Screener" button
3. Enter `AAPL` as Symbol
4. Enter `175.00` as Cost Basis
5. Select "aggressive" preset
6. Click "Run Screener"
7. **Expected:** Progress indicator with "Screening in progress…" appears
8. Wait for screening to complete
9. **Expected:** Results table with columns: Symbol, Strike, DTE, Premium, Delta, OI, Spread, Ann. Return, Cost Basis. No "Underlying" column. Cost Basis column shows $175.00 for all rows.

### 3. Key-status gate — Alpaca not connected

1. Delete Alpaca keys from `/settings` (or use a fresh account with no keys stored)
2. Navigate to `/screener/puts`
3. **Expected:** Page shows "Connect your Alpaca API keys to use the screener." with a "Go to Settings" link. No form is rendered.
4. Click "Go to Settings"
5. **Expected:** Navigates to `/settings`
6. Navigate to `/screener/calls`
7. **Expected:** Same "Connect your Alpaca API keys" message, no form

### 4. Form validation errors

1. Navigate to `/screener/puts` with keys connected
2. Leave Symbols empty, enter `50000` for Buying Power, click "Run Screener"
3. **Expected:** Red alert box: "Enter at least one symbol"
4. Enter `AAPL` in Symbols, clear Buying Power, click "Run Screener"
5. **Expected:** Browser native validation prevents submission (required field)
6. Navigate to `/screener/calls`
7. Leave Symbol empty, enter `175` for Cost Basis, click "Run Screener"
8. **Expected:** Browser native validation prevents submission (required field)

### 5. Auth-required endpoints (API level)

1. Open a terminal and run: `curl -s http://localhost:8000/api/screen/puts -X POST -H "Content-Type: application/json" -d '{"symbols":["AAPL"],"buying_power":50000,"preset":"moderate"}'`
2. **Expected:** 401 response with `{"detail": "Not authenticated"}`
3. Run: `curl -s http://localhost:8000/api/screen/runs/fake-id`
4. **Expected:** 401 response
5. Run: `curl -s http://localhost:8000/api/positions`
6. **Expected:** 401 response
7. Run: `curl -s http://localhost:8000/api/account`
8. **Expected:** 401 response

## Edge Cases

### Empty screening results

1. Navigate to `/screener/puts`
2. Enter a very low buying power (e.g. `100`) with a high-priced symbol (e.g. `BRK.B`)
3. Click "Run Screener"
4. **Expected:** After polling completes, table area shows "No results found" message (not a crash or empty table with headers only)

### Screening failure

1. If Alpaca keys are invalid or expired, screening should fail
2. **Expected:** After polling, a red alert box appears with the error message from the backend. No infinite spinner.

### Page navigation during polling

1. Start a put screener run, see "Screening in progress…"
2. Navigate away (e.g. click "Call Screener" in sidebar)
3. Return to `/screener/puts`
4. **Expected:** No JavaScript errors in console. Page resets to form state (previous results are not preserved — this is a known limitation).

### Rapid double-submit

1. Click "Run Screener" and immediately try to click again
2. **Expected:** Button is disabled after first click (shows "Screening…"), preventing duplicate submissions

## Failure Signals

- Red alert boxes on screener pages indicate API errors (key status, submit, polling)
- "Screening in progress…" spinner that never resolves indicates a polling failure — check browser Network tab for failed `GET /api/screen/runs/{run_id}` requests
- "Connect your Alpaca API keys" message when keys are stored indicates a `GET /api/keys/status` failure
- Browser console errors (especially `TypeError` or `fetch` failures) indicate a broken `apiFetch()` path
- Empty results table without "No results found" message indicates a rendering bug

## Requirements Proved By This UAT

- WEB-05 — Put screener form → submit → poll → sortable results table (test case 1)
- WEB-06 — Call screener form → submit → poll → sortable results table with Cost Basis (test case 2)
- WEB-11 — Async screening with polling UI works end-to-end (test cases 1 and 2)

## Not Proven By This UAT

- WEB-07, WEB-08 — Positions dashboard and account summary (S06)
- WEB-09 — Rate limiting enforcement (S06)
- WEB-12 — Deployed on Render (S07)
- Multi-tenant isolation between two different users' screening results (S07 end-to-end)
- Screening results persistence in database (screener uses in-memory task store for MVP)

## Notes for Tester

- Screening runs take 30-60 seconds against live Alpaca data — this is expected, not a bug
- The "moderate" preset with 3-5 liquid large-cap symbols (AAPL, MSFT, GOOG, AMZN) against $50k+ buying power is the most likely to produce results
- "Conservative" preset with low buying power may produce zero results — that's valid behavior
- The Next.js dev server shows a middleware deprecation warning ("'middleware' file convention is deprecated") — this is a known Next.js 16 cosmetic warning documented in KNOWLEDGE.md and does not affect functionality
- Alpaca paper trading must be during/near market hours for options data to be available. If testing outside market hours, results may be empty or stale.
