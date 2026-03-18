---
id: T03
parent: S05
milestone: M004
provides:
  - Full Call Screener page with key-status gate, form, POST→poll→results flow, and sortable results table with Cost Basis column
key_files:
  - apps/web/src/app/(app)/screener/calls/page.tsx
key_decisions:
  - No "Underlying" column in call results — single symbol entered by user makes it redundant
patterns_established:
  - Call screener follows identical architecture to put screener (key gate → form → POST → poll → results)
observability_surfaces:
  - Key-status gate text "Connect your Alpaca API keys" visible when Alpaca not connected
  - "Screening in progress…" text + spinner during active poll
  - Error alerts rendered in role="alert" divs
  - Sort indicator ▲/▼ on active column header
  - Empty table shows "No results found"
duration: 8m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T03: Build Call Screener page reusing shared results table

**Built full Call Screener page with symbol/cost-basis/preset form, POST→poll→results flow, and sortable results table including Cost Basis column**

## What Happened

Replaced the placeholder Call Screener page with a full implementation following the same architecture as the Put Screener (T02). The page reuses the shared `ScreenerResultsTable` component with call-specific `CALL_COLUMNS` definitions.

Key differences from the put screener:
- **Simpler form:** single symbol text input + cost basis number input (vs. symbols textarea + buying power)
- **Column set:** 9 columns without "Underlying" (redundant since user enters one symbol), but with "Cost Basis" column added
- **API endpoint:** `POST /api/screen/calls` with `{ symbol, cost_basis, preset }` body

All shared patterns are identical: key-status gate on mount, 2s poll interval, `useEffect` cleanup, error alerts, progress spinner.

## Verification

- `npm run build` exits 0 — both `/screener/puts` and `/screener/calls` in build output
- `apiFetch` count = 4 (≥3 required)
- `'use client'` directive present
- `cost_basis/costBasis/Cost Basis` count = 9 (≥2 required)
- 67 API tests pass, 425 CLI tests pass
- `retrieve_alpaca_keys` used in both routers (3+3)
- `get_current_user` used in both routers (4+3)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd apps/web && npm run build` | 0 | ✅ pass | 5.6s |
| 2 | `grep -c "apiFetch" calls/page.tsx` | 0 | ✅ pass (4) | <1s |
| 3 | `grep "'use client'" calls/page.tsx` | 0 | ✅ pass | <1s |
| 4 | `grep -c "cost_basis\|costBasis\|Cost Basis" calls/page.tsx` | 0 | ✅ pass (9) | <1s |
| 5 | `.venv/bin/python -m pytest apps/api/tests/ -v` | 0 | ✅ pass (67) | 8.7s |
| 6 | `.venv/bin/python -m pytest tests/ -q` | 0 | ✅ pass (425) | 1.2s |
| 7 | `grep -c "retrieve_alpaca_keys" screen.py positions.py` | 0 | ✅ pass (3+3) | <1s |
| 8 | `grep -c "get_current_user" screen.py positions.py` | 0 | ✅ pass (4+3) | <1s |

## Diagnostics

- **Key-status gate:** Look for "Connect your Alpaca API keys" text on page to confirm gate is active. If Alpaca connected, form renders instead.
- **Polling state:** "Screening in progress…" text + spinner visible during active poll. Network tab shows `GET /api/screen/runs/{run_id}` at 2s intervals.
- **Error display:** All API errors render in `role="alert"` divs — check for red alert boxes on page.
- **Sort state:** Click any sortable column header — ▲/▼ indicator appears next to active sort column.
- **Empty results:** If screening completes with no results, table shows "No results found" message.

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `apps/web/src/app/(app)/screener/calls/page.tsx` — full call screener page replacing placeholder (~280 lines)
- `.gsd/milestones/M004/slices/S05/tasks/T03-PLAN.md` — added missing Observability Impact section
