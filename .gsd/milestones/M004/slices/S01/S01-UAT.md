# S01: FastAPI wraps existing screener engine — UAT

**Milestone:** M004
**Written:** 2026-03-16

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S01 is an API-only slice with no UI or live deployment. All contracts are verified through automated test suites (425 CLI + 31 API tests) running against FastAPI's TestClient with mocked screener backends. No live Alpaca connection is needed at this stage.

## Preconditions

- Python 3.13 virtualenv active: `source .venv/bin/activate`
- API dependencies installed: `uv pip install -r apps/api/requirements.txt`
- All 15 .py files present under `apps/api/`

## Smoke Test

```bash
python -c "from apps.api.main import app; print(app.title)"
# Expected: "Wheeely Screening API"
```

## Test Cases

### 1. CLI compatibility — 425 tests pass unchanged

1. Run `python -m pytest tests/ -q`
2. **Expected:** `425 passed` with 0 failures, 0 errors

### 2. Put screening submit returns 202 with run_id

1. Run `python -m pytest apps/api/tests/test_screen_endpoints.py::test_put_screen_submit_returns_202 -v`
2. **Expected:** POST `/api/screen/puts` with valid body returns HTTP 202 with `{"run_id": "<uuid>", "status": "pending"}`

### 3. Put screening poll returns completed results

1. Run `python -m pytest apps/api/tests/test_screen_endpoints.py::test_put_screen_poll_returns_completed -v`
2. **Expected:** After background task completes, GET `/api/screen/runs/{run_id}` returns `{"status": "completed", "run_type": "put", "results": [...]}` with typed put recommendation fields (symbol, strike, expiration, bid, ask, delta, oi, spread_pct, annualized_return, dte)

### 4. Call screening submit and poll

1. Run `python -m pytest apps/api/tests/test_screen_endpoints.py::test_call_screen_submit_returns_202 -v`
2. Run `python -m pytest apps/api/tests/test_screen_endpoints.py::test_call_screen_poll_returns_completed -v`
3. **Expected:** POST `/api/screen/calls` returns 202; poll returns completed with call recommendation fields

### 5. Positions endpoint returns wheel state

1. Run `python -m pytest apps/api/tests/test_positions_account.py::test_positions_returns_wheel_state -v`
2. **Expected:** GET `/api/positions` returns position list with `wheel_state` field set to `short_put`, `long_shares`, or `short_call`

### 6. Account endpoint returns summary with risk

1. Run `python -m pytest apps/api/tests/test_positions_account.py::test_account_with_positions_calculates_risk -v`
2. **Expected:** GET `/api/account` returns `buying_power`, `portfolio_value`, `cash`, `capital_at_risk` fields

### 7. TaskStore lifecycle — submit, update, cleanup

1. Run `python -m pytest apps/api/tests/test_task_store.py -v`
2. **Expected:** All 9 tests pass — submit creates pending entry, update transitions status, cleanup removes old entries while preserving recent ones

### 8. Client factory constructs per-request clients

1. Run `python -m pytest apps/api/tests/test_client_factory.py -v`
2. **Expected:** All 3 tests pass — returns correct tuple type, paper vs live URLs differ, no env vars leaked

## Edge Cases

### Unknown run_id returns 404

1. Run `python -m pytest apps/api/tests/test_screen_endpoints.py::test_unknown_run_id_returns_404 -v`
2. **Expected:** GET `/api/screen/runs/nonexistent-uuid` returns HTTP 404

### Invalid preset returns 400

1. Run `python -m pytest apps/api/tests/test_screen_endpoints.py::test_invalid_preset_returns_400 -v`
2. **Expected:** POST `/api/screen/puts` with `preset: "nonexistent"` returns HTTP 400 with error detail

### Missing API keys returns 422

1. Run `python -m pytest apps/api/tests/test_positions_account.py::test_positions_missing_keys_returns_422 -v`
2. **Expected:** GET `/api/positions` without required API key query params returns HTTP 422

### Alpaca API error surfaces as 502

1. Run `python -m pytest apps/api/tests/test_positions_account.py::test_positions_api_error_returns_502 -v`
2. **Expected:** When Alpaca SDK raises an exception, endpoint returns HTTP 502 with error detail

### Failed screening captures error

1. Run `python -m pytest apps/api/tests/test_screen_endpoints.py::test_failed_screen_captures_error -v`
2. **Expected:** When screener throws, poll returns `{"status": "failed", "error": "<message>"}`

### Empty portfolio

1. Run `python -m pytest apps/api/tests/test_positions_account.py::test_positions_empty -v`
2. **Expected:** GET `/api/positions` with no positions returns empty list `[]`

## Failure Signals

- `python -m pytest tests/ -q` shows fewer than 425 passed → CLI code was modified
- `python -m pytest apps/api/tests/ -v` shows failures → API contracts broken
- `from apps.api.main import app` raises `ModuleNotFoundError` → missing dependencies or files
- Any test importing from `screener/` fails → import path pollution between CLI and API

## Requirements Proved By This UAT

- WEB-11 — Async background task pattern: submit returns run_id, poll returns status/results, failed runs capture errors
- CLI-COMPAT-01 — 425 CLI tests pass unchanged with zero files outside apps/api/ modified

## Not Proven By This UAT

- WEB-05, WEB-06 — Browser-based screener UI (S05)
- WEB-07, WEB-08 — Browser-based positions/account dashboard (S06)
- WEB-01, WEB-10 — Auth and multi-tenant isolation (S02)
- WEB-02, WEB-03 — Encrypted key storage (S02)
- WEB-09 — Rate limiting (S06)
- WEB-12 — Render deployment (S07)
- Live Alpaca integration — all tests use mocked clients; real API calls tested by downstream slices

## Notes for Tester

- All tests use FastAPI's `TestClient` with mocked screener functions — no live API keys needed.
- The full suite runs in under 10 seconds: `python -m pytest tests/ -q && python -m pytest apps/api/tests/ -v`
- If running tests individually, ensure the virtualenv is active and requirements are installed.
- The `apps/api/` directory is fully self-contained — deleting it would restore the project to pre-S01 state with no side effects.
