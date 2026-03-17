---
id: T02
parent: S01
milestone: M004
provides:
  - CLI-COMPAT-01 proven: 425 CLI tests pass with zero failures
  - WEB-11 proven: 31 API tests pass covering all endpoint contracts
  - Slice S01 fully verified and ready for downstream consumption by S02, S05, S06
key_files:
  - apps/api/tests/test_screen_endpoints.py
  - apps/api/tests/test_positions_account.py
  - apps/api/tests/test_task_store.py
  - apps/api/tests/test_client_factory.py
key_decisions: []
patterns_established:
  - Both test suites run independently with no cross-contamination — CLI tests in tests/, API tests in apps/api/tests/
observability_surfaces:
  - none (validation-only task — no new runtime signals)
duration: 5m
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T02: Run full test suites and validate S01 contracts

**Both CLI (425 tests) and API (31 tests) suites pass with zero failures, proving CLI-COMPAT-01 and WEB-11.**

## What Happened

Ran three verification passes with no failures and no fixes needed:

1. **CLI suite** (`python -m pytest tests/ -q`): 425 passed in 1.16s. Zero regressions from adding the `apps/api/` tree — no CLI files were modified.

2. **API suite** (`python -m pytest apps/api/tests/ -v`): 31 passed in 8.69s across 4 test files:
   - `test_task_store.py` — 9 tests (submit, get, update, cleanup lifecycle)
   - `test_client_factory.py` — 3 tests (return types, paper vs live, no env vars)
   - `test_screen_endpoints.py` — 11 tests (submit 202, poll completed, 404, status progression, failure capture, invalid preset 400, pending observation, schema validation)
   - `test_positions_account.py` — 8 tests (wheel state, empty portfolio, API error 502, account summary, risk calculation, missing keys 422)

3. **Failure-path subset** (`-k "invalid or error or 404 or 400 or 502"`): 6 selected, 6 passed — confirming all error status code contracts.

4. **Import smoke test**: `from apps.api.main import app` prints "Wheeely Screening API".

No diagnosis or fixes were required — all tests passed on first run.

## Verification

| Check | Result |
|-------|--------|
| `python -m pytest tests/ -q` | ✅ 425 passed, 0 failures |
| `python -m pytest apps/api/tests/ -v` | ✅ 31 passed, 0 failures |
| `python -c "from apps.api.main import app; print(app.title)"` | ✅ "Wheeely Screening API" |
| Failure-path tests (`-k "invalid or error or 404 or 400 or 502"`) | ✅ 6 passed |

### Key endpoint contracts verified:
- 202 submit (puts and calls)
- Completed poll with typed results
- 404 unknown run_id
- 400 invalid preset
- 422 missing keys
- 502 Alpaca API error

## Diagnostics

Re-verify at any time:
```bash
source .venv/bin/activate
python -m pytest tests/ -q                    # CLI-COMPAT-01
python -m pytest apps/api/tests/ -v           # WEB-11
```

## Deviations

None. All tests passed on first run — no diagnosis or fixes needed.

## Known Issues

None.

## Files Created/Modified

No source files modified — this was a validation-only task.
