# S02: CLI Flag + Display — Research

**Date:** 2026-03-12

## Summary

S02 adds the `--top-n` CLI flag to `run-screener` and a "Perf 1M" column to the Rich results table. This slice owns TOPN-01 (CLI flag), TOPN-05 (display column), and TOPN-06 (backward compatibility).

**Critical finding:** S01's code exists on branch `gsd/M002/S01` (commits `815541d` for T01 and `94af363` for T02) but was never merged into the current branch `gsd/M002/S02`. The current HEAD has no `perf_1m` field on `ScreenedStock`, no `compute_monthly_performance()` function, and no `top_n` parameter on `run_pipeline()`. S02 must merge or cherry-pick S01's work before adding its own CLI and display changes. The S01 diff is clean and well-tested (6 market_data tests + 6 pipeline tests).

The S02-specific changes are low-risk: one Typer option, one kwarg pass-through, one table column, and one formatting helper. All patterns are established in the codebase with 345 passing tests as baseline.

## Recommendation

**Cherry-pick or merge S01 branch, then layer S02 changes on top.**

The S01 branch (`gsd/M002/S01`) contains exactly two implementation commits:
1. `815541d` — `compute_monthly_performance()` in `market_data.py`, `perf_1m` field on `ScreenedStock`, 6 tests in `test_market_data.py`
2. `94af363` — Two-pass pipeline refactor with `top_n` parameter, sort/cap logic, 6 tests in `test_pipeline.py`

After S01 code is present, S02 adds:
1. `--top-n` Typer option on `run()` in `scripts/run_screener.py`
2. Pass `top_n=top_n` to `run_pipeline()` call
3. `fmt_pct_signed()` helper in `screener/display.py` for `+3.1%` / `-5.2%` formatting
4. "Perf 1M" column in `render_results_table()` using the new helper
5. Tests for CLI flag parsing, display column, and signed formatting

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI argument parsing | `Annotated[T, typer.Option()]` pattern in `run_screener.py` | Used for `--verbose`, `--preset`, `--config` — same pattern for `--top-n` |
| Results table rendering | Rich `Table` with `add_column()` / `add_row()` in `render_results_table()` | 12 columns already rendered; add one more in same pattern |
| Percentage formatting | `fmt_pct()` in `screener/display.py` | Handles None→"N/A", formats as `X.X%` — but needs sign-aware variant for perf |
| CLI testing | `typer.testing.CliRunner` + `@patch` stack | `test_verbose_shows_filter_breakdown` is exact template to follow |
| Console capture | `Console(file=StringIO(), width=120)` in `test_display.py` | `_capture_console()` helper already exists |

## Existing Code and Patterns

