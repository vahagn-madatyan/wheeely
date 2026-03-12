# S02: CLI Flag + Display — Research

**Date:** 2026-03-11

## Summary

S02 is a thin integration slice: wire the `top_n` parameter from CLI to pipeline, and add a "Perf 1M" column to the Rich results table. All code touches are in three files (`scripts/run_screener.py`, `screener/display.py`, and tests). The existing Typer CLI and Rich table patterns are clean and consistent — S02 follows them exactly with no novel patterns needed.

S01 is fully implemented on the `gsd/M002/S01` branch (T01 + T02 complete, 357 tests passing, all boundary contract items delivered: `ScreenedStock.perf_1m`, `compute_monthly_performance()`, `run_pipeline(top_n=N)` two-pass architecture). However, S01 has **not been merged** into `main` or the current `gsd/M002/S02` branch. The first task of S02 execution must merge S01's changes into S02's branch before any new code is written.

## Recommendation

Merge S01's branch first, then follow existing patterns exactly. Add `--top-n` as an `Annotated[int | None, typer.Option()]` with `None` default (backward compatible per TOPN-06). Pass it through to `run_pipeline(top_n=N)`. Add "Perf 1M" column to `render_results_table()` using the existing `fmt_pct()` helper. Test with the same mock/patch patterns used by `test_cli_screener.py` and `test_display.py`.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI flag parsing | Typer `typer.Option()` | Already used for all CLI flags in project |
| Percentage formatting | `screener.display.fmt_pct()` | Handles None→"N/A", sign, 1 decimal |
| Console capture in tests | `Console(file=StringIO(), width=120)` | Pattern established in test_display.py |
| CLI test invocation | `typer.testing.CliRunner` | Pattern established in test_cli_screener.py |

## Existing Code and Patterns

- `scripts/run_screener.py:56-74` — `run()` function with Typer options. All options use `Annotated[type, typer.Option()]` pattern. `--top-n` follows this exactly. The function calls `run_pipeline()` at line ~90 with keyword args — `top_n` simply adds another kwarg.
- `scripts/run_screener.py:88-95` — `run_pipeline()` call site. Currently passes `trade_client`, `stock_client`, `finnhub`, `cfg`, `on_progress`, `option_client`. Add `top_n=top_n` here.
- `screener/display.py:181-193` — Column definitions in `render_results_table()`. 13 columns: #, Symbol, Price, AvgVol, MktCap, D/E, Margin, Growth, RSI, HV%ile, Yield, Score, Sector. "Perf 1M" inserts between "HV%ile" (col 10) and "Yield" (col 11) — this groups all technical/performance metrics together before options data.
- `screener/display.py:97-107` — `fmt_pct()` returns `"{value:.1f}%"` or `"N/A"`. Perfect for `perf_1m` display. Handles negatives correctly (e.g. `-5.2%`).
- `screener/display.py:202-215` — `add_row()` call. The new "Perf 1M" value must be inserted at the matching positional index (after `hv_pct_str`, before `yield_str`).
- `tests/test_cli_screener.py` — All CLI tests use `@patch("scripts.run_screener.<import>")` pattern (D019). `test_default_no_file_writes` is the template for verifying `run_pipeline` is called with correct args.
- `tests/test_display.py` — `_make_stock()` helper creates ScreenedStock with specific fields. Must extend it with `perf_1m` param or set `stock.perf_1m` directly. `_all_pass_filters()` returns passing filter results. `test_table_has_column_headers` checks column names — add "Perf 1M" to that assertion list.
- `models/screened_stock.py` — `ScreenedStock` has `perf_1m: Optional[float] = None` (on S01 branch). S02 only reads this field.

## Requirements Mapping

| Requirement | What S02 Delivers | Implementation |
|-------------|-------------------|----------------|
| TOPN-01 | `--top-n N` CLI flag | `Annotated[int \| None, typer.Option("--top-n")]` on `run()`, passed to `run_pipeline(top_n=N)` |
| TOPN-05 | "Perf 1M" column in results table | `table.add_column("Perf 1M")` + `fmt_pct(stock.perf_1m)` in `add_row()` |
| TOPN-06 | No flag = all stocks | `top_n=None` default, `run_pipeline(top_n=None)` processes all (S01 already handles this) |

## Constraints

- S01 branch (`gsd/M002/S01`) must be merged into S02 branch before any code changes — `perf_1m` field and `top_n` parameter don't exist on current branch
- `top_n` must be `Optional[int]` with `None` default — Typer renders `None` defaults as no-value in help text, which is the backward-compatible path
- Column order in `render_results_table()` must match `add_row()` positional args exactly — inserting a column requires inserting the corresponding value at the same position in every `add_row()` call
- `fmt_pct()` shows 1 decimal place without explicit `+` prefix for positive values. This is consistent with how RSI/Margin/Growth display. The TOPN-05 spec mentions "e.g. -5.2%, +3.1%" but explicit `+` is cosmetic and not a hard requirement — negative values naturally show `-`
- Typer `Option` for `int | None` type needs explicit `None` default, otherwise Typer prompts interactively

## Common Pitfalls

- **Column/row positional mismatch** — Adding `add_column("Perf 1M")` without adding the corresponding value at the same position in `add_row()` causes columns to shift. Count positions carefully: "Perf 1M" goes after HV%ile (position 10) and before Yield (position 11).
- **Typer int option with None default** — Must use `Annotated[int | None, typer.Option("--top-n", ...)] = None`. Without explicit `None`, Typer will make it required or prompt.
- **Patching run_pipeline in CLI tests** — Tests must patch `scripts.run_screener.run_pipeline` (not `screener.pipeline.run_pipeline`) because of D019's module-level import pattern. The `--top-n` flag test must verify `run_pipeline` was called with `top_n=N` in its kwargs.
- **Merge conflicts** — S01 modifies `screener/pipeline.py`, `models/screened_stock.py`, `screener/market_data.py`, and `tests/test_pipeline.py`, `tests/test_market_data.py`. S02 modifies different files (`scripts/run_screener.py`, `screener/display.py`, `tests/test_cli_screener.py`, `tests/test_display.py`), so merge should be clean. But verify by running all tests after merge.
- **Test helper _make_stock needs perf_1m** — The `_make_stock()` helper in `test_display.py` doesn't accept `perf_1m`. Either extend it with an optional `perf_1m` param or set `stock.perf_1m = value` directly after construction (both patterns used in tests).

## Open Risks

- **Merge risk** — S01 branch has 12 new tests (6 market_data, 6 pipeline) and touches 5 files. The merge to S02 should be straightforward since S02 touches different files, but full test suite must pass post-merge before proceeding.
- No other significant risks — this is low-risk wiring work with clear patterns to follow.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer | — | none needed (standard Python CLI lib, existing patterns sufficient) |
| Rich | — | none needed (standard Python TUI lib, existing patterns sufficient) |

## Sources

- S01 task summaries on `gsd/M002/S01` branch (T01-SUMMARY.md, T02-SUMMARY.md)
- S01 diff: `git diff main..gsd/M002/S01 -- screener/pipeline.py models/screened_stock.py screener/market_data.py`
- Existing codebase patterns: `scripts/run_screener.py`, `screener/display.py`, `tests/test_cli_screener.py`, `tests/test_display.py`
- Decisions D019 (CLI imports), D022 (CLI error output), D041-D044 (M002 architecture decisions)
