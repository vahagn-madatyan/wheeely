# S02: CLI Flag + Display

**Goal:** User can run `run-screener --top-n 20` and see results with a "Perf 1M" column, completing in minutes instead of hours.
**Demo:** `run-screener --top-n 20` shows ≤20 scored results with Perf 1M percentages visible in the table.

## Must-Haves

- `--top-n` Typer option on `run-screener` that passes through to `run_pipeline(top_n=N)`
- "Perf 1M" column in `render_results_table()` showing `perf_1m` percentage for each stock
- Backward compatible: `run-screener` without `--top-n` behaves identically to before

## Verification

- `pytest tests/test_display.py -v` — includes test for Perf 1M column rendering
- `pytest tests/test_run_screener.py -v` — includes test for `--top-n` CLI flag parsing (if test file exists, else inline Typer testing)
- `pytest tests/ -v` — all 357+ tests pass, no regressions

## Integration Closure

- Upstream surfaces consumed: `run_pipeline(top_n=N)` from S01, `ScreenedStock.perf_1m` field from S01
- New wiring introduced in this slice: CLI flag → pipeline parameter, perf_1m → table column
- What remains before the milestone is truly usable end-to-end: nothing — this is the terminal slice

## Tasks

- [ ] **T01: Add --top-n CLI flag, Perf 1M column, and tests** `est:20m`
  - Why: Single task — both changes are small and tightly coupled (flag feeds pipeline, field feeds display). Splitting would be artificial.
  - Files: `scripts/run_screener.py`, `screener/display.py`, `tests/test_display.py`
  - Do:
    1. Add `top_n: Annotated[int | None, typer.Option("--top-n", help="Cap Stage 1 survivors to N worst-performing stocks")] = None` parameter to `run()` in `run_screener.py`
    2. Pass `top_n=top_n` to `run_pipeline()` call
    3. Add "Perf 1M" column to `render_results_table()` between "HV%ile" and "Yield" — use `fmt_pct(stock.perf_1m)` with "N/A" fallback for None
    4. Add test for Perf 1M column rendering: create ScreenedStock fixtures with known perf_1m values, call `render_results_table()`, capture console output, assert "Perf 1M" header and formatted values appear
    5. Add test for --top-n flag: use Typer's CliRunner to invoke with `--top-n 5`, verify the parameter reaches `run_pipeline` (mock pipeline, check kwargs)
  - Verify: `pytest tests/ -v` — all tests pass including new ones
  - Done when: `--top-n` flag accepted by CLI, "Perf 1M" column visible in table output, all tests green

## Files Likely Touched

- `scripts/run_screener.py`
- `screener/display.py`
- `tests/test_display.py`
