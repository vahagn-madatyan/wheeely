---
id: T01
parent: S04
milestone: M004
provides:
  - Complete Settings page with Alpaca and Finnhub provider cards, key store/verify/delete flows
key_files:
  - apps/web/src/app/(app)/settings/page.tsx
key_decisions:
  - Kept all provider logic in a single page component (~310 lines) rather than extracting a ProviderCard component — T02 will extract if needed
patterns_established:
  - Per-provider form state pattern (loading, error, verifyResult) for independent async operations on the same page
  - Auto-verify after store pattern (save keys → auto POST verify → show result)
observability_surfaces:
  - role="alert" divs surface API errors inline per provider card
  - GET /api/keys/status is the single source of truth for connection state
  - Partial Alpaca store failure shows explicit "Failed to store secret key" message
  - Key values never logged or displayed post-submission (password inputs only)
duration: 12m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T01: Build Settings page with provider cards, key forms, and all CRUD flows

**Replaced placeholder Settings page with complete BYOK key management UI — Alpaca (api_key + secret_key + paper toggle) and Finnhub (api_key) provider cards with store, verify, and delete flows via apiFetch()**

## What Happened

Wrote a `'use client'` Settings page component that wires the frontend to the S02 key management backend endpoints. The page fetches `GET /api/keys/status` on mount and after every mutation to render green/gray connection badges per provider.

**Alpaca card:** Two password inputs (api_key, secret_key), a paper/live toggle switch (defaults to paper), and a "Save & Verify" button. On submit, sends two sequential POSTs — api_key first, then secret_key — with explicit error handling if the second call fails. Auto-verifies after store. When connected, shows badges (Connected + Paper/Live), stored key names, Verify button, and Delete button.

**Finnhub card:** Single password input (api_key), simpler save flow with one POST call. Same verify/delete pattern as Alpaca.

All API calls go through `apiFetch()` from `@/lib/api-client`. Error alerts use the same `bg-red-50 role="alert"` pattern as the login page. Loading states disable buttons and show "Saving…" / "Verifying…" / "Deleting…" text. Delete triggers `window.confirm()` before executing.

## Verification

- **`'use client'`** directive confirmed at line 1
- **`apiFetch` import** confirmed from `@/lib/api-client`
- **useEffect + status fetch** confirmed at lines 94, 105
- **POST/DELETE handlers** — 9 API calls across store, verify, and delete for both providers
- **3 password inputs** (alpaca api_key, alpaca secret_key, finnhub api_key)
- **Paper toggle** with checkbox input and isPaper state
- **Green/gray badge classes** present (bg-green-100, bg-gray-100)
- **Error alerts** — 5 `role="alert"` divs, 7 `bg-red-50` usages
- **window.confirm** — 2 calls (one per provider delete)
- **Loading states** — 6 loading text variants

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd apps/web && npm run build` | 0 | ✅ pass | 5.3s |
| 2 | `python -m pytest tests/ -q` | 0 | ✅ pass | 1.0s |
| 3 | Settings route in build output (`ƒ /settings`) | — | ✅ pass | — |
| 4 | Code-level checks (directive, imports, handlers, inputs, badges, alerts) | — | ✅ pass | — |

## Diagnostics

- **Inspect connection state:** `GET /api/keys/status` returns `{ providers: [{ provider, connected, is_paper, key_names }] }`
- **Error shapes:** API errors surface as `role="alert"` divs with error text from backend `detail` field or generic fallback
- **Partial store visibility:** If Alpaca api_key stores but secret_key fails, the inline error reads "Failed to store secret key — please retry"
- **Verify results:** Green `bg-green-50` banner for valid, red `bg-red-50` banner for invalid with backend error message

## Deviations

None — implementation follows the plan exactly.

## Known Issues

None.

## Files Created/Modified

- `apps/web/src/app/(app)/settings/page.tsx` — complete Settings page with Alpaca and Finnhub provider cards, key store/verify/delete flows (~310 lines)
- `.gsd/milestones/M004/slices/S04/tasks/T01-PLAN.md` — added missing Observability Impact section
