---
id: M003
provides:
  - "screener/put_screener.py — screen_puts() with multi-symbol pagination, buying power pre-filter, OI/spread/delta filters, one-per-underlying diversification, annualized return ranking"
  - "PutRecommendation dataclass with compute_put_annualized_return() using premium/strike formula (D046)"
  - "run-put-screener CLI with --buying-power, --preset, --config flags"
  - "run-strategy modernized: uses screen_puts() for put leg, screen_calls() for call leg"
  - "Legacy code removed: core/strategy.py, core/execution.py, models/contract.py, obsolete config/params.py constants"
  - "BrokerClient cleaned to 3 methods: get_positions(), market_sell(), liquidate_all_positions()"
key_decisions:
  - "D045: Put screener module mirrors call_screener.py with multi-symbol support and buying power pre-filter"
  - "D046: Put annualized return uses premium/strike (not premium/cost_basis) — capital at risk for puts is strike×100"
  - "D047: Legacy code removal scope — core/strategy.py, core/execution.py, models/contract.py, 6 obsolete constants"
  - "D048: BrokerClient.get_options_contracts() removed — screeners use trade_client directly"
patterns_established:
  - "PutRecommendation mirrors CallRecommendation — structural symmetry between put and call screeners"
  - "screen_puts() extends call screener pattern with pagination, buying power filter, one-per-underlying"
  - "run-put-screener CLI mirrors run-call-screener with variadic symbols + --buying-power"
observability_surfaces:
  - "run-put-screener CLI with Rich results table"
  - "run-strategy logs each put sold with contract details and remaining buying power"
  - "425 tests covering all screening, CLI, and strategy integration paths"
duration: "1 session (2026-03-15)"
verification_result: passed
completed_at: 2026-03-15
---

# M003: Modern Put Screener + Legacy Cleanup

**Replaced legacy sell_puts() with modern screen_puts() mirroring the call screener, added run-put-screener CLI, removed all legacy code — 425 tests, zero failures, clean codebase**

## What Happened

Four-slice milestone that modernized the put-selling leg to match the call screener's quality and removed all legacy code.

**S01 (Put Screener Module):** Built `screener/put_screener.py` (~390 lines) as a structural mirror of `call_screener.py` extended for multi-symbol use. `PutRecommendation` dataclass, `compute_put_annualized_return()` with `premium/strike` formula (D046), `screen_puts()` with buying power pre-filter, paginated contract fetch, OI/spread/delta filters, one-per-underlying selection, and `render_put_results_table()` with 10 columns. 50 tests.

**S02 (CLI + Strategy Integration):** Created `run-put-screener` Typer CLI with variadic symbols and `--buying-power` flag. Replaced `sell_puts()` in `run_strategy.py` with `screen_puts()` + order execution loop with buying power tracking. Removed all `core.execution` imports. Fixed 3 call screener strategy tests that patched the removed `sell_puts`.

**S03 (Legacy Removal + Docs):** Deleted `core/strategy.py`, `core/execution.py`, `models/contract.py`. Cleaned `config/params.py` to 3 constants. Cleaned `core/broker_client.py` to 3 methods. Updated `CLAUDE.md` with accurate architecture.

**S04 (Verification):** Confirmed 425 tests pass, zero dead imports (AST checked), zero obsolete constants, both screening paths tested in strategy integration.

## Forward Intelligence

### What the next milestone should know
- The wheel strategy now uses two symmetric screener modules: `screen_puts()` for the sell-put leg and `screen_calls()` for the sell-call leg. Both use preset-configurable thresholds.
- `BrokerClient` is now a thin wrapper with 3 methods. Screeners use SDK clients (`trade_client`, `option_client`, `stock_client`) directly.
- 425 tests run in under 1 second. The test suite is fast and comprehensive.

### What's fragile
- `screen_puts()` needs `stock_client` for buying power pre-filter — this is an optional parameter (None skips the filter), but callers should pass it for proper operation.
- The `logging/` package shadow (D001) still requires `import logging as stdlib_logging` pattern.

### Authoritative diagnostics
- `python -m pytest tests/ -q` — 425 tests, full regression suite
- `python -m pytest tests/test_put_screener.py -v` — 53 tests covering all put screener functionality
- `run-put-screener AAPL MSFT --buying-power 50000` against live APIs — the ultimate integration test
