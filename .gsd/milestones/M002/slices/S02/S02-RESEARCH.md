# S02: CLI Flag + Display — Research

**Date:** 2026-03-11

## Summary

S02 wires S01's `run_pipeline(top_n=N)` parameter to a `--top-n` Typer CLI option on `run-screener` and adds a "Perf 1M" column to the Rich results table reading `ScreenedStock.perf_1m`. Both changes are straightforward — the hard work (pipeline refactoring, sort/cap logic, perf computation) is done in S01.

The main integration risk is that S01's branch (`gsd/M002/S01`) must be merged into this branch first. The code changes are small: one new Typer `Option` parameter, one `top_n=` kwarg passthrough to `run_pipeline()`, one new column + row cell in `render_results_table()`, and corresponding tests.

## Recommendation

Two tasks:

1. **T01 — CLI flag**: Add `--top-n` option to `scripts/run_screener.py`, pass through to `run_pipeline(top_n=top_n)`. Typer supports `min=1` validation natively. Tests: flag appears in help, value passes through to pipeline, omitting flag passes `top_n=None` (backward compat), invalid values rejected.

2. **T02 — Display column**: Add "Perf 1M" column to `render_results_table()` in `screener/display.py`. Format with `fmt_pct()` (already handles sign and None→"N/A"). Tests: column header present, values formatted correctly, None shows "N/A".

Merge S01 branch before starting T01.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option validation (min >= 1) | `typer.Option(min=1)` | Native Typer validation; no custom callback needed |
| Percentage formatting | `fmt_pct()` in `screener/display.py` | Already formats `float → "X.X%"`, handles None→"N/A", includes negative sign |
| CLI test runner | `typer.testing.CliRunner` | Already used in `test_cli_screener.py`; proven pattern |
| Console capture for display tests | `Console(file=StringIO(), width=120)` | Already used in `test_display.py`; `_capture_console()` helper exists |

## Existing Code and Patterns

- `scripts/run_screener.py` — CLI entry point using Typer. Four existing `Annotated[..., typer.Option()]` parameters. New `--top-n` follows identical pattern. Must pass `top_n=top_n` kwarg to `run_pipeline()` call at line ~119.
- `screener/display.py:render_results_table()` — Rich table with 13 columns. "Perf 1M" inserts after "HV%ile" (column index 10) and before "Yield" to group performance/volatility metrics together. Uses `fmt_pct()` for percentage columns (RSI, HV%ile, Yield, Margin, Growth).
- `tests/test_cli_screener.py` — 4 existing CLI tests using `typer.testing.CliRunner` with `@patch` decorators on `scripts.run_screener.*` imports (D019 pattern). New tests follow same mock pattern.
- `tests/test_display.py` — 35 existing tests. `_make_stock()` helper builds `ScreenedStock` objects. `_all_pass_filters()` returns passing filter results. `_capture_console()` captures Rich output to StringIO. New display tests follow same pattern.
- `models/screened_stock.py` — `perf_1m: Optional[float] = None` field (added by S01, line 40 on S01 branch).

## Constraints

- S01 branch must be merged first — `perf_1m` field, `compute_monthly_performance()`, and `top_n` parameter don't exist on current branch.
- `typer.Option(min=1)` requires `int | None` type annotation — Typer 0.24.1 supports this for optional int options.
- `fmt_pct()` already shows sign for negative values (`-3.7%`) but not explicit `+` for positive. This is acceptable — matches RSI/Margin/Growth column behavior (no `+` prefix on positive values). If explicit `+` is wanted, a small wrapper suffices.
- The CLI test mocking pattern (D019) patches at `scripts.run_screener.<name>` not at source module — all imports are module-level in `run_screener.py`.

## Common Pitfalls

- **Forgetting to pass `top_n` kwarg through** — If `top_n` is added to the CLI function signature but not forwarded to `run_pipeline()`, the flag silently does nothing. Test must verify `run_pipeline` receives the value.
- **Column order mismatch in tests** — `test_table_has_column_headers` checks a fixed list of column names. Adding "Perf 1M" requires updating the assertion list or adding a separate test.
- **`_make_stock()` helper missing `perf_1m`** — The test helper in `test_display.py` needs a `perf_1m` kwarg to set the field for display tests. Without it, all "Perf 1M" values render as "N/A".
- **`--top-n` vs `--top_n` naming** — Typer converts underscores to hyphens by default. The Python parameter should be `top_n` which Typer exposes as `--top-n` on CLI. No special config needed.

## Open Risks

- S01 merge conflict potential: S01 modifies `pipeline.py` significantly (two-pass refactor). If any other work touched pipeline.py on `gsd/M002/S02` branch, merge conflicts could arise. Current diff shows no pipeline changes on S02 branch, so risk is low.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer | — | none needed (simple Option addition; well-documented in existing code) |
| Rich | — | none needed (follows existing table column pattern) |

## Sources

- S01 task summaries on `gsd/M002/S01` branch (T01-SUMMARY.md, T02-SUMMARY.md) — confirmed deliverables: `perf_1m` field, `compute_monthly_performance()`, `run_pipeline(top_n=)`, 12 new tests
- S01 diff (`git diff gsd/M002/S02..gsd/M002/S01 -- screener/pipeline.py`) — confirmed two-pass architecture and `top_n` parameter signature
- Existing test files (`test_cli_screener.py`, `test_display.py`) — confirmed mock/capture patterns
- Typer 0.24.1 `Option()` signature — confirmed `min`/`max` parameter support
