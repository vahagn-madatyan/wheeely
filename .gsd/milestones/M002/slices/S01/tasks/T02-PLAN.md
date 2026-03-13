---
estimated_steps: 5
estimated_files: 2
---

# T02: Split pipeline into two passes with top_n sort/cap and tests

**Slice:** S01 — Monthly Perf + Pipeline Cap
**Milestone:** M002

## Description

Refactor `run_pipeline()` to split the single per-symbol loop into two passes, wire `compute_monthly_performance` into the indicator step, add `top_n: int | None = None` parameter, and implement sort/cap logic between passes. This is the structural heart of the slice.

Pass 1 (cheap — all symbols): create ScreenedStock, compute indicators + perf_1m + HV, run Stage 1 filters. Pass 2 (expensive — capped survivors only): run Stage 1b (earnings), Stage 2 (Finnhub fundamentals), Stage 3 (options chain). Between passes: sort Stage 1 survivors ascending by perf_1m (None last via `float('inf')` sentinel), take top N if `top_n` is set.

When `top_n=None`, no cap is applied and behavior is identical to current — all 345 existing tests must pass without modification.

## Steps

1. Add `top_n: int | None = None` parameter to `run_pipeline()` signature and docstring.
2. Import `compute_monthly_performance` from `screener.market_data` at the top of `pipeline.py`.
3. Refactor the loop body in `run_pipeline()`:
   - **Pass 1:** Loop over all symbols. For each: create ScreenedStock, compute indicators, compute HV/HV percentile, compute `perf_1m` via `compute_monthly_performance(bars[sym])`, run Stage 1 filters. Append to `stocks` list. Collect passing stocks in a `stage1_survivors` list.
   - **Sort/cap:** Sort `stage1_survivors` by ascending `perf_1m` using key `lambda s: s.perf_1m if s.perf_1m is not None else float('inf')`. If `top_n` is set and `len(stage1_survivors) > top_n`, slice to `stage1_survivors[:top_n]`. Log the cap: `"Top-N cap: %d of %d Stage 1 survivors selected"`.
   - **Pass 2:** Loop over `stage1_survivors` (now capped). For each: run Stage 1b earnings, Stage 2 fundamentals, Stage 3 options. Progress totals use `len(stage1_survivors)` (capped count).
4. Write `TestTopNPipelineCap` test class in `tests/test_pipeline.py` with tests:
   - `test_top_n_caps_stage2_calls` — 5 Stage 1 survivors, top_n=2 → only 2 get Finnhub calls
   - `test_top_n_none_processes_all` — top_n=None → all survivors get Finnhub calls (backward compat)
   - `test_sort_ascending_perf` — survivors sorted by ascending perf_1m before cap
   - `test_none_perf_sorts_last` — stocks with perf_1m=None sort after stocks with real values
   - `test_perf_1m_populated_on_stocks` — stocks with bar data have perf_1m set, stocks without have None
   - `test_all_stocks_still_returned` — both passing and eliminated stocks in result (no silent drops)
5. Run full test suite: all existing 345 tests + new tests pass.

## Must-Haves

- [ ] `run_pipeline(top_n=N)` only runs Stage 1b/2/3 for top N survivors
- [ ] `run_pipeline(top_n=None)` produces identical results to before (backward compat)
- [ ] Stage 1 survivors sorted ascending by perf_1m before cap
- [ ] Stocks with `perf_1m=None` sort to end (not dropped)
- [ ] `perf_1m` populated on ScreenedStock objects that have bar data
- [ ] Progress callback totals reflect capped count in Pass 2
- [ ] All 345 existing tests pass unchanged
- [ ] 6 new pipeline tests pass

## Verification

- `pytest tests/test_pipeline.py::TestTopNPipelineCap -v` — 6 tests pass
- `pytest tests/ -v` — all 345+ existing tests pass, zero regressions

## Observability Impact

- Signals added/changed: New log line `"Top-N cap: %d of %d Stage 1 survivors selected"` when top_n is active
- How a future agent inspects this: check `stock.perf_1m` on returned ScreenedStock objects; log output shows cap ratio
- Failure state exposed: stocks with no bar data still get `bar_data` FilterResult(passed=False); stocks with <22 bars get perf_1m=None but still pass Stage 1 if other filters pass

## Inputs

- `screener/market_data.py` — `compute_monthly_performance()` from T01
- `models/screened_stock.py` — `perf_1m` field from T01
- `screener/pipeline.py` — current single-loop `run_pipeline()` to refactor
- `tests/test_pipeline.py` — existing `TestRunPipeline._setup_mocks()` pattern to follow

## Expected Output

- `screener/pipeline.py` — `run_pipeline()` refactored to two-pass with `top_n` parameter
- `tests/test_pipeline.py` — new `TestTopNPipelineCap` class with 6 tests
