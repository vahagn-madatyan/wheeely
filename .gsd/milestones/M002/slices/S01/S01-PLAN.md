# S01: Monthly Perf + Pipeline Cap

**Goal:** `run_pipeline(top_n=20)` returns results from only the 20 worst-performing Stage 1 survivors, with `perf_1m` populated on all ScreenedStock objects that have bar data.
**Demo:** Run pipeline tests showing: (a) perf_1m computed correctly from bars, (b) Stage 1 survivors sorted ascending by perf_1m with None last, (c) top_n caps survivors before expensive stages, (d) top_n=None preserves current behavior.

## Must-Haves

- `compute_monthly_performance(bars_df)` returns `(close[-1] / close[-22] - 1) * 100` or None if <22 bars
- `ScreenedStock.perf_1m: Optional[float]` populated during indicator step
- `run_pipeline(top_n=N)` sorts Stage 1 survivors ascending by perf_1m (None last), takes top N
- `run_pipeline(top_n=None)` produces identical results to current behavior (all 345 tests pass)
- Pipeline splits into Pass 1 (indicators + Stage 1) → sort/cap → Pass 2 (Stage 1b/2/3)
- Progress callback totals reflect capped count in Pass 2

## Proof Level

- This slice proves: contract
- Real runtime required: no (all verified via mocked pipeline tests)
- Human/UAT required: no (deferred to S02 terminal slice)

## Verification

- `pytest tests/test_market_data.py::TestComputeMonthlyPerformance -v` — 5+ pure math tests pass
- `pytest tests/test_pipeline.py::TestTopNPipelineCap -v` — 6+ sort/cap/backward-compat pipeline tests pass
- `pytest tests/ -v` — all 345+ existing tests still pass (no regressions)

## Observability / Diagnostics

- Runtime signals: existing `logger.info("Pipeline complete: ...")` updated to include capped count when top_n active
- Inspection surfaces: `perf_1m` field on ScreenedStock objects returned by pipeline
- Failure visibility: `compute_monthly_performance` returns None (not raise) for insufficient data; None stocks logged
- Redaction constraints: none (no secrets involved)

## Integration Closure

- Upstream surfaces consumed: `fetch_daily_bars()` bar DataFrames (existing), `run_stage_1_filters()` (existing)
- New wiring introduced in this slice: `compute_monthly_performance()` called in pipeline loop; two-pass loop structure; `top_n` parameter on `run_pipeline()`
- What remains before the milestone is truly usable end-to-end: S02 adds `--top-n` CLI flag and "Perf 1M" display column

## Tasks

- [x] **T01: Add compute_monthly_performance and perf_1m field with tests** `est:30m`
  - Why: Establishes the perf computation function and data model field that the pipeline refactor (T02) will wire in. Covers TOPN-02 (computation) and TOPN-04 (field).
  - Files: `screener/market_data.py`, `models/screened_stock.py`, `tests/test_market_data.py`
  - Do: Add `compute_monthly_performance(bars_df)` to market_data.py following `compute_indicators` pattern. Add `perf_1m: Optional[float] = None` to ScreenedStock after `hv_percentile`. Write tests covering: exact math, insufficient data returns None, single-bar edge, 22-bar boundary.
  - Verify: `pytest tests/test_market_data.py::TestComputeMonthlyPerformance -v` — all pass. `pytest tests/ -v` — 345+ existing tests still pass.
  - Done when: Function returns correct percentage for valid data, None for <22 bars, and field exists on ScreenedStock.

- [x] **T02: Split pipeline into two passes with top_n sort/cap and tests** `est:45m`
  - Why: The core structural change — splits the single per-symbol loop into Pass 1 (cheap) and Pass 2 (expensive), wires perf computation, and adds sort/cap logic. Covers TOPN-03 (sort/cap), supports TOPN-06 (backward compat).
  - Files: `screener/pipeline.py`, `tests/test_pipeline.py`
  - Do: Wire `compute_monthly_performance` into Pass 1 indicator step. Refactor `run_pipeline` loop: Pass 1 builds ScreenedStock + indicators + Stage 1 filters for all symbols; collect Stage 1 survivors; sort ascending by perf_1m (use `float('inf')` sentinel for None); if top_n set, take first N; Pass 2 runs Stage 1b/2/3 only for capped survivors. Add `top_n: int | None = None` parameter. Adjust progress totals for Pass 2. Add log line for cap count. Write tests: sort order, cap applied, None-perf sorts last, top_n=None returns all, perf_1m populated on stocks, progress callback totals.
  - Verify: `pytest tests/test_pipeline.py::TestTopNPipelineCap -v` — all pass. `pytest tests/ -v` — all 345+ existing tests pass (no regressions).
  - Done when: Pipeline two-pass refactor works, top_n caps expensive stage processing, backward compat preserved, all tests green.

## Files Likely Touched

- `screener/market_data.py`
- `models/screened_stock.py`
- `screener/pipeline.py`
- `tests/test_market_data.py`
- `tests/test_pipeline.py`
