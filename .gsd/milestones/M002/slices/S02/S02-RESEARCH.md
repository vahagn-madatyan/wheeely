# S02: CLI Flag + Display — Research

**Date:** 2026-03-11

## Summary

S02 is a low-risk wiring slice. S01 (on branch `gsd/M002/S01`) already implemented the backend: `compute_monthly_performance()`, `ScreenedStock.perf_1m` field, `run_pipeline(top_n=N)` parameter with two-pass sort/cap architecture, and 12+ tests covering math, sort, cap, and backward compatibility. S02's job is to surface this through the CLI (`--top-n` flag) and display ("Perf 1M" column), plus merge S01 into this branch first.

All three primary requirements (TOPN-01, TOPN-05, TOPN-06) have clear insertion points with established patterns. The only wrinkle is that `fmt_pct` doesn't add a `+` prefix for positive values, and TOPN-05 specifies signed display (e.g. "+3.1%"). A small `fmt_signed_pct` helper or inline format is needed.

## Recommendation

Merge `gsd/M002/S01` into `gsd/M002/S02` first, then make three targeted changes:

1. **CLI** — Add `top_n: Annotated[int | None, typer.Option("--top-n", ...)] = None` parameter to `run()` in `scripts/run_screener.py`, pass it through to `run_pipeline(top_n=top_n)`.
2. **Display** — Add "Perf 1M" column to `render_results_table()` in `screener/display.py`. Use a signed percentage formatter. Place the column between HV%ile and Yield.
3. **Tests** — Add CLI flag tests to `test_cli_screener.py` and display column tests to `test_display.py`, following existing patterns exactly.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option parsing | Typer `typer.Option()` | Already used for all other flags in `run_screener.py` |
| Table rendering | Rich `Table.add_column()` | Already used for all other columns in `render_results_table()` |
| CLI test runner | `typer.testing.CliRunner` | Already used in `test_cli_screener.py` |
| Console capture for display tests | `Console(file=StringIO(), width=120)` | Already used in `test_display.py` |

## Existing Code and Patterns

- `scripts/run_screener.py:run()` — All CLI params use `Annotated[type, typer.Option(...)]` pattern; `run_pipeline()` call at line ~97 needs `top_n=top_n` kwarg added.
- `screener/display.py:render_results_table()` — Columns added via `table.add_column()` then values via `table.add_row()`. HV%ile and Yield already use conditional `fmt_pct(stock.field) if stock.field is not None else "N/A"` pattern.
- `screener/display.py:fmt_pct()` — Formats as `"{value:.1f}%"` but does NOT add `+` prefix for positive values. TOPN-05 requires signed display ("+3.1%", "-5.2%"). Need a new helper or inline format string.
- `tests/test_cli_screener.py` — Uses `@patch("scripts.run_screener.X")` for all dependencies. `test_default_no_file_writes` is the template for testing default behavior; `test_verbose_shows_filter_breakdown` is the template for testing a flag triggers specific behavior.
- `tests/test_display.py:_make_stock()` — Helper for creating test ScreenedStock; needs `perf_1m` kwarg added. `_all_pass_filters()` returns all-passing filter results.
- `tests/test_display.py:TestRenderResultsTable` — Tests column presence, row count, sort order, empty/zero cases. Follow this pattern for "Perf 1M" column tests.

## Constraints

- S01 branch (`gsd/M002/S01`) must be merged into S02 before implementation — it provides `perf_1m` field, `top_n` parameter, and `compute_monthly_performance()`.
- `top_n` must be `int | None` (not `int` with default 0) — `None` means "no cap" for backward compatibility (D042, TOPN-06).
- `perf_1m` is a percentage float (e.g. -5.2), not a decimal (e.g. -0.052). The formatter displays the raw value with a `%` suffix.
- The project shadows Python's `logging` module (D001) — always `import logging as stdlib_logging`.
- Typer doesn't natively support `int | None` for options — use `Optional[int]` with `default=None` or explicit `Annotated[int | None, typer.Option()]` (both patterns work in Typer ≥0.9).

## Common Pitfalls

- **Typer `int | None` handling** — Typer may not handle `int | None` union syntax in all versions. Use `Optional[int]` from typing for safety, consistent with how `PresetName | None` is already handled in the same file (though that uses the `|` syntax — verify it works for `int` too).
- **Column position in `add_row()`** — When adding a new column to the table, the positional `add_row()` arguments must stay in sync with `add_column()` order. Adding "Perf 1M" between HV%ile and Yield means inserting both the column and the row value at the correct position.
- **`_make_stock()` helper in tests** — The helper in `test_display.py` needs a `perf_1m` kwarg added, or tests must set `stock.perf_1m = value` after creation. Don't forget this or display tests will all show "N/A" for Perf 1M.
- **Merge conflicts** — S01 and S02 branches diverged from the same base. S01 added code to `pipeline.py`, `market_data.py`, `screened_stock.py`, and tests. S02 currently has none of those changes. Merge should be clean since S02 hasn't modified those files.

## Open Risks

- **S01 placeholder summary** — The S01 summary was doctor-generated. S01 task summaries should be inspected during planning to confirm all backend work is actually complete and tests pass after merge.
- **Typer `--top-n` with hyphen** — Typer converts `--top-n` to `top_n` as a Python parameter name. Verify `typer.Option("--top-n", ...)` works correctly (Typer docs confirm hyphenated option names are supported).

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer (CLI framework) | — | none found (standard library, well-documented) |
| Rich (terminal tables) | — | none found (standard library, well-documented) |
| pytest | — | none found (standard library) |

No specialized skills needed — all technologies are well-established with existing patterns in the codebase.

## Sources

- `gsd/M002/S01` branch — S01 implementation (git diff confirms `perf_1m`, `top_n`, `compute_monthly_performance` exist on that branch)
- `scripts/run_screener.py` — current CLI structure (Typer options, `run_pipeline()` call)
- `screener/display.py` — current table columns and formatters
- `tests/test_cli_screener.py` — CLI test patterns (mock decorators, CliRunner)
- `tests/test_display.py` — display test patterns (`_make_stock`, `_capture_console`, column assertions)
- `DECISIONS.md` — D041 (22-day lookback), D042 (CLI-only flag), D044 (None sorts last)
