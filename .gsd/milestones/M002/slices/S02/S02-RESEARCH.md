# S02: CLI Flag + Display — Research

**Date:** 2026-03-11

## Summary

S02 is a low-risk terminal slice that wires S01's pipeline `top_n` parameter into the `run-screener` CLI via a `--top-n` Typer option, and adds a "Perf 1M" column to the Rich results table. All the hard work (perf computation, sort/cap logic, two-pass pipeline refactor) was done in S01. S02 is purely surface-level: one CLI option, one table column, and tests for both.

The S01 branch (`gsd/M002/S01`) must be merged into S02 before implementation — it provides `run_pipeline(top_n=N)`, `ScreenedStock.perf_1m`, and `compute_monthly_performance()`. S02 consumes these without modification.

Requirements owned by this slice: **TOPN-01** (CLI flag), **TOPN-05** (Perf 1M column), **TOPN-06** (backward compat). All three are straightforward additions following existing patterns in the codebase.

## Recommendation

Merge S01 into S02 branch first. Then implement in two small tasks:

1. **CLI flag** — Add `--top-n` Typer option to `scripts/run_screener.py`, pass through to `run_pipeline(top_n=N)`. Add Typer `min=1` constraint. Write 3 tests: flag passes to pipeline, no flag = `top_n=None`, `--help` shows `--top-n`.
2. **Display column** — Add "Perf 1M" column to `render_results_table()` in `screener/display.py` with signed percentage formatting (`+3.1%`, `-5.2%`, `N/A`). Write 3-4 tests: column appears, positive/negative formatting, None shows N/A.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option parsing | Typer `Annotated[int \| None, typer.Option()]` | Already used for all other flags in `run_screener.py` |
| Terminal table rendering | Rich `Table.add_column()` + `table.add_row()` | Already used for all other columns in `render_results_table()` |
| Percentage formatting | `screener/display.py:fmt_pct()` | Exists but needs a signed variant for perf_1m (no `+` prefix currently) |
| CLI testing | `typer.testing.CliRunner` + `@patch` | Established pattern in `tests/test_cli_screener.py` |

## Existing Code and Patterns

- `scripts/run_screener.py:run()` — CLI entry point using Typer `Annotated` options. All existing flags (`--update-symbols`, `--verbose`, `--preset`, `--config`) follow identical pattern. Add `--top-n` the same way.
- `scripts/run_screener.py:119-126` — `run_pipeline()` call site. Currently passes `trade_client`, `stock_client`, `finnhub`, `cfg`, `on_progress`, `option_client`. After S01 merge, add `top_n=top_n` kwarg.
- `screener/display.py:render_results_table()` — Builds Rich Table with 13 columns (#, Symbol, Price, AvgVol, MktCap, D/E, Margin, Growth, RSI, HV%ile, Yield, Score, Sector). Insert "Perf 1M" column after HV%ile, before Yield.
- `screener/display.py:fmt_pct()` — Formats `float | None → str` as `"X.X%"` or `"N/A"`. Does NOT add `+` prefix for positive values. Perf 1M needs signed output per TOPN-05 (`-5.2%`, `+3.1%`). Options: (a) new `fmt_signed_pct()` helper, or (b) inline format in `render_results_table`. Recommend (a) for testability.
- `tests/test_cli_screener.py` — 5 existing CLI tests. Pattern: heavy `@patch("scripts.run_screener.X")` decoration, `CliRunner.invoke(app, args)`, assert on `exit_code` and `mock.assert_called_*`. The `test_default_no_file_writes` test verifies `mock_pipeline.assert_called_once()` — extend to check `top_n` kwarg.
- `tests/test_display.py` — 45 existing display tests. Pattern: `_capture_console()` → call render function → string assertions on `console.file.getvalue()`. `_make_stock()` helper builds ScreenedStock with controllable fields. Add `perf_1m` param to `_make_stock()`.

## Constraints

- **S01 merge required** — `gsd/M002/S01` branch must be merged into `gsd/M002/S02` before any code changes. S01 provides `run_pipeline(top_n=)`, `ScreenedStock.perf_1m`, and `compute_monthly_performance` import in `pipeline.py`.
- **Typer version ≥0.9.0** — `Annotated` syntax is supported. `int | None` union type requires Python 3.10+ (project already uses this syntax for other Typer options).
- **Backward compat (TOPN-06)** — `--top-n` omitted must result in `top_n=None` passed to pipeline. Default `= None` on the Typer option handles this.
- **No default cap** — Per D042, `top_n` is CLI-only, not preset-configurable. No preset YAML changes needed.
- **Existing test count** — 357 tests (345 baseline + 12 from S01) must continue passing after S02 changes.

## Common Pitfalls

- **Typer hyphen/underscore conversion** — Typer automatically converts `--top-n` CLI flag to `top_n` Python parameter. Define the parameter as `top_n` with `typer.Option("--top-n", ...)` to be explicit. The existing `--update-symbols` → `update_symbols` pattern confirms this works.
- **fmt_pct lacks sign prefix** — Using `fmt_pct()` directly for perf_1m would show `3.1%` instead of `+3.1%`. Need a dedicated `fmt_signed_pct()` or inline `f"{value:+.1f}%"` format string. Python's `+` format spec handles this natively.
- **Display test helper needs perf_1m** — `_make_stock()` in `tests/test_display.py` doesn't accept `perf_1m`. Must add it or set `stock.perf_1m = X` directly after creation. Direct assignment is simpler and follows the existing pattern for `hv_percentile` and `put_premium_yield`.
- **Column count in existing tests** — Tests that check for specific column headers (e.g. `test_table_has_column_headers`) will still pass because they check for column name presence, not column count. No breakage expected.
- **Typer min=1 validation** — `typer.Option(min=1)` prevents `--top-n 0` or negative values. Without this, `run_pipeline(top_n=0)` would return 0 stocks with no error.

## Open Risks

- **None** — This is the lowest-risk slice in the milestone. All patterns are established, all dependencies are delivered by S01, and the implementation is purely additive (one option, one column, one formatter).

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer | — | none found (no skill needed; pattern already established in codebase) |
| Rich | — | none found (no skill needed; pattern already established in codebase) |

## Sources

- S01 task summaries on `gsd/M002/S01` branch — confirmed `run_pipeline(top_n=N)` signature, `ScreenedStock.perf_1m` field, and 12 passing tests
- `scripts/run_screener.py` — existing CLI option patterns (Typer `Annotated` with `typer.Option`)
- `screener/display.py` — existing table column patterns and `fmt_pct` limitation (no sign prefix)
- `tests/test_cli_screener.py` — existing mock-heavy CLI test pattern with `CliRunner`
- `tests/test_display.py` — existing display test pattern with `_capture_console()` and string assertions