- **`scripts/run_screener.py:run()`** (line 49) — CLI entry point. Add `top_n` parameter as `Annotated[int | None, typer.Option("--top-n", ...)]` following the `preset` parameter pattern. Pass to `run_pipeline()` call at line ~103 as `top_n=top_n`.
- **`screener/display.py:render_results_table()`** (line 154) — Results table. Has 12 columns (# through Sector). Add "Perf 1M" column. Column and row additions must stay aligned — each `add_column` needs matching positional arg in `add_row`.
- **`screener/display.py:fmt_pct()`** (line 108) — Returns `f"{value:.1f}%"`. Does NOT prepend `+` for positive values. TOPN-05 specifies `+3.1%` format. Add a new `fmt_pct_signed()` rather than modifying `fmt_pct` (6 existing callers depend on current behavior).
- **`tests/test_cli_screener.py`** — CLI tests use `@patch("scripts.run_screener.X")` decorator stacks. The `test_verbose_shows_filter_breakdown` test is the exact template: patches all dependencies, passes a CLI flag, asserts the flag triggered the right behavior.
- **`tests/test_display.py:_make_stock()`** — Helper builds `ScreenedStock` with selective fields. Does not accept `perf_1m` kwarg yet — needs to be extended or set directly on the object.
- **`tests/test_display.py:TestRenderResultsTable`** — 7 tests verify table output. `test_table_has_column_headers` checks column names in captured output — add "Perf 1M" to the assertion list.

## Constraints

- **D019 — Module-level imports for patchability:** `run_pipeline` is already imported at module level in `run_screener.py`. No change needed.
- **D015 — Console injection for testability:** `render_results_table()` accepts optional `console` parameter. Display tests use `_capture_console()`.
- **D042 — CLI-only top_n:** Not stored in presets or YAML config. Pure CLI flag with `None` default.
- **D044 — None perf_1m sorts last:** S01 handles this with `float('inf')` sort key in pipeline. Display just shows "N/A".
- **Typer `int | None` type:** Must use `Annotated[int | None, typer.Option("--top-n", ...)]` with `default=None`. Typer handles this correctly — `None` when flag omitted, `int` when provided.
- **345 existing tests must pass.** The `run_pipeline` signature change (adding `top_n` kwarg) is backward-compatible since it's keyword-only with `None` default.
- **Column/row alignment:** Rich `Table` requires the number of positional args in `add_row()` to match the number of `add_column()` calls. Adding "Perf 1M" column means adding one value to every `add_row()` call.

## Common Pitfalls

- **Forgetting to thread `top_n` from CLI to pipeline** — The `run()` function calls `run_pipeline()` around line 103. Must add `top_n=top_n` kwarg. Without it, the flag parses but does nothing.
- **Column/row count mismatch in Rich table** — Adding `add_column("Perf 1M", ...)` without adding a matching positional arg in the `add_row(...)` call will crash at render time. There are 13 positional args in the current `add_row` — adding one makes 14.
- **`fmt_pct` doesn't show `+` sign** — `fmt_pct(3.1)` → `"3.1%"` not `"+3.1%"`. TOPN-05 wants signed display. Modifying `fmt_pct` would break existing callers (net_margin, sales_growth, RSI, HV%ile, yield all use it and should NOT show `+`). Add a separate `fmt_pct_signed()`.
- **`_make_stock` helper in tests lacks `perf_1m`** — Existing `_make_stock()` doesn't accept `perf_1m`. Tests can set it directly: `stock.perf_1m = -5.2` after construction. Or extend the helper.
- **S01 branch divergence** — `gsd/M002/S01` branched from the same base as `gsd/M002/S02`. Both branches have only added files/changes — no conflicts expected on merge. But verify with `git merge --no-commit` first.

## Open Risks

- **S01 merge may need conflict resolution** — The S01 and S02 branches both auto-committed `.gsd/` files that may conflict on merge. Source code changes (`.py` files) should merge cleanly since S02 hasn't touched `pipeline.py`, `market_data.py`, or `screened_stock.py`. Mitigated by: cherry-picking the two implementation commits (`815541d`, `94af363`) instead of merging the full branch.
- **`fmt_pct_signed` for zero** — Should `0.0%` show as `+0.0%` or plain `0.0%`? Financial convention is usually `0.0%` without sign. Decide during implementation; low risk either way.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer (CLI) | `narumiruna/agent-skills@python-cli-typer` | available (13 installs) — not needed, patterns established in codebase |
| Rich (tables) | — | none found — not needed, patterns established in codebase |

## Sources

- S01 implementation: branch `gsd/M002/S01`, commits `815541d` (T01: compute_monthly_performance + perf_1m field + 6 tests) and `94af363` (T02: two-pass pipeline + top_n + 6 tests)
- Existing CLI patterns: `scripts/run_screener.py` and `tests/test_cli_screener.py` (4 tests)
- Existing display patterns: `screener/display.py` and `tests/test_display.py` (29 tests)
- Formatting analysis: `fmt_pct()` has 6 callers (net_margin, sales_growth, rsi_14, hv_percentile, put_premium_yield, perf display) — cannot add `+` sign without breaking existing behavior
