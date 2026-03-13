---
id: T02
parent: S01
milestone: M002
provides:
  - run_pipeline(top_n=N) two-pass architecture with sort/cap
  - perf_1m wired into pipeline via compute_monthly_performance
  - stage1_survivors sorted ascending by perf_1m before expensive stages
key_files:
  - screener/pipeline.py
  - tests/test_pipeline.py
key_decisions:
  - Sort always runs (even top_n=None) so stage1_survivors order is deterministic; no behavior change since all survivors still proceed
patterns_established:
  - Two-pass pipeline pattern: Pass 1 (cheap indicators + Stage 1), sort/cap, Pass 2 (expensive Finnhub + options)
  - Mock compute_monthly_performance via @patch("screener.pipeline.compute_monthly_performance") in tests that need controlled perf_1m values
observability_surfaces:
  - Log line "Top-N cap: %d of %d Stage 1 survivors selected" when top_n is active
  - stock.perf_1m field on ScreenedStock objects returned by pipeline
duration: ~15min
verification_result: passed
completed_at: 2026-03-11
blocker_discovered: false
---

# T02: Split pipeline into two passes with top_n sort/cap and tests

**Refactored `run_pipeline()` to two-pass architecture with `top_n` parameter: Pass 1 runs cheap indicators + Stage 1 filters on all symbols, then sorts survivors ascending by `perf_1m` and caps to top N before Pass 2 runs expensive Finnhub/options stages.**

## What Happened

1. Added `compute_monthly_performance` import to `pipeline.py`.
2. Added `top_n: int | None = None` parameter to `run_pipeline()` with full docstring.
3. Refactored the single per-symbol loop into two passes:
   - **Pass 1**: Creates ScreenedStock, computes indicators + HV + perf_1m, runs Stage 1 filters. Collects survivors in `stage1_survivors` list.
   - **Sort/cap**: Sorts `stage1_survivors` ascending by `perf_1m` (None last via `float('inf')` sentinel). If `top_n` set and survivors exceed it, slices to `stage1_survivors[:top_n]` with a log message.
   - **Pass 2**: Iterates capped survivors only for Stage 1b (earnings), Stage 2 (Finnhub fundamentals), Stage 3 (options chain). Progress totals use `len(stage1_survivors)` (capped count).
4. Wrote `TestTopNPipelineCap` test class with 6 tests covering cap behavior, backward compat, sort order, None handling, perf_1m population, and no-drop guarantee.

## Verification

- `pytest tests/test_pipeline.py::TestTopNPipelineCap -v` — 6/6 passed
- `pytest tests/test_market_data.py::TestComputeMonthlyPerformance -v` — 6/6 passed (T01 tests)
- `pytest tests/ -v` — 357 passed, 0 failed (345 existing + 6 T01 + 6 T02)
- All existing tests pass unchanged (backward compat confirmed with top_n=None default)

## Diagnostics

- Check `stock.perf_1m` on any ScreenedStock returned by `run_pipeline()` — set for stocks with bar data, None for stocks without.
- When `top_n` is active, log output includes `"Top-N cap: %d of %d Stage 1 survivors selected"` showing cap ratio.
- Stocks with no bar data still get `bar_data` FilterResult(passed=False); stocks with <22 bars get perf_1m=None but still pass Stage 1 if other filters pass.

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `screener/pipeline.py` — Refactored `run_pipeline()` to two-pass architecture with `top_n` parameter, added `compute_monthly_performance` import and wiring
- `tests/test_pipeline.py` — Added `TestTopNPipelineCap` class with 6 tests
