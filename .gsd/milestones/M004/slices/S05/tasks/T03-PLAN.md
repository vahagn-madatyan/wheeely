---
estimated_steps: 3
estimated_files: 1
---

# T03: Build Call Screener page reusing shared results table

**Slice:** S05 — Screener UI
**Milestone:** M004

## Description

Build the Call Screener page following the same pattern as the Put Screener (T02), reusing the `ScreenerResultsTable` component. The call screener has a simpler form (single symbol + cost basis instead of symbols list + buying power) and adds a Cost Basis column to the results table.

## Steps

1. **Build `apps/web/src/app/(app)/screener/calls/page.tsx`** — full call screener page:
   - `'use client'` directive. Same imports as put screener: `useState`, `useEffect`, `useCallback`, `useRef`, `apiFetch`, `ScreenerResultsTable`, `ColumnDef`, `ProviderStatus`, `KeyStatusResponse`.
   - **Key status check on mount:** same pattern as put screener — fetch `GET /api/keys/status`, show "connect keys" message if Alpaca not connected.
   - **Form fields:**
     - Symbol: `<input type="text">` — single ticker (uppercase on submit), required
     - Cost Basis: `<input type="number" step="0.01" min="0.01">` — average entry price, required
     - Preset: `<select>` with same 3 options (conservative/moderate/aggressive), default "moderate"
   - **Submit handler:**
     - Trim and uppercase the symbol
     - Validate symbol not empty and cost_basis > 0
     - `POST /api/screen/calls` with body `{ symbol, cost_basis, preset }`
     - Start polling loop (same pattern as put screener)
   - **Polling:** identical to put screener — `setInterval` every 2s, `useEffect` cleanup on unmount
   - **Progress indicator:** same spinner pattern as put screener
   - **Results display:** `ScreenerResultsTable` with call-specific columns:
     - Symbol (sortable), Strike (sortable, $), DTE (sortable), Premium (sortable, $), Delta (sortable), OI (sortable, comma int), Spread (sortable), Ann. Return (sortable, %), Cost Basis (sortable, $)
     - Note: call results don't have a separate "Underlying" column — the underlying is the single symbol the user entered
   - **Error display:** same red alert pattern

2. **Define call-specific column config** as `const CALL_COLUMNS: ColumnDef[]` at the top of the file.

3. **Verify build** — `cd apps/web && npm run build` must exit 0 with both `/screener/puts` and `/screener/calls` in the output.

## Must-Haves

- [ ] Call Screener page replaces placeholder with full form + polling + results table
- [ ] Form has symbol input, cost basis input, preset select
- [ ] Submit triggers POST → poll loop with 2s interval
- [ ] Results table includes Cost Basis column
- [ ] Key status check shows "connect keys" if Alpaca not connected
- [ ] Polling cleans up on unmount
- [ ] `npm run build` passes with zero errors

## Verification

- `cd apps/web && npm run build` exits 0
- Build output includes both `ƒ /screener/puts` and `ƒ /screener/calls`
- `grep -c "apiFetch" apps/web/src/app/\(app\)/screener/calls/page.tsx` returns ≥3
- `grep "'use client'" apps/web/src/app/\(app\)/screener/calls/page.tsx` — present
- `grep -c "cost_basis\|costBasis\|Cost Basis" apps/web/src/app/\(app\)/screener/calls/page.tsx` — ≥2 (form field + column def)

## Inputs

- `apps/web/src/components/screener-results-table.tsx` — shared component from T02, exports `ScreenerResultsTable` and `ColumnDef`
- `apps/web/src/app/(app)/screener/puts/page.tsx` — reference pattern from T02 for the page structure, polling logic, key status check, and error handling. The call screener page follows the same architecture.
- `apps/web/src/lib/api-client.ts` — `apiFetch()` function
- `apps/web/src/components/provider-card.tsx` — `ProviderStatus`, `KeyStatusResponse` types
- T01 output — `POST /api/screen/calls` now expects body `{ symbol: string, cost_basis: number, preset: string }` + Bearer token. Returns `{ run_id, status }`. Poll same as puts.
- `apps/api/schemas.py` — `CallResultSchema` defines: symbol, underlying, strike, dte, premium, delta, oi, spread, annualized_return, cost_basis

## Observability Impact

- **Key-status gate:** If Alpaca not connected, page shows "Connect your Alpaca API keys" — inspect by looking for that text on load.
- **Polling state:** "Screening in progress…" text + spinner visible during active poll. Network tab shows `GET /api/screen/runs/{run_id}` at 2s intervals.
- **Error display:** All API errors render in `role="alert"` divs — check for red alert boxes on page.
- **Sort state:** Click any sortable column header — ▲/▼ indicator appears next to active sort column.
- **Failure visibility:** If screening completes with no results, table shows "No results found". If screening fails, poll returns `status: "failed"` and error text is displayed in alert.

## Expected Output

- `apps/web/src/app/(app)/screener/calls/page.tsx` — full call screener page replacing the placeholder (~180-220 lines)
