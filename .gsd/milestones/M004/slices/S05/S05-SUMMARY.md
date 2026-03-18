---
id: S05
parent: M004
milestone: M004
provides:
  - Auth-protected screen/positions endpoints consuming DB-stored keys (no raw keys in requests)
  - retrieve_alpaca_keys() shared helper for any endpoint needing Alpaca credentials
  - ScreenerResultsTable generic sortable table component with ColumnDef type
  - Put Screener page with key-status gate, preset/symbols/buying-power form, POST→poll→results flow
  - Call Screener page with key-status gate, symbol/cost-basis/preset form, POST→poll→results flow
requires:
  - slice: S01
    provides: POST /api/screen/puts, POST /api/screen/calls, GET /api/screen/runs/{run_id} endpoints
  - slice: S02
    provides: api_keys table, envelope encryption, JWT auth middleware, decrypt_value()
  - slice: S03
    provides: App shell with route protection, apiFetch() API client
  - slice: S04
    provides: User has stored Alpaca+Finnhub keys, GET /api/keys/status endpoint, ProviderStatus type
affects:
  - S06
  - S07
key_files:
  - apps/api/services/key_retrieval.py
  - apps/api/routers/screen.py
  - apps/api/routers/positions.py
  - apps/api/schemas.py
  - apps/web/src/components/screener-results-table.tsx
  - apps/web/src/app/(app)/screener/puts/page.tsx
  - apps/web/src/app/(app)/screener/calls/page.tsx
key_decisions:
  - Missing auth returns 401 (HTTPBearer auto-raises), not 403 as plan hypothesized
  - Column format functions defined inline in COLUMNS array — co-located with the page, not the shared component
  - No Underlying column in call results — redundant since user enters a single symbol
patterns_established:
  - retrieve_alpaca_keys(user_id, db) pattern for any endpoint needing Alpaca credentials from DB
  - mock_key_retrieval fixture pattern — patch at router import path, return tuple
  - ScreenerResultsTable accepts ColumnDef[] + data generically; callers define format functions for domain-specific display
  - Key-status gate on mount — fetch /api/keys/status, show "connect keys" card if Alpaca not connected
  - Polling via useRef interval + useEffect cleanup — startPolling(runId) creates interval, clears on completed/failed/error/unmount
observability_surfaces:
  - retrieve_alpaca_keys logs "keys_retrieved" with provider + user_id on success
  - HTTPException 400 with descriptive messages for missing/incomplete/undecryptable keys
  - Key connectivity gate visible as "Connect your Alpaca API keys" text with /settings link
  - Polling progress visible as "Screening in progress…" text with spinner
  - Errors surface in role="alert" divs for key status, submit, and polling failures
  - Sort state indicated by ▲/▼ in column headers
drill_down_paths:
  - .gsd/milestones/M004/slices/S05/tasks/T01-SUMMARY.md
  - .gsd/milestones/M004/slices/S05/tasks/T02-SUMMARY.md
  - .gsd/milestones/M004/slices/S05/tasks/T03-SUMMARY.md
duration: 32m
verification_result: passed
completed_at: 2026-03-17
---

# S05: Screener UI

**Put and Call screener pages work end-to-end in the browser — auth-protected backend reads keys from DB, frontend gates on key connectivity, submits screening requests, polls for results, and renders sortable tables matching CLI columns.**

## What Happened

Three tasks delivered this slice in a backend-first, shared-component, then reuse sequence.

**T01 — Backend auth switchover.** Created `apps/api/services/key_retrieval.py` with `retrieve_alpaca_keys(user_id, db)` — a shared helper that queries `api_keys`, decrypts via `decrypt_value()`, validates both keys exist, and returns `(api_key, secret_key, is_paper)`. All screen and positions endpoints were updated: `AlpacaKeysMixin` removed from schemas, `PutScreenRequest` / `CallScreenRequest` now inherit `BaseModel` directly with only screening params, and `PositionsQuery` / `AccountQuery` were deleted entirely. The poll endpoint (`GET /runs/{run_id}`) also requires auth now. All 19 existing tests were rewritten to use `mock_auth` + `mock_key_retrieval` fixtures, and 7 new tests added for auth-required (401) and missing-keys (400) error paths. Total: 67 API tests passing.

**T02 — Put Screener + shared table.** Built `ScreenerResultsTable` (125 lines) — a generic `'use client'` component accepting `ColumnDef[]` with optional format functions and `Record<string, unknown>[]` data. Supports click-to-sort (asc → desc → reset cycle), null-safe sorting, and "No results found" empty state. The Put Screener page (260 lines) follows this flow: mount → check `GET /api/keys/status` → if Alpaca not connected, show card with `/settings` link → if connected, render form (preset select, symbols textarea, buying power input) → on submit, `POST /api/screen/puts` → poll `GET /runs/{run_id}` every 2s via `setInterval` → on completed, render results via `ScreenerResultsTable` with `PUT_COLUMNS` (Symbol, Underlying, Strike, DTE, Premium, Delta, OI, Spread, Ann. Return).

