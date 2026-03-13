---
estimated_steps: 4
estimated_files: 3
---

# T01: Add compute_monthly_performance and perf_1m field with tests

**Slice:** S01 — Monthly Perf + Pipeline Cap
**Milestone:** M002

## Description

Add the `compute_monthly_performance(bars_df)` pure function to `screener/market_data.py` and the `perf_1m: Optional[float]` field to `ScreenedStock`. Write comprehensive tests for the computation math. This task is pure addition — no refactoring of existing code — so it carries zero regression risk.

The function computes `(close[-1] / close[-22] - 1) * 100`, returning a percentage (e.g. -5.2 for a 5.2% decline). Returns None when fewer than 22 close prices are available.

## Steps

1. Add `compute_monthly_performance(bars_df: pd.DataFrame) -> float | None` to `screener/market_data.py` after the existing `compute_indicators` function. Follow the same docstring and type annotation conventions as `compute_indicators`. Use `close.iloc[-1] / close.iloc[-22] - 1) * 100`. Return None if `len(bars_df) < 22`.
2. Add `perf_1m: Optional[float] = None` to `models/screened_stock.py` after the `hv_percentile` field, in the "Technical indicators" section.
3. Add `TestComputeMonthlyPerformance` test class to `tests/test_market_data.py` with tests:
   - `test_exact_22_bars_computes_correctly` — 22 bars with known close values, assert exact percentage
   - `test_250_bars_uses_last_22` — 250 bars, verify computation uses iloc[-1] and iloc[-22]
   - `test_insufficient_data_returns_none` — 21 bars returns None
   - `test_negative_return` — declining price gives negative percentage
   - `test_positive_return` — rising price gives positive percentage
   - `test_flat_return_is_zero` — same close price gives 0.0
4. Run full test suite to confirm no regressions.

## Must-Haves

- [ ] `compute_monthly_performance` returns correct percentage for ≥22 bars
- [ ] `compute_monthly_performance` returns None for <22 bars
- [ ] `ScreenedStock.perf_1m` field exists and defaults to None via `from_symbol()`
- [ ] All 6 new tests pass
- [ ] All 345 existing tests pass unchanged

## Verification

- `pytest tests/test_market_data.py::TestComputeMonthlyPerformance -v` — 6 tests pass
- `pytest tests/ -v` — 345+ tests pass, zero failures

## Observability Impact

- Signals added/changed: None (pure function, no logging needed)
- How a future agent inspects this: call `compute_monthly_performance(df)` directly; check `stock.perf_1m` field
- Failure state exposed: None return value for insufficient data (not raise)

## Inputs

- `screener/market_data.py` — existing indicator computation pattern to follow
- `models/screened_stock.py` — existing Optional[float] field pattern (hv_30, hv_percentile)
- `tests/test_market_data.py` — existing `_make_bars` helper and test class structure

## Expected Output

- `screener/market_data.py` — new `compute_monthly_performance()` function
- `models/screened_stock.py` — new `perf_1m` field on ScreenedStock
- `tests/test_market_data.py` — new `TestComputeMonthlyPerformance` class with 6 tests
