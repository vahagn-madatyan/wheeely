# S02: CLI Flag + Display — Research

**Date:** 2026-03-12

## Summary

S02 adds the `--top-n` CLI flag to `run-screener` and a "Perf 1M" column to the Rich results table. This slice owns TOPN-01 (CLI flag), TOPN-05 (display column), and TOPN-06 (backward compatibility). It consumes the `perf_1m` field and `top_n` pipeline parameter from S01.

**Critical finding:** S01's code was implemented (commit `376f4de`) but has been **reverted** from `HEAD`. The current codebase has no `perf_1m` field on `ScreenedStock`, no `compute_monthly_performance()` function, and no `top_n` parameter on `run_pipeline()`. S02 must re-implement all S01 deliverables before adding its own CLI and display work. The reverted code is available in git history and provides a known-good implementation to restore.

The changes are low-risk: adding a Typer option, threading it to `run_pipeline()`, and adding a column to an existing Rich table. All patterns are well-established in the codebase.

## Recommendation

**Restore S01 code from git history, then layer S02 changes on top.** The reverted S01 code (diff between HEAD and `376f4de`) provides the exact implementation needed: `compute_monthly_performance()` in `market_data.py`, `perf_1m` field on `ScreenedStock`, `top_n` parameter on `run_pipeline()`, and the two-pass pipeline architecture. Re-apply this diff first, then add:

1. `--top-n` Typer option on the `run()` command in `scripts/run_screener.py`
2. Pass `top_n=` through to `run_pipeline()`
3. "Perf 1M" column in `render_results_table()` in `screener/display.py`
4. Tests for CLI flag parsing, display column rendering

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI argument parsing | Typer `typer.Option()` with `Annotated` type hints | Already used for `--update-symbols`, `--verbose`, `--preset`, `--config` in `run_screener.py` |
| Results table rendering | Rich `Table` with `add_column()` / `add_row()` | `render_results_table()` already renders 12 columns with formatting helpers |
| Percentage formatting | `fmt_pct()` in `screener/display.py` | Handles None→"N/A", formats as `X.X%` — exact format needed for Perf 1M |
| CLI testing | `typer.testing.CliRunner` | Already used in `test_cli_screener.py` with mock patterns established |
| Console capture for display tests | `Console(file=StringIO(), width=120)` | Pattern in `test_display.py` — inject test console, read `.file.getvalue()` |

## Existing Code and Patterns

- `scripts/run_screener.py:run()` — CLI entry point. Add `top_n` parameter following the same `Annotated[int | None, typer.Option(...)]` pattern as `preset`. Pass to `run_pipeline()` call at line ~103.
- `screener/display.py:render_results_table()` — Results table. Add "Perf 1M" column between "HV%ile" and "Yield" columns. Use `fmt_pct(stock.perf_1m)` for formatting. Sign is automatic since `fmt_pct` preserves negatives.
- `screener/pipeline.py:run_pipeline()` — Pipeline orchestrator (line 1191). S01's reverted code restructured this into a two-pass architecture with `stage1_survivors` list and sort/cap step. Restore from `376f4de`.
- `screener/market_data.py:compute_indicators()` — Indicator computation. S01 added `compute_monthly_performance()` below this function. Restore from `376f4de`.
- `models/screened_stock.py` — Add `perf_1m: Optional[float] = None` after `hv_percentile`. Restore from `376f4de`.
- `tests/test_cli_screener.py` — CLI test patterns: `@patch` decorators on module-level imports, `CliRunner.invoke(app, ["--flag"])`, assert `exit_code == 0`. Follow `test_verbose_shows_filter_breakdown` pattern for `--top-n`.
- `tests/test_display.py` — Display test patterns: `_make_stock()` helper, `_all_pass_filters()`, `_capture_console()`, check column headers in output string. Follow `test_table_has_column_headers` pattern for "Perf 1M".
- `tests/test_pipeline.py` — S01 had `TestTopNPipelineCap` class with 6 tests. Restore from `376f4de`.
- `tests/test_market_data.py` — S01 had `TestComputeMonthlyPerformance` class with 6 tests. Restore from `376f4de`.

## Constraints

- **D019 — Module-level imports for patchability:** CLI entry points use module-level imports so `@patch` targets work. New import of `run_pipeline` is already module-level.
- **D015 — Console injection for testability:** `render_results_table()` takes optional `console` parameter. No change to this pattern needed.
- **D041 — Fixed 22-day lookback:** Monthly perf uses exactly 22 trading days. Not configurable.
- **D042 — CLI-only top_n:** Not configurable per preset in YAML. CLI flag only.
- **D043 — Cap after Stage 1, before Stage 1b:** Sort/cap happens between Stage 1 cheap filters and Stage 1b earnings.
- **D044 — None perf_1m sorts last:** `float('inf')` sort key for None values.
- **Typer Option type:** Must be `int | None` with `default=None` to make the flag optional. Typer does not support bare `Optional[int]` cleanly — use `Annotated[int | None, typer.Option(...)]`.
- **345 existing tests must pass.** Restoring S01 code changes the `run_pipeline` signature (adds `top_n` kwarg with `None` default) — backward compatible since it's keyword-only with a default.

## Common Pitfalls

- **Forgetting to thread `top_n` from CLI to pipeline** — The CLI `run()` function calls `run_pipeline()` around line 103. Must add `top_n=top_n` to that call. Without it, the flag parses but does nothing.
- **Column ordering in Rich table** — "Perf 1M" should be added as a column in the right position. The `add_column` calls and `add_row` calls must stay aligned — adding a column without a matching cell in `add_row` will crash.
- **perf_1m sign display** — `fmt_pct()` shows `-3.7%` but positive values show `3.7%` not `+3.7%`. TOPN-05 says "formatted as percentage with sign (e.g. -5.2%, +3.1%)". May need a custom `fmt_pct_signed()` that prepends `+` for positive values, or modify `fmt_pct` to accept a `show_sign` flag.
- **S01 revert left no tests** — The `TestTopNPipelineCap` and `TestComputeMonthlyPerformance` test classes from S01 are also reverted. Must restore them alongside the code, or existing pipeline tests may fail due to changed function signature.
- **CliRunner captures `stdout` not `stderr`** — Error output goes to `Console(stderr=True)`. Standard `runner.invoke(app, [...]).output` captures stdout. Use `runner.invoke(app, [...], catch_exceptions=False)` pattern for debugging.

## Open Risks

- **S01 revert cause unknown** — The S01 code was reverted but the reason is unclear. The reverted code looked correct and complete. Re-applying it may encounter the same issue. Mitigated by: the code is simple, tests existed, and we can verify with `pytest` immediately after restore.
- **`fmt_pct` sign formatting gap** — TOPN-05 wants `+3.1%` for positive values. Current `fmt_pct` returns `3.1%`. Need to decide: modify `fmt_pct` (risks breaking other callers) or add a new `fmt_pct_signed()` helper. Low risk — check all `fmt_pct` callers to confirm.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer (CLI) | — | none found (no specialized skill needed — patterns well-established in codebase) |
| Rich (tables) | — | none found (no specialized skill needed — patterns well-established in codebase) |

## Sources

- Reverted S01 code at commit `376f4de` — full implementation of `compute_monthly_performance`, `perf_1m` field, `top_n` pipeline parameter, and two-pass architecture with 12 tests (source: `git diff HEAD..376f4de`)
- Existing CLI patterns in `scripts/run_screener.py` and `tests/test_cli_screener.py` (source: codebase)
- Existing display patterns in `screener/display.py` and `tests/test_display.py` (source: codebase)
