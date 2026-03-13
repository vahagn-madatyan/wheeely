# S02: CLI Flag + Display

**Milestone:** M002 — Top-N Performance Cap
**Goal:** User can run `run-screener --top-n 20` and see results with a "Perf 1M" column, completing in minutes instead of hours.
**Demo:** `run-screener --top-n 20` shows ≤20 scored results with Perf 1M percentages visible in the table.
**Risk:** low
**Depends on:** S01

## Tasks

- [x] **T01: Add --top-n CLI flag, Perf 1M column, and tests** `est:medium`

## Verification

- `pytest tests/test_display.py -v` — includes test for Perf 1M column rendering
- `pytest tests/test_cli_screener.py -v` — includes test for `--top-n` CLI flag parsing
- `pytest tests/ -v` — all 357+ tests pass, no regressions
