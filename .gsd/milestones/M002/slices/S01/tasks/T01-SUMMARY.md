---
id: T01
parent: S01
milestone: M002
provides:
  - compute_monthly_performance() pure function in screener/market_data.py
  - perf_1m field on ScreenedStock dataclass
  - 6 tests covering monthly performance computation math
key_files:
  - screener/market_data.py
  - models/screened_stock.py
  - tests/test_market_data.py
key_decisions: []
patterns_established:
  - compute_monthly_performance follows same docstring/typing conventions as compute_indicators
observability_surfaces:
  - compute_monthly_performance returns None (not raise) for insufficient data
duration: 10m
verification_result: passed
completed_at: 2026-03-11
blocker_discovered: false
---

# T01: Add compute_monthly_performance and perf_1m field with tests

**Added `compute_monthly_performance(bars_df)` pure function and `perf_1m` field to ScreenedStock with 6 passing tests.**

## What Happened

Added `compute_monthly_performance(bars_df: pd.DataFrame) -> float | None` to `screener/market_data.py` after `compute_indicators`. The function computes `(close.iloc[-1] / close.iloc[-22] - 1) * 100`, returning a percentage. Returns None when fewer than 22 close prices are available.

Added `perf_1m: Optional[float] = None` to `ScreenedStock` in the Technical indicators section after `hv_percentile`.

Wrote `TestComputeMonthlyPerformance` class with 6 tests: exact 22-bar math, 250-bar uses-last-22, insufficient data returns None, negative return, positive return, and flat return is zero.

## Verification

- `pytest tests/test_market_data.py::TestComputeMonthlyPerformance -v` — 6/6 passed
- `pytest tests/ -v` — 351 passed, 0 failures (up from 345 baseline — 6 new tests added)
- `ScreenedStock.from_symbol('AAPL').perf_1m` returns None (default confirmed)

### Slice-level verification status (intermediate task)
- ✅ `pytest tests/test_market_data.py::TestComputeMonthlyPerformance -v` — 6 tests pass
- ⬜ `pytest tests/test_pipeline.py::TestTopNPipelineCap -v` — not yet created (T02)
- ✅ `pytest tests/ -v` — 351 passed, no regressions

## Diagnostics

Call `compute_monthly_performance(df)` directly with any DataFrame containing a `close` column. Returns None for insufficient data (no exceptions). Check `stock.perf_1m` field on any ScreenedStock instance.

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `screener/market_data.py` — added `compute_monthly_performance()` function
- `models/screened_stock.py` — added `perf_1m: Optional[float] = None` field
- `tests/test_market_data.py` — added `TestComputeMonthlyPerformance` class with 6 tests
