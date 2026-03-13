---
id: S02
parent: M002
milestone: M002
provides:
  - "--top-n CLI flag on run-screener"
  - "Perf 1M column in results table"
  - "fmt_signed_pct() display helper"
requires:
  - slice: S01
    provides: "run_pipeline(top_n=N) parameter, ScreenedStock.perf_1m field"
affects: []
key_files:
  - scripts/run_screener.py
  - screener/display.py
  - tests/test_cli_screener.py
  - tests/test_display.py
key_decisions:
  - "D042: top_n is CLI-only, not configurable per preset"
patterns_established:
  - "fmt_signed_pct() for signed percentage display (+3.1%, -5.2%, N/A)"
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M002/slices/S02/tasks/T01-SUMMARY.md
duration: short
verification_result: passed
completed_at: 2026-03-12
---

# S02: CLI Flag + Display

**Added `--top-n` Typer CLI flag and "Perf 1M" column to screener results table, completing the M002 top-N performance cap feature.**

## What Happened

Single task slice. Added `--top-n` option to `scripts/run_screener.py` as `Optional[int]` with `min=1`, forwarded to `run_pipeline(top_n=)`. Added `fmt_signed_pct()` helper and "Perf 1M" column (with `no_wrap=True`) to `screener/display.py`, positioned between HV%ile and Yield. Wrote 3 CLI tests (help text, value forwarding, None default) and 8 display tests (column rendering + unit tests for the formatter).

## Verification

- `pytest tests/test_cli_screener.py -v` — 8/8 passed (5 existing + 3 new)
- `pytest tests/test_display.py -v` — 53/53 passed (45 existing + 8 new)
- `pytest tests/ -v` — 368/368 passed, no regressions (357 baseline + 11 new)

## Requirements Advanced

- TOPN-01 — CLI flag wired: `--top-n N` accepted by run-screener and forwarded to pipeline
- TOPN-05 — "Perf 1M" column renders signed percentages in Rich results table
- TOPN-06 — Omitting `--top-n` passes `top_n=None` to pipeline, preserving full processing

## Requirements Validated

- TOPN-01 — 3 CLI tests prove flag parsing, forwarding, and default behavior
- TOPN-05 — 4 display tests prove column header, positive sign, negative value, and None→N/A rendering
- TOPN-06 — test_no_top_n_defaults_to_none confirms backward compatibility

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- Widened `_capture_console()` test helper from 120→200 chars to accommodate the 14th column. Test-only change, no production impact.

## Known Limitations

- none — M002 feature complete.

## Follow-ups

- none

## Files Created/Modified

- `scripts/run_screener.py` — Added `--top-n` Typer option, forwarded to `run_pipeline(top_n=)`
- `screener/display.py` — Added `fmt_signed_pct()` helper and "Perf 1M" column in results table
- `tests/test_cli_screener.py` — 3 new tests for `--top-n` flag
- `tests/test_display.py` — 8 new tests for Perf 1M column and `fmt_signed_pct()`

## Forward Intelligence

### What the next slice should know
- M002 is complete. The screener now has 14 columns in the results table — any further columns should consider terminal width.

### What's fragile
- Test console width at 200 chars — if more columns are added, this may need widening again or a different capture approach.

### Authoritative diagnostics
- `pytest tests/test_display.py tests/test_cli_screener.py -v` — covers the full S02 surface in under 1 second.

### What assumptions changed
- none — S02 executed as planned with no surprises.
