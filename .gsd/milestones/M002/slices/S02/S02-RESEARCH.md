# S02: CLI Flag + Display — Research

**Date:** 2026-03-11

## Summary

S02 is a thin integration slice: wire the `top_n` parameter from CLI to pipeline, and add a "Perf 1M" column to the Rich results table. All code touches are in three files (`scripts/run_screener.py`, `screener/display.py`, and tests). The existing Typer CLI and Rich table patterns are clean and consistent — S02 follows them exactly with no novel patterns needed.

**Critical dependency:** S01 (Monthly Perf + Pipeline Cap) has not been implemented yet. The `perf_1m` field on `ScreenedStock` and `top_n` parameter on `run_pipeline()` do not exist in the codebase. S02 cannot be executed until S01 is complete. Research below assumes S01 delivers the boundary map contract: `ScreenedStock.perf_1m: Optional[float]` and `run_pipeline(top_n=None)`.

## Recommendation

Follow existing patterns exactly. Add `--top-n` as an `Optional[int]` Typer option with `None` default (backward compatible per TOPN-06). Pass it through to `run_pipeline(top_n=N)`. Add "Perf 1M" column to `render_results_table()` using the existing `fmt_pct()` helper. Test with the same mock/patch patterns used by `test_cli_screener.py` and `test_display.py`.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI flag parsing | Typer `typer.Option()` | Already used for all CLI flags in project |
| Percentage formatting | `screener.display.fmt_pct()` | Handles None→"N/A", sign, 1 decimal |
| Console capture in tests | `Console(file=StringIO(), width=120)` | Pattern established in test_display.py |
| CLI test invocation | `typer.testing.CliRunner` | Pattern established in test_cli_screener.py |

## Existing Code and Patterns

- `scripts/run_screener.py:56-74` — `run()` function with Typer options. All options use `Annotated[type, typer.Option()]` pattern. `--top-n` follows this exactly. Note: the function calls `run_pipeline()` at line ~90 with keyword args — `top_n` simply adds another kwarg.
- `scripts/run_screener.py:88-95` — `run_pipeline()` call site. Currently passes `trade_client`, `stock_client`, `finnhub`, `cfg`, `on_progress`, `option_client`. Add `top_n=top_n` here.
- `screener/display.py:149-198` — `render_results_table()` with 13 columns. The "Perf 1M" column inserts naturally between "HV%ile" and "Yield" (or after "Yield" before "Score"). Uses `table.add_column()` then matching `table.add_row()` positional args.
- `screener/display.py:97-107` — `fmt_pct()` returns `"{value:.1f}%"` or `"N/A"`. Perfect for `perf_1m` display. Note: `perf_1m` can be negative (e.g. `-5.2%`), and `fmt_pct` handles negatives correctly.
- `tests/test_cli_screener.py` — All CLI tests use `@patch("scripts.run_screener.<import>")` pattern (D019). The `test_default_no_file_writes` test is the template for verifying `run_pipeline` is called with correct args.
- `tests/test_display.py` — `_make_stock()` helper creates `ScreenedStock` with specific fields. Add `perf_1m` param to this helper. `_all_pass_filters()` returns passing filter results. `TestRenderResultsTable.test_table_has_column_headers` checks column names in output — add "Perf 1M" check here.
- `models/screened_stock.py` — `ScreenedStock` dataclass. S01 should add `perf_1m: Optional[float] = None`. S02 only reads this field.

## Constraints

- `perf_1m` field and `top_n` parameter must exist before S02 can be implemented (S01 dependency)
- `top_n` must be `Optional[int]` with `None` default — Typer renders `None` defaults as no-value, which is the backward-compatible path (TOPN-06)
- `fmt_pct()` shows 1 decimal place — this matches the context's format spec ("e.g. -5.2%, +3.1%") except it won't show explicit `+` for positive values. To match TOPN-05's "with sign" spec, either: (a) accept that negative values naturally show `-` and positive don't show `+`, or (b) add a small `fmt_perf_pct()` variant that adds `+` prefix. Recommend (a) — consistent with how RSI/Margin/Growth columns display, and `+` prefix is not a hard requirement.
- Column order in `render_results_table()` must match `add_row()` positional args exactly — inserting a column requires inserting the corresponding value in every `add_row()` call
- Typer `Option` for int with None default needs `Optional[int]` type annotation (not bare `int`), otherwise Typer treats it as required

## Common Pitfalls

- **Column/row positional mismatch** — Adding `add_column("Perf 1M")` without adding the corresponding value at the same position in `add_row()` causes columns to shift. Count positions carefully.
- **Typer int option with None default** — `typer.Option()` with `int | None` type needs explicit `None` default. Without it, Typer prompts for the value interactively. Pattern: `top_n: Annotated[int | None, typer.Option("--top-n", ...)] = None`.
- **Patching run_pipeline in CLI tests** — The test patches `scripts.run_screener.run_pipeline` (not `screener.pipeline.run_pipeline`) because of D019's module-level import pattern. The `--top-n` flag test must verify `run_pipeline` was called with `top_n=N` in its kwargs.
- **Test helper _make_stock needs perf_1m** — The `_make_stock()` helper in `test_display.py` doesn't accept `perf_1m`. Must extend it or set `stock.perf_1m` directly after construction.

## Open Risks

- **S01 not implemented** — The roadmap marks S01 as `[x]` (complete) but the code has no `perf_1m` field, no `top_n` parameter, no `compute_monthly_performance` function. The S01 summary is a doctor-created placeholder. S02 cannot proceed until S01 actually delivers its boundary contract. This is the only real risk.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer | — | none found (standard Python CLI lib, no skill needed) |
| Rich | — | none found (standard Python TUI lib, no skill needed) |

## Sources

- Existing codebase patterns (source: `scripts/run_screener.py`, `screener/display.py`, `tests/test_cli_screener.py`, `tests/test_display.py`)
- Milestone context and boundary map (source: `.gsd/milestones/M002/M002-CONTEXT.md`, `M002-ROADMAP.md`)
- Decision register D019, D022 (source: `.gsd/DECISIONS.md`)