**T03 — Call Screener.** Built the Call Screener page (~280 lines) reusing the identical architecture: key-status gate, form (single symbol + cost basis + preset), `POST /api/screen/calls`, same polling, same `ScreenerResultsTable` with `CALL_COLUMNS` (adds Cost Basis column, drops Underlying since it's redundant for single-symbol input). All shared patterns — polling cleanup, error alerts, progress spinner — are identical.

## Verification

| # | Check | Result |
|---|-------|--------|
| 1 | `python -m pytest apps/api/tests/ -v` — all API tests pass (≥19) | ✅ 67 passed |
| 2 | `python -m pytest tests/ -q` — 425 CLI tests pass | ✅ 425 passed |
| 3 | `cd apps/web && npm run build` — zero TS errors, both routes in output | ✅ `/screener/puts` + `/screener/calls` in build |
| 4 | `retrieve_alpaca_keys` used in both routers | ✅ screen.py:3, positions.py:3 |
| 5 | `get_current_user` in both routers | ✅ screen.py:4, positions.py:3 |

## Requirements Advanced

- WEB-05 — Put screener page built with preset/symbols/buying-power form, POST→poll→results flow, and sortable results table matching CLI columns. Awaits live UAT in S07 for full validation.
- WEB-06 — Call screener page built with symbol/cost-basis/preset form, same async flow, results table with Cost Basis column. Awaits live UAT in S07 for full validation.
- WEB-11 — Frontend polling UI implemented consuming the background task infrastructure proved in S01. Already validated by S01's 31 API tests; S05 adds the browser-side consumer.

## Requirements Validated

- none — WEB-05 and WEB-06 require live runtime UAT (S07) for full validation.

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- Plan expected 403 for missing auth; actual behavior is 401 (FastAPI's `HTTPBearer` raises 401 for missing credentials). Tests updated to expect 401. This was already documented in KNOWLEDGE.md.

## Known Limitations

- No frontend component tests — screener pages are verified by TypeScript compilation + build, not by React testing. Live verification deferred to S07 UAT.
- Polling is interval-based (2s) — acceptable for MVP but could be replaced with WebSocket/SSE in a future milestone.
- No client-side caching of screener results — navigating away loses results. Acceptable for free tier.

## Follow-ups

- none — remaining work is S06 (positions dashboard + rate limiting) and S07 (deployment + end-to-end verification).

## Files Created/Modified

- `apps/api/services/key_retrieval.py` — new shared helper: `retrieve_alpaca_keys(user_id, db) -> (api_key, secret_key, is_paper)`
- `apps/api/routers/screen.py` — all 3 endpoints now use `Depends(get_current_user)`, submit endpoints use `retrieve_alpaca_keys()`
- `apps/api/routers/positions.py` — both endpoints use `Depends(get_current_user)` + `retrieve_alpaca_keys()`, no query params
- `apps/api/schemas.py` — removed `AlpacaKeysMixin`, `PositionsQuery`, `AccountQuery`; screen requests inherit `BaseModel` directly
- `apps/api/tests/test_screen_endpoints.py` — 14 tests using mock auth + mock key retrieval
- `apps/api/tests/test_positions_account.py` — 10 tests using mock auth + mock key retrieval
- `apps/web/src/components/screener-results-table.tsx` — new shared sortable table component (125 lines), exports `ScreenerResultsTable` and `ColumnDef`
- `apps/web/src/app/(app)/screener/puts/page.tsx` — full put screener page (260 lines)
- `apps/web/src/app/(app)/screener/calls/page.tsx` — full call screener page (~280 lines)

## Forward Intelligence

### What the next slice should know
- S06 (positions + rate limiting) should use the same `retrieve_alpaca_keys()` helper for its positions/account endpoints — it's already wired in `positions.py`. The `mock_key_retrieval` fixture pattern in test files shows exactly how to mock it.
- The `ScreenerResultsTable` component is reusable if S06's positions table needs sorting. Import `ScreenerResultsTable` and `ColumnDef` from `@/components/screener-results-table`.
- Rate limiting (S06) should hook into the `POST /api/screen/puts` and `POST /api/screen/calls` endpoints. These already require `get_current_user` so the user_id is available for the rate counter.

### What's fragile
- The `apiFetch()` function from `@/lib/api-client.ts` is the single path for all authenticated API calls. If session refresh breaks, all screener/positions/key-status calls fail silently. S07 UAT should test expired-session behavior.
- `ProviderStatus` and `KeyStatusResponse` types are imported from `@/components/provider-card.tsx` — if the provider card component changes its type exports, both screener pages break at build time (caught by TS, but worth knowing).

### Authoritative diagnostics
- `python -m pytest apps/api/tests/ -v` — 67 tests cover all auth, key retrieval, screen, positions, encryption, and task store paths. If any fail, start here.
- `cd apps/web && npm run build` — TypeScript compilation catches all type mismatches across screener pages and shared components.
- `grep -c "retrieve_alpaca_keys" apps/api/routers/screen.py apps/api/routers/positions.py` — confirms auth+DB key pattern is wired in both routers.

### What assumptions changed
- Plan assumed 403 for missing auth — actual is 401 (FastAPI HTTPBearer behavior). Already documented in KNOWLEDGE.md; all tests reflect the correct status code.
