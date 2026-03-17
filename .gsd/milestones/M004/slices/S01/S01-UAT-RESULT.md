---
sliceId: S01
uatType: artifact-driven
verdict: PASS
date: 2026-03-17T02:44:30Z
---

# UAT Result — S01

## Checks

| Check | Result | Notes |
|-------|--------|-------|
| Smoke test — `from apps.api.main import app` prints title | PASS | Output: `Wheeely Screening API` |
| 15 .py files present under `apps/api/` | PASS | `find apps/api -name '*.py' | wc -l` → 15 |
| CLI compatibility — 425 tests pass unchanged | PASS | `python -m pytest tests/ -q` → 425 passed in 0.85s, 0 failures |
| Put screening submit returns 202 with run_id | PASS | `test_put_screen_submit_returns_202` PASSED |
| Put screening poll returns completed results | PASS | `test_put_screen_poll_returns_completed` PASSED |
| Call screening submit returns 202 | PASS | `test_call_screen_submit_returns_202` PASSED |
| Call screening poll returns completed results | PASS | `test_call_screen_poll_returns_completed` PASSED |
| Positions endpoint returns wheel state | PASS | `test_positions_returns_wheel_state` PASSED |
| Account endpoint returns summary with risk | PASS | `test_account_with_positions_calculates_risk` PASSED |
| TaskStore lifecycle — 9 tests | PASS | All 9 `test_task_store.py` tests passed |
| Client factory — 3 tests | PASS | All 3 `test_client_factory.py` tests passed |
| Edge: Unknown run_id returns 404 | PASS | `test_unknown_run_id_returns_404` PASSED |
| Edge: Invalid preset returns 400 | PASS | `test_invalid_preset_returns_400` PASSED |
| Edge: Missing API keys returns 422 | PASS | `test_positions_missing_keys_returns_422` PASSED |
| Edge: Alpaca API error surfaces as 502 | PASS | `test_positions_api_error_returns_502` PASSED |
| Edge: Failed screening captures error | PASS | `test_failed_screen_captures_error` PASSED |
| Edge: Empty portfolio | PASS | `test_positions_empty` PASSED |

## Overall Verdict

PASS — All 17 checks passed. 425 CLI tests + 31 API tests green with zero failures. Smoke test, all endpoint contracts, TaskStore lifecycle, client factory, and all 6 edge cases verified.

## Notes

- CLI suite ran in 0.85s, API suite in 8.61s. Both produced only a single deprecation warning from `websockets.legacy` (unrelated to this slice).
- No test modifications or retries were needed — all checks passed on first run.
- Requirements WEB-11 (async background task pattern) and CLI-COMPAT-01 (425 CLI tests unchanged) are fully proven.
