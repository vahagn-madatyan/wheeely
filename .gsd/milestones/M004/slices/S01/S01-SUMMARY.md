---
id: S01
parent: M004
milestone: M004
provides:
  - FastAPI app at apps/api/ with 5 endpoints wrapping existing screener engine
  - POST /api/screen/puts — async put screening with background task, returns run_id
  - POST /api/screen/calls — async call screening with background task, returns run_id
  - GET /api/screen/runs/{run_id} — poll task status and retrieve typed results
  - GET /api/positions — positions with wheel state classification
  - GET /api/account — account summary with buying power and capital at risk
  - Per-request Alpaca client factory (no env vars, no BrokerClient)
  - In-memory TaskStore with TTL cleanup for background task lifecycle
  - 14 Pydantic request/response schemas
requires: []
affects:
  - S05
  - S06
key_files:
  - apps/api/main.py
  - apps/api/schemas.py
  - apps/api/services/clients.py
  - apps/api/services/task_store.py
  - apps/api/routers/screen.py
  - apps/api/routers/positions.py
  - apps/api/requirements.txt
  - apps/api/tests/test_screen_endpoints.py
  - apps/api/tests/test_positions_account.py
  - apps/api/tests/test_task_store.py
  - apps/api/tests/test_client_factory.py
key_decisions:
  - none (slice used existing decisions D053, D055 — per-request client construction and async background tasks)
patterns_established:
  - API source lives under apps/api/ with its own requirements.txt, fully isolated from CLI
  - Per-request Alpaca client factory constructs TradingClient + StockHistoricalDataClient + OptionHistoricalDataClient from request-provided keys
  - Background task pattern via in-memory TaskStore — submit returns run_id, poll returns status/results/error
  - FastAPI app uses lifespan context manager for TaskStore initialization and TTL cleanup
  - Both CLI and API test suites run independently with no cross-contamination
observability_surfaces:
  - GET /api/screen/runs/{run_id} exposes task status (pending/running/completed/failed), results, and error messages
  - TaskStore status transitions logged via Python logging in screen.py and positions.py routers
  - Failed screening runs surface error string via TaskStore error field
drill_down_paths:
  - .gsd/milestones/M004/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M004/slices/S01/tasks/T02-SUMMARY.md
duration: 10m
verification_result: passed
completed_at: 2026-03-16
---

# S01: FastAPI wraps existing screener engine

**FastAPI app with 5 endpoints wraps `screen_puts()`, `screen_calls()`, `update_state()`, and `calculate_risk()` with per-request Alpaca client construction and async background task execution. 425 CLI tests + 31 API tests pass.**

## What Happened

The complete API source tree (15 Python files + requirements.txt) was checked out from the `gsd/M004/S01` feature branch into the working branch. The API lives entirely under `apps/api/` with zero modifications to any CLI file.

The FastAPI app (`apps/api/main.py`) defines two routers — `screen` and `positions` — mounted under `/api`. The screen router accepts PUT and CALL screening requests via POST, spawns background tasks using an in-memory `TaskStore`, and exposes a polling endpoint at `GET /api/screen/runs/{run_id}`. The positions router provides `GET /api/positions` (with wheel state classification via `update_state()`) and `GET /api/account` (with capital at risk via `calculate_risk()`).

Per-request Alpaca client construction (`apps/api/services/clients.py`) creates a fresh `TradingClient`, `StockHistoricalDataClient`, and `OptionHistoricalDataClient` tuple from request-provided API keys — no env vars, no `BrokerClient` wrapper. This directly implements decision D053 (per-request client construction for multi-tenant).

The `TaskStore` (`apps/api/services/task_store.py`) manages background task lifecycle with status transitions (PENDING → RUNNING → COMPLETED/FAILED), TTL-based cleanup via the FastAPI lifespan, and thread-safe in-memory storage. This implements decision D055 (async screening via background tasks).

14 Pydantic schemas (`apps/api/schemas.py`) define request/response contracts for all endpoints with full type safety.

Both test suites passed on first run with zero fixes needed — the API code was already working from the feature branch.

## Verification

| Check | Result |
|-------|--------|
| `python -m pytest tests/ -q` | ✅ 425 passed, 0 failures |
| `python -m pytest apps/api/tests/ -v` | ✅ 31 passed, 0 failures |
| `python -c "from apps.api.main import app; print(app.title)"` | ✅ "Wheeely Screening API" |
| Failure-path tests (`-k "invalid or error or 404 or 400 or 502"`) | ✅ 6 passed |

