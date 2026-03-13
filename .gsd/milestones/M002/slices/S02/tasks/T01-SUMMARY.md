---
id: T01
parent: S02
milestone: M002
provides:
  - "--top-n CLI flag on run-screener"
  - "Perf 1M column in results table"
  - "fmt_signed_pct() display helper"
key_files:
  - scripts/run_screener.py
  - screener/display.py
  - tests/test_cli_screener.py
  - tests/test_display.py
key_decisions:
  - "Widened test capture console from 120→200 to accommodate the extra column"
  - "Added no_wrap=True on Perf 1M column to prevent Rich from splitting header across lines"
patterns_established:
  - "fmt_signed_pct() for signed percentage display (+3.1%, -5.2%, N/A)"
observability_surfaces:
  - none
duration: short
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T01: Add --top-n CLI flag, Perf 1M column, and tests

**Added `--top-n` Typer option to `run-screener` and "Perf 1M" column to the results table with 11 new tests.**

## What Happened

1. Merged main (containing S01's squash-merged code) into S02 branch — resolved one conflict in `.gsd/STATE.md`.
2. Added `--top-n` option to `scripts/run_screener.py` using `Optional[int]` with `min=1`, forwarded as `top_n=` kwarg to `run_pipeline()`.
3. Added `fmt_signed_pct()` helper to `screener/display.py` — uses Python's `+` format flag for `+3.1%` / `-5.2%` style.
4. Added "Perf 1M" column to `render_results_table()` between HV%ile and Yield, with `no_wrap=True`.
5. Wrote 3 CLI tests: help text includes `--top-n`, flag value forwarded to pipeline, omitted flag defaults to None.
6. Wrote 8 display tests: 4 for Perf 1M column rendering (header present, positive sign, negative value, None→N/A) and 4 for `fmt_signed_pct()` unit tests.

## Verification

- `pytest tests/test_cli_screener.py -v` — 8/8 passed (5 existing + 3 new)
- `pytest tests/test_display.py -v` — 53/53 passed (45 existing + 8 new)
- `pytest tests/ -v` — 368/368 passed, no regressions (357 baseline + 11 new)

All three slice-level verification checks pass. This is the only task in S02.

## Diagnostics

None — CLI tool, no runtime surfaces.

## Deviations

- Widened `_capture_console()` from 120→200 chars. Adding a 14th column pushed "Sector" off-screen at 120 width. This affected only the test helper, not production rendering.
- S02-PLAN.md and T01-PLAN.md had to be created (they didn't exist at dispatch time — only S02-RESEARCH.md was present).

## Known Issues

None.

## Files Created/Modified

- `scripts/run_screener.py` — Added `--top-n` Typer option, forwarded to `run_pipeline(top_n=)`
- `screener/display.py` — Added `fmt_signed_pct()` helper and "Perf 1M" column in results table
- `tests/test_cli_screener.py` — 3 new tests for `--top-n` flag
- `tests/test_display.py` — 8 new tests for Perf 1M column and `fmt_signed_pct()`
- `.gsd/milestones/M002/slices/S02/S02-PLAN.md` — Created slice plan
- `.gsd/milestones/M002/slices/S02/tasks/T01-PLAN.md` — Created task plan
