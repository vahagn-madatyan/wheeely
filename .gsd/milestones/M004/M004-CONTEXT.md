# M004: Free Tier Online — Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

## Project Description

Wheeely is an options wheel strategy bot with a mature CLI screening pipeline (425 tests, 4-stage funnel, 3 presets, symmetric put/call screeners). M004 brings the free-tier experience online as a multi-tenant SaaS — traders sign up, connect their own Alpaca + Finnhub keys (BYOK), run screeners in a browser, and see their positions. The CLI stays untouched.

## Why This Milestone

The CLI works well for a single trader on their own machine. But the goal is a SaaS product other traders can use. M004 is the minimum viable platform — proving that the existing screening engine can serve multiple users concurrently with proper isolation, encrypted key storage, and a usable web interface. Everything after this (billing, premium data, auto-trading, LLM) layers on top.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Sign up with email, log in, and see an authenticated dashboard
- Connect their Alpaca (paper/live) and Finnhub API keys from a settings page, with connectivity verification
- Run the put screener from a browser with preset selection and get ranked results in a sortable table
- Run the call screener from a browser with symbol + cost basis input
- View their current Alpaca positions with wheel state (short_put / long_shares / short_call)
- See account summary (buying power, capital at risk)
- Hit a rate limit after 3 screening runs per day (free tier)

### Entry point / environment

- Entry point: Browser URL (deployed Render instance) + `localhost:3000` for dev
- Environment: Render (web + api + redis) for production; Docker Compose for local dev
- Live dependencies involved: Supabase (auth + DB + vault), Redis (rate limiting + screening state), Alpaca API (user's keys), Finnhub API (user's keys)

## Completion Class

- Contract complete means: FastAPI endpoints return correct JSON for mocked screener calls; auth flow issues/verifies JWTs; key encryption/decryption round-trips; rate limiting enforces 3/day; frontend renders all pages with test data
- Integration complete means: Full vertical flow works with real Supabase instance and real API keys — sign up, store keys, run screener, see results, see positions
- Operational complete means: Deployed on Render via Blueprint; services communicate over private network; cold restart recovers cleanly

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- A new user can sign up, connect Alpaca + Finnhub keys, run the put screener, and see results — on the deployed Render instance
- A second user's data is fully isolated from the first (different keys, different results, different positions)
- Rate limiting blocks the 4th screening run within 24 hours
- The CLI continues to work exactly as before (425 tests still pass, `run-strategy` unaffected)

## Risks and Unknowns

- **Per-request client construction** — Current code constructs Alpaca/Finnhub clients from env vars at import time. Multi-tenant requires per-request construction from decrypted keys. Must refactor client initialization without touching CLI code paths.
- **Async screening over HTTP** — CLI screening runs take 30-60 seconds. Can't block an HTTP request. Need background task pattern with status polling or WebSocket.
- **Envelope encryption for API keys** — Storing brokerage credentials for other people's money. Security-critical. Must get Supabase Vault + envelope encryption right.
- **Monorepo structure** — Introducing `apps/api/` and `apps/web/` while keeping CLI entry points working from the root. Import paths must not break.
- **Render private networking** — Next.js → FastAPI over internal network, not public internet. Must verify this works with Supabase Auth JWTs.

## Existing Codebase / Prior Art

- `screener/pipeline.py` — 1347-line pipeline orchestrator. M004 wraps this, doesn't modify it.
- `screener/put_screener.py` — `screen_puts()` function M004's API will call per-user
- `screener/call_screener.py` — `screen_calls()` function M004's API will call per-user
- `core/broker_client.py` — `BrokerClient` wrapping 3 Alpaca SDK clients. Currently uses module-level env vars. Multi-tenant will construct per-request.
- `core/state_manager.py` — `update_state()` mapping positions to wheel states. API will call this per-user.
- `config/credentials.py` — Module-level env var loading. CLI path unchanged; API path constructs clients from decrypted keys.
- `screener/config_loader.py` — Preset loading. Shared between CLI and web.
- `screener/finnhub_client.py` — Rate-limited Finnhub wrapper. Multi-tenant needs per-user instances.

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- WEB-01 through WEB-13 — All free-tier online requirements (see REQUIREMENTS.md)
- CLI-COMPAT-01 — CLI must remain fully functional and untouched

## Scope

### In Scope

- FastAPI backend wrapping existing screening engine for multi-tenant use
- Supabase Auth (email signup/login), database schema, RLS policies
- Encrypted API key storage (envelope encryption)
- Next.js frontend: auth flow, dashboard, put screener, call screener, settings
- Per-user rate limiting (3 screening runs/day free tier)
- Render deployment (Blueprint, Docker Compose for local dev)
- `/premium` directory structure (inert — tier detection only, no premium features)

### Out of Scope / Non-Goals

- Stripe billing / payment processing (M005)
- FMP or ORATS data provider integration (M005+)
- Cloud auto-trading (M006+)
- LLM analysis agents (M006+)
- Manual trade execution from web UI (M005+)
- Watchlists, trade journal, P&L charts (M005+)
- Notifications (M006+)
- WebSocket for live screening progress (can use polling for MVP)

## Technical Constraints

- Python 3.13 for API (matching CLI)
- Next.js 15 with App Router
- Supabase for auth + DB (not self-hosted Postgres — managed service)
- Redis for rate limiting and screening run state
- Render for deployment (not AWS/GCP — simpler, cheaper at this scale)
- BYOK model: platform never stores its own API keys for data providers
- CLI import paths must not change — `pyproject.toml` console scripts still work from root

## Integration Points

- **Supabase** — Auth (JWT issuance + verification), Postgres (user data, screening results), key storage
- **Alpaca API** — Per-user brokerage operations (positions, account, options chains) via user's decrypted keys
- **Finnhub API** — Per-user fundamental data via user's decrypted key
- **Redis** — Rate limiting counters, screening run status/results cache
- **Render** — Hosting (web, api, redis services), private networking between services

## Open Questions

- **Supabase Vault vs application-level encryption** — Supabase Vault is Postgres-native but has limited SDK support in Python. May need application-level envelope encryption (encrypt in FastAPI, store ciphertext in regular Postgres column) instead of native Vault. Will decide in S02.
- **Turborepo vs simpler monorepo** — The expansion doc specifies Turborepo, but for two apps it may be overkill. Simple `apps/` directory with separate package.json and pyproject.toml may suffice. Will decide in S01.
- **Alpaca OAuth vs raw keys** — OAuth is cleaner (scoped, revocable) but adds complexity. Raw keys as MVP, OAuth as future enhancement.
