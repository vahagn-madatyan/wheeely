---
id: M002
provides:
  - "--top-n CLI flag caps expensive per-symbol API calls to N worst monthly performers"
  - "compute_monthly_performance() from existing bar data"
  - "perf_1m field on ScreenedStock"
  - "Perf 1M column in Rich results table"
  - "fmt_signed_pct() display helper"
key_decisions:
  - "D041: Fixed 22 trading day lookback for monthly performance"
  - "D042: top_n is CLI-only, not configurable per preset"
  - "D043: Sort/cap placed after Stage 1 but before Stage 1b (maximizes API savings)"
  - "D044: None perf_1m sorts last (deprioritized, not dropped)"
patterns_established:
  - "fmt_signed_pct() for signed percentage display (+3.1%, -5.2%, N/A)"
  - "Sort key with None→float('inf') for None-last ordering"
observability_surfaces:
  - "Pipeline logs top_n cap application with count before/after"
requirement_outcomes:
  - id: TOPN-01
    from_status: active
    to_status: validated
    proof: "3 CLI tests (help text, value forwarding, None default) in test_cli_screener.py; --top-n Typer option with min=1 forwarded to run_pipeline(top_n=)"
  - id: TOPN-02
    from_status: active
    to_status: validated
    proof: "4 compute_monthly_performance tests in test_pipeline.py::TestTopNPipelineCap; uses last 22 bars of existing 250-day data"
  - id: TOPN-03
    from_status: active
    to_status: validated
    proof: "4 sort/cap tests in test_pipeline.py::TestTopNPipelineCap; ascending sort with None-last ordering, cap applied before Stage 1b"
  - id: TOPN-04
    from_status: active
    to_status: validated
    proof: "ScreenedStock.perf_1m Optional[float] field; populated by compute_monthly_performance() during indicator step; integration tests confirm"
  - id: TOPN-05
    from_status: active
    to_status: validated
    proof: "4 display tests (header present, positive +sign, negative value, None→N/A) in test_display.py; fmt_signed_pct() helper"
  - id: TOPN-06
    from_status: active
    to_status: validated
    proof: "test_no_top_n_defaults_to_none in test_cli_screener.py; top_n=None in pipeline means no cap; backward-compat tests in test_pipeline.py"
duration: short
verification_result: passed
completed_at: 2026-03-12
---

# M002: Top-N Performance Cap

**Added `--top-n` CLI flag to cap screener processing to the N worst-performing Stage 1 survivors, reducing runtime from hours to minutes while prioritizing the best put-selling candidates.**

## What Happened

Two-slice milestone. S01 added the computation and pipeline mechanics: `compute_monthly_performance()` derives 1-month return from existing 250-day bar data (last 22 trading days), populates `perf_1m` on `ScreenedStock`, and inserts a sort/cap step in `run_pipeline()` between Stage 1 (cheap Alpaca filters) and Stage 1b (expensive Finnhub earnings calls). Stocks sort ascending by `perf_1m` — worst performers first (best put-selling candidates) — with `None` values sorted to the end rather than dropped. When `top_n` is set, only the top N survivors proceed to the expensive per-symbol API stages.

S02 wired the CLI and display: added `--top-n` Typer option to `run-screener` (Optional[int], min=1), forwarded to `run_pipeline(top_n=)`, and added a "Perf 1M" column to the Rich results table using `fmt_signed_pct()` for signed percentage rendering (+3.1%, -5.2%, N/A).

The milestone delivered all six TOPN requirements with 11 new tests (368 total, zero failures).

## Cross-Slice Verification

| Success Criterion | Evidence |
|---|---|
| `run-screener --top-n 20` processes only 20 stocks through expensive stages | `pipeline.py:1301` — `stage1_survivors = stage1_survivors[:top_n]` applied before Stage 1b/2/3; 6 pipeline cap tests pass |
| `run-screener` without `--top-n` processes all stocks (backward compatible) | `top_n=None` → no cap; `test_no_top_n_defaults_to_none` + `test_top_n_none_processes_all` confirm |
| "Perf 1M" column with percentage values in results table | `display.py:198` adds column; `test_perf_1m_column_header_present` + 3 value rendering tests pass |
| Sorted by ascending monthly performance before cap | `pipeline.py:1299` — `key=lambda s: s.perf_1m if s.perf_1m is not None else float('inf')`; `test_sort_ascending_perf` confirms |
| Insufficient bar data stocks sorted to end | None → `float('inf')` in sort key; `test_none_perf_sorts_last` confirms |
| All 368 tests pass | `pytest tests/ -v` — 368 passed, 0 failed |

## Requirement Changes

- TOPN-01: active → validated — 3 CLI tests prove flag parsing, forwarding, and default behavior
- TOPN-02: active → validated — 4 compute_monthly_performance tests; uses last 22 bars of existing data
- TOPN-03: active → validated — 4 sort/cap tests; ascending sort with None-last, cap before Stage 1b
- TOPN-04: active → validated — ScreenedStock.perf_1m field populated during indicator computation
- TOPN-05: active → validated — 4 display tests for Perf 1M column + fmt_signed_pct helper
- TOPN-06: active → validated — test_no_top_n_defaults_to_none; top_n=None = no cap

## Forward Intelligence

### What the next milestone should know
- The screener now has 14 columns in the Rich results table. Terminal width may become a concern if more columns are added.
- Pipeline has 4 clear stages (1 → 1b → 2 → 3) with clean insertion points between each. The sort/cap step between 1 and 1b is a good pattern for future pre-filtering.
- 368 tests run in under 1 second — the test suite is fast and reliable.

### What's fragile
- Test console capture width is set to 200 chars — adding more columns will require widening or a different capture approach.
- S01's summary is a doctor-created placeholder — task summaries in `S01/tasks/` are the authoritative source for S01 details.

### Authoritative diagnostics
- `pytest tests/test_pipeline.py::TestTopNPipelineCap tests/test_cli_screener.py tests/test_display.py -v` — covers the full M002 surface in under 0.4 seconds.

### What assumptions changed
- None — both slices executed as planned with no scope changes or surprises. The pipeline insertion point was clean and the existing bar data had sufficient history for monthly perf computation.

## Files Created/Modified

- `screener/market_data.py` — Added `compute_monthly_performance()` (22-day lookback)
- `models/screened_stock.py` — Added `perf_1m: Optional[float]` field
- `screener/pipeline.py` — Added `top_n` parameter, sort/cap logic after Stage 1, perf_1m population
- `scripts/run_screener.py` — Added `--top-n` Typer option forwarded to `run_pipeline()`
- `screener/display.py` — Added `fmt_signed_pct()` helper and "Perf 1M" column
- `tests/test_pipeline.py` — 6 new tests in `TestTopNPipelineCap`
- `tests/test_cli_screener.py` — 3 new tests for `--top-n` flag
- `tests/test_display.py` — 8 new tests for Perf 1M column and `fmt_signed_pct()`
