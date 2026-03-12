# S09: Options Chain Validation — UAT

**Milestone:** M001
**Written:** 2026-03-11

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: All S09 functionality (filter functions, yield computation, pipeline integration, display, preset config) is verified through 58 unit/integration tests with mocked API calls. The filter functions are pure, the stage runner is tested with controlled mock responses, and the display output is captured and asserted. No live API calls are required to prove correctness.

## Preconditions

- Python 3.13 virtual environment activated (`source .venv/bin/activate`)
- Project installed in development mode (`uv pip install -e .`)
- All test dependencies available (pytest, numpy, pandas, rich, etc.)

## Smoke Test

Run `python -m pytest tests/test_options_chain.py -q` — expect 58 passed, 0 failed.

## Test Cases

### 1. OI Filter Correctness

1. Run `pytest tests/test_options_chain.py::TestFilterOptionsOI -v`
2. **Expected:** 7 tests pass — covers above-min, equal-to-min, below-min, None, zero, custom threshold, zero threshold

### 2. Spread Filter Correctness

1. Run `pytest tests/test_options_chain.py::TestFilterOptionsSpread -v`
2. **Expected:** 6 tests pass — covers below-max, equal-to-max, above-max, None, custom threshold, wide threshold

### 3. Yield Computation Math

1. Run `pytest tests/test_options_chain.py::TestComputePutPremiumYield -v`
2. **Expected:** 8 tests pass — basic yield ≈36.5%, low yield, high yield, zero/negative inputs return None, zero bid returns 0

### 4. ATM Put Selection

1. Run `pytest tests/test_options_chain.py::TestFindNearestAtmPut -v`
2. **Expected:** 5 tests pass — closest strike selected, exact match, empty list returns None

### 5. Stage 3 Integration

1. Run `pytest tests/test_options_chain.py::TestRunStage3Options -v`
2. **Expected:** 9 tests pass — liquid passes, low OI fails, wide spread fails, no contracts, no snapshot, yield gated, API error handled, ATM selection, no price

### 6. Preset Differentiation

1. Run `pytest tests/test_options_chain.py::TestPresetOptionsThresholds -v`
2. **Expected:** 5 tests pass — each preset has distinct OI/spread values, conservative strictest, aggressive loosest

### 7. Pipeline Backward Compatibility

1. Run `pytest tests/test_options_chain.py::TestPipelineOptionsIntegration -v`
2. **Expected:** 3 tests pass — Stage 3 runs with option_client, skipped without, only for Stage 2 passers

### 8. Display Output

1. Run `pytest tests/test_options_chain.py::TestDisplayYieldColumn -v`
2. **Expected:** 2 tests pass — Yield column present, shows percentage or N/A

### 9. Full Regression Suite

1. Run `pytest tests/ -q`
2. **Expected:** 302 passed, 0 failed (244 existing + 58 new)

## Edge Cases

### No option contracts available

1. Stock passes all prior filters but Alpaca returns no put contracts in DTE range
2. **Expected:** Both options_oi and options_spread filters fail; stock eliminated; no crash

### API exception during contract fetch

1. Alpaca trade_client.get_option_contracts raises an exception
2. **Expected:** Exception caught; stock fails options filters gracefully; pipeline continues

### Snapshot missing for contract

1. Contracts found, but option_client.get_option_snapshot returns empty dict
2. **Expected:** OI passes (from contract), spread fails (no bid/ask data); stock eliminated

### Zero-bid option

1. Nearest ATM put has bid=0, ask=0.05
2. **Expected:** midpoint=0.025 > 0; spread computed correctly; yield is 0.0%

## Failure Signals

- Any test in test_options_chain.py fails → regression in filter logic, config, or pipeline
- Existing tests in test_pipeline.py fail → backward incompatibility from option_client addition
- Run-screener crashes on import → missing import or circular dependency
- "Options" line missing from filter summary when option_client provided → display regression

## Requirements Proved By This UAT

- OPTS-01 — filter_options_oi tests prove OI filtering works with configurable thresholds
- OPTS-02 — filter_options_spread tests prove spread filtering works with configurable thresholds
- OPTS-03 — Preset tests prove all three presets have distinct, correctly-ordered OI and spread values
- OPTS-04 — Pipeline integration test proves Stage 3 only runs after prior stages pass
- OPTS-05 — Display test proves Yield column renders in results table; yield math tests prove computation

## Not Proven By This UAT

- Live Alpaca API contract/snapshot response shapes — tests use mocks; actual API integration verified by S10 or user acceptance
- Real-world screening results with options validation active — requires market hours and live credentials
- Performance impact of options chain API calls on pipeline throughput — not measured

## Notes for Tester

- All tests are fully mocked — no API keys or market data needed
- The `option_client` parameter to `run_pipeline()` defaults to None. Existing callers are unaffected unless they explicitly pass it.
- To test with live data: `run-screener --preset moderate` during market hours (requires ALPACA_API_KEY, ALPACA_SECRET_KEY, FINNHUB_API_KEY in .env)
