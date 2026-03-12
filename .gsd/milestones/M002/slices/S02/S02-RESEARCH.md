# S02: CLI Flag + Display — Research

**Date:** 2026-03-11

## Summary

S02 is the terminal slice for M002, wiring S01's pipeline `top_n` parameter to a `--top-n` CLI flag on `run-screener` and adding a "Perf 1M" column to the Rich results table. This is low-risk work touching three production files (`scripts/run_screener.py`, `screener/display.py`, `models/screened_stock.py` helper update) plus two test files.

S01 is fully implemented on the `gsd/M002/S01` branch. It delivers: `ScreenedStock.perf_1m: Optional[float]` field, `compute_monthly_performance(bars_df)` function, and `run_pipeline(top_n=N)` parameter with two-pass pipeline architecture (Stage 1 → sort/cap → Stage 1b/2/3). The S02 branch (`gsd/M002/S02`) does NOT yet contain these changes — they must be merged in before any S02 work begins.

The existing codebase has clear, consistent patterns for both CLI options (Typer `Annotated` style with `typer.Option()`) and display columns (Rich `Table.add_column()` / `.add_row()`). No new libraries needed, no architectural decisions, no API calls — pure wiring and formatting.

## Recommendation

Follow established patterns exactly:
1. Merge `gsd/M002/S01` into `gsd/M002/S02` as the first step.
2. Add `--top-n` as a `typer.Option` with `Annotated[int | None, typer.Option("--top-n", ...)]` defaulting to `None`, matching existing flag patterns.
3. Pass `top_n=top_n` to `run_pipeline()` in the CLI handler.
4. Add a `fmt_pct_signed()` formatter (or extend inline) for explicit `+`/`-` signs since TOPN-05 requires `+3.1%` format.
5. Add "Perf 1M" column to `render_results_table()` between "HV%ile" and "Yield" using the signed formatter.
6. Tests follow existing patterns: `CliRunner` + `@patch` for CLI, `_capture_console` + direct field assignment for display.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option parsing | `Annotated[..., typer.Option()]` in `run_screener.py` | All 4 existing flags use this exact pattern |
| Percentage formatting | `fmt_pct()` in `screener/display.py` | Handles `None` → `"N/A"`, consistent `X.X%` format |
| Table rendering | Rich `Table.add_column()` / `.add_row()` | 13 columns already follow this pattern |
| CLI test harness | `typer.testing.CliRunner` + `@patch` | 5 existing tests in `test_cli_screener.py` use this |
| Display test capture | `Console(file=StringIO())` | `_capture_console()` helper in `test_display.py` |

## Existing Code and Patterns

- **`scripts/run_screener.py:run()`** — CLI handler. 4 existing `Annotated[..., typer.Option()]` parameters. The `run_pipeline()` call at ~line 120 needs `top_n=top_n` kwarg. Follow existing `option_client=broker.option_client` passthrough pattern.
- **`screener/pipeline.py:run_pipeline(top_n=None)`** — S01 added `top_n: int | None = None` as the last keyword parameter. When set, sorts Stage 1 survivors ascending by `perf_1m` (None→∞) and caps to N before Stage 1b/2/3. When `None`, all survivors proceed.
- **`screener/display.py:render_results_table()`** — Builds Rich Table with 13 columns (`#`, Symbol, Price, AvgVol, MktCap, D/E, Margin, Growth, RSI, HV%ile, Yield, Score, Sector). "Perf 1M" inserts between HV%ile and Yield (after line 190, before line 191).
- **`screener/display.py:fmt_pct()`** — `f"{value:.1f}%"` — negative sign included automatically but no explicit `+` for positives. TOPN-05 requires `+3.1%` format, so a new `fmt_pct_signed()` helper is needed.
- **`models/screened_stock.py`** — S01 added `perf_1m: Optional[float] = None` after `hv_percentile` in the technical indicators block.
- **`screener/market_data.py:compute_monthly_performance()`** — S01 added: `(close[-1] / close[-22] - 1) * 100`, returns `None` for < 22 bars.
- **`tests/test_cli_screener.py`** — 5 tests. Heavy mocking with `@patch("scripts.run_screener.X")`. `test_screener_help` checks `--help` output for all flags. `test_default_no_file_writes` verifies default invocation calls `run_pipeline` and displays results.
- **`tests/test_display.py`** — `_make_stock()` helper creates `ScreenedStock` with arbitrary fields (does NOT accept `perf_1m` kwarg — set directly on object). `_all_pass_filters()` returns passing filter results. `_capture_console()` returns `Console(file=StringIO(), width=120)`.

