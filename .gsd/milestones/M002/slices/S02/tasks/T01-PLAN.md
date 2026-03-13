---
estimated_steps: 6
estimated_files: 4
---

# T01: Add --top-n CLI flag, Perf 1M column, and tests

**Slice:** S02 — CLI Flag + Display
**Milestone:** M002

## Description

Add `--top-n` Typer option to `run-screener`, add "Perf 1M" column to the results table, and write tests for both.

## Steps

1. Merge S01 from main into S02 branch (prerequisite for `perf_1m` field and `top_n` pipeline param)
2. Add `--top-n` Typer option to `scripts/run_screener.py` — `Optional[int]`, default None, min=1, passed to `run_pipeline(top_n=N)`
3. Add `fmt_signed_pct()` helper and "Perf 1M" column to `screener/display.py:render_results_table()` between HV%ile and Yield
4. Write CLI tests in `tests/test_cli_screener.py` — help text includes `--top-n`, flag value forwarded to pipeline, backward compat (no flag = no top_n)
5. Write display tests in `tests/test_display.py` — Perf 1M header present, values formatted with sign, None → N/A
6. Run full test suite to confirm no regressions

## Must-Haves

- [ ] `--top-n` flag accepted by `run-screener` CLI
- [ ] `top_n` value forwarded to `run_pipeline()` call
- [ ] "Perf 1M" column visible in results table with signed percentages
- [ ] `run-screener` without `--top-n` still works (backward compat)
- [ ] All 357+ existing tests pass plus new tests

## Verification

- `pytest tests/test_cli_screener.py -v` — new `--top-n` tests pass
- `pytest tests/test_display.py -v` — new Perf 1M tests pass
- `pytest tests/ -v` — all tests pass, no regressions

## Inputs

- S01 code on main: `perf_1m` field on ScreenedStock, `run_pipeline(top_n=)` param, `compute_monthly_performance()`
- Existing patterns in `scripts/run_screener.py` (Typer options), `screener/display.py` (columns), `tests/test_cli_screener.py` (CliRunner), `tests/test_display.py` (_make_stock helper)

## Expected Output

- `scripts/run_screener.py` — `--top-n` option added, passed to pipeline
- `screener/display.py` — `fmt_signed_pct()` helper, "Perf 1M" column in table
- `tests/test_cli_screener.py` — 2-3 new tests for `--top-n`
- `tests/test_display.py` — 3-4 new tests for Perf 1M column
