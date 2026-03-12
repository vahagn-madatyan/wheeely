# S02: CLI Flag + Display — Research

**Date:** 2026-03-11

## Summary

S02 wires the `top_n` pipeline parameter (delivered by S01) to the CLI via a `--top-n` Typer option and adds a "Perf 1M" column to the Rich results table. Both changes are straightforward — the CLI already follows an established `Annotated[type, typer.Option()]` pattern and the display table already handles optional numeric columns (HV%ile, Yield). The main prerequisite is merging S01's branch (`gsd/M002/S01`) into S02's branch before coding.

The slice owns requirements TOPN-01 (CLI flag), TOPN-05 (display column), and TOPN-06 (backward compatibility). All three are low-risk given S01 already delivered the underlying `run_pipeline(top_n=N)` parameter, `ScreenedStock.perf_1m` field, and sort/cap logic with 6 pipeline tests.

## Recommendation

Merge S01 first, then implement in two tasks:

1. **CLI flag** — Add `--top-n` option to `scripts/run_screener.py`, pass through to `run_pipeline()`. Test with `typer.testing.CliRunner` mocks (follow existing `test_cli_screener.py` patterns).
2. **Display column** — Add "Perf 1M" column to `render_results_table()` in `screener/display.py`. Use a sign-aware formatter (`+3.1%` / `-5.2%`) since the existing `fmt_pct` doesn't show `+` for positive values. Test with `Console(file=StringIO())` capture (follow existing `test_display.py` patterns).

Both tasks can potentially be combined into a single task given the low complexity.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option parsing | `typer.Option` with `Annotated` | Already used for all 4 existing options in `run_screener.py` |
| CLI testing | `typer.testing.CliRunner` | Already used in `test_cli_screener.py` for 5 tests |
| Table rendering | Rich `Table.add_column()` + `table.add_row()` | Already used in `render_results_table()` for 13 columns |
| Display testing | `Console(file=StringIO(), width=120)` | Already used in `test_display.py` for all display tests |

## Existing Code and Patterns

- `scripts/run_screener.py:run()` — CLI entry point. Uses `Annotated[type, typer.Option("--flag", help="...")]` for all options. Calls `run_pipeline(...)` at line 119. Add `top_n` to that call.
- `screener/display.py:render_results_table()` — Adds columns via `table.add_column()`, formats values in row loop. HV%ile/Yield pattern: `fmt_pct(stock.field) if stock.field is not None else "N/A"`. Follow same for `perf_1m`.
- `screener/display.py:fmt_pct()` — Returns `"{value:.1f}%"`. Does NOT prefix `+` for positive values. For Perf 1M, need either a new `fmt_pct_signed()` helper or inline formatting.
- `tests/test_cli_screener.py` — Uses `@patch("scripts.run_screener.<module>")` pattern. Existing `test_default_no_file_writes` verifies `run_pipeline` is called — extend to check `top_n` kwarg.
- `tests/test_display.py:_make_stock()` — Helper builds `ScreenedStock` with keyword args. Doesn't currently accept `perf_1m` — needs a new kwarg or use `setattr` pattern from `test_options_chain.py`.
- `tests/test_display.py:TestRenderResultsTable` — Verifies column headers, row count, sort order, empty states. Follow same pattern for "Perf 1M" column.
- `models/screened_stock.py` — S01 adds `perf_1m: Optional[float] = None` (on S01 branch, not yet merged).
- `screener/pipeline.py:run_pipeline()` — S01 adds `top_n: int | None = None` parameter (on S01 branch, not yet merged).

## Constraints

- **S01 must be merged first** — The `gsd/M002/S01` branch contains `perf_1m` field, `compute_monthly_performance()`, `top_n` parameter on `run_pipeline()`, and 6 pipeline tests. Current `gsd/M002/S02` branch does NOT have these changes.
- `--top-n` must accept positive integers only — Typer's `int` type handles basic validation; add `min=1` or validate in the handler.
- `top_n=None` when flag omitted — default must be `None` (not 0) to preserve backward compatibility per TOPN-06 and D042.
- 345 existing tests must continue to pass after changes.
- `fmt_pct` is used elsewhere — don't modify its signature; add a new helper for signed formatting if needed.
- Column order in the table matters for readability — "Perf 1M" logically goes after HV%ile (technical indicators cluster) and before Yield (options data) or Score.

## Common Pitfalls

- **Forgetting to merge S01** — The S02 branch currently has no `perf_1m` field or `top_n` parameter. Code will fail immediately without merging `gsd/M002/S01` first.
- **`top_n=0` vs `top_n=None`** — Typer defaults `int | None` options to `None` when omitted, but `--top-n 0` would be a valid but nonsensical input. Add a `min=1` constraint or validate.
- **Sign formatting for Perf 1M** — Requirement TOPN-05 specifies signed format (e.g. `-5.2%`, `+3.1%`). The existing `fmt_pct` only shows `-` for negative. Using `fmt_pct` directly would miss the `+` prefix on positive values.
- **`_make_stock` helper in test_display.py** — Doesn't accept `perf_1m` kwarg. Either add it or use `setattr()` after creation (the `test_options_chain.py` pattern is more flexible with `**kwargs`).
- **Patching `run_pipeline` in CLI tests** — Must patch at `scripts.run_screener.run_pipeline` (the import location), not `screener.pipeline.run_pipeline`.

## Open Risks

- **None** — This is a low-risk, well-defined slice. All patterns are established, all APIs are known, and S01 has already proven the underlying pipeline changes work.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer | — | none found (well-known, no skill needed) |
| Rich | — | none found (well-known, no skill needed) |

## Sources

- Codebase exploration: `scripts/run_screener.py`, `screener/display.py`, `tests/test_display.py`, `tests/test_cli_screener.py`, `models/screened_stock.py`
- S01 branch diff: `git diff main..gsd/M002/S01` for pipeline.py, market_data.py, screened_stock.py, test files
- Typer 0.24.1 installed in project virtualenv