## Constraints

- **S01 merge required first.** `perf_1m` field and `top_n` parameter exist only on `gsd/M002/S01`. S02 branch must incorporate S01's changes. Diff shows 5 files, 407 additions — clean separation from S02's target files (`run_screener.py`, `display.py`).
- **`--top-n` must be `int | None`, default `None`.** Typer handles `Optional[int]` natively. When omitted, `top_n=None` passes through to pipeline (backward compatible per TOPN-06).
- **Positive integer only.** Typer's type annotation handles `int` parsing. Zero or negative values should be rejected — add a `min=1` constraint or validate in the handler.
- **Sign-prefixed percentage display.** `fmt_pct()` uses `f"{value:.1f}%"` which yields `-5.2%` but `3.1%` (no `+`). TOPN-05 spec says `+3.1%`. Need explicit sign formatting.
- **Column ordering.** "Perf 1M" logically belongs between HV%ile (technical indicator) and Yield (options data). Insert at column index ~10.
- **345 existing tests must pass.** S01 added ~67 test lines in `test_market_data.py` and 267 lines in `test_pipeline.py`. These run on the S01 branch; after merge they must continue to pass on S02.

## Common Pitfalls

- **Forgetting S01 merge** — Without it, `perf_1m`, `compute_monthly_performance`, and `top_n` don't exist. The build will fail immediately.
- **Missing `+` sign on positive percentages** — `fmt_pct(3.1)` returns `"3.1%"` not `"+3.1%"`. Need `f"+{value:.1f}%"` for `value > 0`, `f"{value:.1f}%"` for `value <= 0` (negative sign auto-included), or `f"{value:+.1f}%"` using Python's `+` format flag which handles both signs.
- **Typer `--top-n` hyphenated flag** — Typer auto-converts `--top-n` to `top_n` as the Python parameter name. Use `typer.Option("--top-n", ...)` explicitly to control the CLI flag name while keeping `top_n` as the Python name.
- **`_make_stock()` lacks `perf_1m`** — The display test helper accepts specific kwargs. For `perf_1m`, just set `stock.perf_1m = value` after construction (same pattern used for `hv_percentile` and `put_premium_yield` in existing tests).
- **Zero value formatting** — `perf_1m = 0.0` should display as `0.0%` (no sign), not `+0.0%`. Use `f"{value:+.1f}%"` which gives `+3.1%`, `-5.2%`, `+0.0%` — the `+0.0%` case is acceptable or handle explicitly.

## Open Risks

- **S01 merge conflicts in test files.** S01 adds 267 lines to `test_pipeline.py` and 67 lines to `test_market_data.py`. S02 doesn't touch these files, so merge should be clean. Low risk.
- **Typer `int | None` behavior with `--top-n 0` or `--top-n -5`.** Typer will parse these as valid integers. If validation is desired, add `typer.Option(..., min=1)` or an explicit check in the handler. Per D042, this is CLI-only, so a clear error message is sufficient.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer CLI | — | none needed (simple API, well-documented, existing patterns in codebase) |
| Rich tables | — | none needed (simple API, 13-column precedent in codebase) |
| Python/pytest | — | standard tooling |

## Sources

- `git diff gsd/M002/S02..gsd/M002/S01` — confirmed S01 deliverables: `perf_1m` field (1 line in `screened_stock.py`), `compute_monthly_performance()` (17 lines in `market_data.py`), two-pass pipeline with `top_n` (84 net lines in `pipeline.py`), 334 test lines
- `scripts/run_screener.py` — CLI handler with 4 existing Typer options, `run_pipeline()` call site
- `screener/display.py` — 13-column Rich table, `fmt_pct()` formatter, `_score_style()` coloring
- `tests/test_cli_screener.py` — 5 tests demonstrating `CliRunner` + `@patch` mock pattern
- `tests/test_display.py` — `_make_stock()` helper, `_capture_console()`, column header assertions, sorted-output assertions
- `models/screened_stock.py` — dataclass with 30+ Optional fields, `from_symbol()` constructor
