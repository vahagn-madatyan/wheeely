# S04: BYOK Key Management UI — Research

**Date:** 2026-03-17
**Depth:** Light

## Summary

S04 replaces the placeholder Settings page with a key management UI for Alpaca and Finnhub API keys. All backend infrastructure is complete — S02 provides 4 key CRUD endpoints (`POST /api/keys/{provider}`, `GET /api/keys/status`, `DELETE /api/keys/{provider}`, `POST /api/keys/{provider}/verify`) and S03 provides the authenticated app shell, Settings route, and `apiFetch()` client utility. The work is standard React form building using patterns already established in the login/signup pages (controlled inputs, loading states, error alerts, Tailwind styling).

No new libraries, APIs, or architectural patterns are needed. The API contract is fully defined in `apps/api/schemas.py` and tested with 14 endpoint tests. The UI needs to present forms for two providers, display connection status badges, and wire verify/delete actions.

## Recommendation

Build a single `'use client'` Settings page that:
1. Fetches key status on mount via `GET /api/keys/status`
2. Renders provider cards (Alpaca, Finnhub) showing connected/disconnected state with green/red badges
3. Each card has a form to enter keys (Alpaca: api_key + secret_key + paper/live toggle; Finnhub: api_key)
4. "Save & Verify" flow: stores keys via `POST /api/keys/{provider}`, then immediately verifies via `POST /api/keys/{provider}/verify`
5. Delete button per provider calls `DELETE /api/keys/{provider}` with confirmation

Keep it in one file (`settings/page.tsx`) — the page isn't complex enough to warrant extracted components. If the file exceeds ~250 lines, extract provider card components.

## Implementation Landscape

### Key Files

- `apps/web/src/app/(app)/settings/page.tsx` — placeholder to replace with full key management UI
- `apps/web/src/lib/api-client.ts` — `apiFetch()` handles auth header injection; all API calls go through this
- `apps/api/routers/keys.py` — backend endpoints the UI calls (already tested, no changes needed)
- `apps/api/schemas.py` — response shapes defining the API contract:
  - `KeyStatusResponse`: `{ providers: [{ provider, connected, is_paper, key_names }] }`
  - `KeyVerifyResponse`: `{ provider, valid, error? }`
  - `KeyStoreRequest`: `{ key_value, key_name, is_paper? }`
- `apps/web/src/app/(auth)/login/page.tsx` — reference for form styling conventions (controlled inputs, error alerts, loading states, Tailwind classes)
- `apps/web/src/components/logout-button.tsx` — reference for `'use client'` component pattern with Supabase client

### API Contract (from S02)

| Action | Method | Path | Body | Response |
|--------|--------|------|------|----------|
| Check status | GET | `/api/keys/status` | — | `{ providers: [{ provider, connected, is_paper, key_names }] }` |
| Store key | POST | `/api/keys/{provider}` | `{ key_value, key_name, is_paper? }` | `{ status: "stored", provider, key_name }` |
| Delete keys | DELETE | `/api/keys/{provider}` | — | `{ status: "deleted", provider }` |
| Verify keys | POST | `/api/keys/{provider}/verify` | — | `{ provider, valid, error? }` |

**Alpaca requires two separate store calls** — one for `key_name: "api_key"` and one for `key_name: "secret_key"`. The verify endpoint only works when both are stored.

**Finnhub requires one store call** — `key_name: "api_key"`.

### Build Order

1. **Key status fetching + provider cards with badges** — mount effect calls `GET /api/keys/status`, renders cards showing connected (green) or disconnected (gray/red) state per provider. This is the visual skeleton everything else builds on.
2. **Key input forms** — Alpaca card gets api_key + secret_key inputs + paper/live toggle. Finnhub card gets api_key input. Controlled inputs with loading/disabled states.
3. **Store + verify flow** — Submit handler stores keys (one or two POST calls), then calls verify. Show verify result as green check or red X with error message.
4. **Delete flow** — Delete button with confirmation (window.confirm or inline confirm state). On success, re-fetch status to update badges.

### Verification Approach

1. `cd apps/web && npm run build` — zero TypeScript errors, Settings route compiles
2. Visual verification in browser with running FastAPI + Supabase:
   - Navigate to `/settings` while authenticated
   - See Alpaca and Finnhub provider cards with disconnected state
   - Enter Alpaca keys, click Save → see stored confirmation
   - Click Verify → see green/red badge based on key validity
   - Enter Finnhub key, save and verify
   - Click Delete on a provider → keys removed, badge resets to disconnected
3. `python -m pytest tests/ -q` — 425 CLI tests still pass (no CLI files touched)

## Constraints

- `apiFetch()` throws `AuthSessionError` if no session — the Settings page is inside `(app)` route group which is middleware-protected, so session always exists at render time. No special error handling needed for auth.
- Alpaca keys must be stored as two separate API calls (api_key and secret_key) — the endpoint accepts one key per call. The UI should send both sequentially, not in parallel, to avoid partial-store states on error.
- `KeyStoreRequest.is_paper` is `Optional[bool]` — only meaningful for Alpaca. Finnhub calls should omit it or pass `null`.
- The verify endpoint tests connectivity by calling real Alpaca/Finnhub APIs — it can take 1-3 seconds. Show a loading spinner during verification.

## Common Pitfalls

- **Partial Alpaca store** — If the first store call (api_key) succeeds but the second (secret_key) fails, the user has a half-configured provider. Handle by attempting both calls and showing a clear error if either fails, with the option to retry.
- **Stale status after store/delete** — After any mutation, re-fetch `GET /api/keys/status` to ensure badges reflect actual state. Don't optimistically update — the source of truth is the API.