### Endpoint contracts verified:
- PUT screening submit → 202 with run_id
- CALL screening submit → 202 with run_id
- Poll completed run → typed results matching PutRecommendation/CallRecommendation schemas
- Unknown run_id → 404
- Invalid preset → 400
- Missing API keys → 422
- Alpaca API error → 502
- Status progression (pending → running → completed)
- Empty portfolio → empty list
- Positions with risk calculation

## Requirements Advanced

- WEB-11 — Async screening background task pattern fully implemented: submit → poll → results with in-memory TaskStore
- CLI-COMPAT-01 — 425 CLI tests pass unchanged; zero files outside apps/api/ modified

## Requirements Validated

- WEB-11 — 31 API tests prove: submit returns 202 with run_id, poll returns status transitions, completed runs include typed results, failed runs capture error messages
- CLI-COMPAT-01 — 425 CLI tests pass with zero modifications to any file outside apps/api/

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

None. Both tasks completed on first run with no fixes needed.

## Known Limitations

- TaskStore is in-memory — state is lost on server restart. Acceptable for S01; persistent storage comes with S02 (Supabase database).
- API keys are accepted in request bodies without encryption or auth. Acceptable for S01; S02 adds JWT auth and envelope encryption.
- No rate limiting on screening endpoints. S06 adds Redis-based rate limiting.
- CORS middleware is configured but permissive (allows all origins). S07 tightens for production deployment.

## Follow-ups

- none — all planned work completed; remaining gaps are covered by downstream slices S02-S07.

## Files Created/Modified

- `apps/api/__init__.py` — Package init
- `apps/api/main.py` — FastAPI app with lifespan, CORS middleware, two routers
- `apps/api/schemas.py` — 14 Pydantic request/response models
- `apps/api/requirements.txt` — API-specific dependencies (fastapi, uvicorn, httpx, pytest-asyncio, pydantic)
- `apps/api/services/__init__.py` — Services package init
- `apps/api/services/clients.py` — Per-request Alpaca client factory
- `apps/api/services/task_store.py` — In-memory background task lifecycle store with TTL cleanup
- `apps/api/routers/__init__.py` — Routers package init
- `apps/api/routers/screen.py` — PUT/CALL screening endpoints with background task submission
- `apps/api/routers/positions.py` — Positions and account endpoints with wheel state + risk
- `apps/api/tests/__init__.py` — Tests package init
- `apps/api/tests/conftest.py` — Test fixtures (TestClient, mock factories)
- `apps/api/tests/test_client_factory.py` — 3 client factory tests
- `apps/api/tests/test_positions_account.py` — 8 positions/account endpoint tests
- `apps/api/tests/test_screen_endpoints.py` — 11 screening endpoint tests
- `apps/api/tests/test_task_store.py` — 9 TaskStore unit tests

## Forward Intelligence

### What the next slice should know
- The API app is at `apps/api/main.py` and imports the existing screener engine directly — `from screener.put_screener import screen_puts`, etc. No adapter layer; direct function calls.
- Per-request client factory returns `(TradingClient, StockHistoricalDataClient, OptionHistoricalDataClient)` tuples. S02's key decryption utility must produce the same three-tuple shape.
- The TaskStore is intentionally in-memory. S02 should wire `screening_runs` and `screening_results` tables as the persistent backend without changing the polling contract (`GET /api/screen/runs/{run_id}`).
- API keys currently travel in request bodies. When S02 adds JWT auth, the screen/positions routers need to switch from request-body keys to decrypted-from-database keys. The client factory interface stays the same.

### What's fragile
- `apps/api/services/clients.py` constructs Alpaca SDK clients directly — if alpaca-py changes its constructor signature, this breaks. Pin alpaca-py version.
- The in-memory TaskStore has no persistence — a server restart during a screening run loses the results silently. Acceptable for dev/testing but must be replaced before production (S02/S07).

### Authoritative diagnostics
- `python -m pytest apps/api/tests/ -v` — covers all endpoint contracts, error paths, and schema validation. If this passes, the API layer is correct.
- `python -m pytest tests/ -q` — if this still shows 425 passed, CLI compatibility is intact.
- `python -c "from apps.api.main import app; print(app.title)"` — fastest check that the import chain works.

### What assumptions changed
- Plan estimated 16 files; actual count is 15 .py files + 1 .txt file. The plan counted requirements.txt in the "file" total. No missing functionality.
- No fixes were needed during T02 — the feature branch code was already clean. Total execution time was ~10 minutes vs the 40 minutes estimated.
