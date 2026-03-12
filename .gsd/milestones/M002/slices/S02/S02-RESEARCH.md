# S02: CLI Flag + Display — Research

**Date:** 2026-03-11

## Summary

S02 is a low-risk wiring slice. S01's code lives on branch `gsd/M002/S01` (not yet merged to `gsd/M002/S02`) and delivers all heavy lifting: `compute_monthly_performance()` in `screener/market_data.py`, `perf_1m: Optional[float]` on `ScreenedStock`, the two-pass pipeline architecture with `run_pipeline(top_n=N)`, sort/cap logic, and 12 new tests (6 math + 6 pipeline). A dry-run merge shows 0 conflicts — 5 files changed, 407 insertions, 29 deletions.

S02 must merge S01 first, then add three things: a `--top-n` Typer option in `scripts/run_screener.py` that passes through to `run_pipeline(top_n=N)`, a "Perf 1M" column in `screener/display.py:render_results_table()`, and tests for both. All three target files have clear, established patterns. No new libraries, no new API calls, no new patterns to invent.

## Recommendation

1. **Merge S01 branch** — `git merge gsd/M002/S01` into the S02 branch. 0 conflicts confirmed via `git merge-tree`. Brings `perf_1m` field, `compute_monthly_performance()`, `run_pipeline(top_n=)`, and 12 tests (total goes from 345 → 357).
2. **Add `--top-n` CLI option** — Single `Annotated[int | None, typer.Option()]` in `run()`, passed as `top_n=top_n` to `run_pipeline()`. Follows the exact pattern of `--verbose`, `--preset`, `--config`.
3. **Add "Perf 1M" column** — Insert into `render_results_table()` between "HV%ile" and "Yield". Use a signed percentage formatter (`f"{value:+.1f}%"`) since `fmt_pct()` omits the `+` sign on positives. Either add a small `fmt_signed_pct()` helper or inline the logic.
4. **Tests** — CLI: verify `--top-n` flag is parsed and passed to `run_pipeline()`. Display: verify "Perf 1M" column appears, handles `None` → `N/A`, shows `+`/`-` sign.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option parsing | `typer.Option` with `Annotated` | Used for all 4 existing flags in `run_screener.py` |
| Table rendering | `rich.table.Table` | Already used in `render_results_table()` |
| Percentage formatting | `fmt_pct()` in `screener/display.py` | Handles `None` → `"N/A"` and decimals; extend for `+` sign |
| CLI testing | `typer.testing.CliRunner` | Used in `tests/test_cli_screener.py` (5 tests) |
| Console capture | `Console(file=StringIO())` | Used in `tests/test_display.py` (35 tests) |

## Existing Code and Patterns

- `scripts/run_screener.py:run()` — CLI entry point. Uses `Annotated[type, typer.Option()]` for all options. `run_pipeline()` call at line ~119 needs `top_n=top_n` kwarg added. No new imports needed beyond the option itself.
- `screener/display.py:render_results_table()` — Table builder. 13 columns currently: `#, Symbol, Price, AvgVol, MktCap, D/E, Margin, Growth, RSI, HV%ile, Yield, Score, Sector`. Insert "Perf 1M" between HV%ile and Yield. Each column is a `table.add_column()` call; each row uses positional `table.add_row()` args.
- `screener/display.py:fmt_pct()` — Formats `float | None` as `"X.X%"` / `"N/A"`. Does NOT prefix `+` for positive values. For perf_1m, positive values should show `+3.1%` to visually distinguish gains from losses — needs a `fmt_signed_pct()` or inline `f"{value:+.1f}%"`.
- `tests/test_cli_screener.py` — 5 tests using `CliRunner` + `@patch`. Pattern: patch all external deps at `scripts.run_screener.X`, invoke with `runner.invoke(app, [...])`, assert exit code and mock calls. The `test_default_no_file_writes` test patches `run_pipeline` and asserts `called_once` — new test should verify `top_n` kwarg is passed through.
- `tests/test_display.py` — 35 tests. `_make_stock()` helper creates `ScreenedStock` with kwargs. `_all_pass_filters()` creates passing `FilterResult` list. `_capture_console()` returns `Console(file=StringIO(), width=120)`. Test pattern: render to captured console, check `console.file.getvalue()` for expected strings.
- `models/screened_stock.py` — `perf_1m: Optional[float] = None` added by S01 (on branch). Located after `hv_percentile` in Technical indicators section.
- `screener/pipeline.py` — S01 adds `top_n: int | None = None` parameter. Two-pass architecture: Pass 1 computes indicators + `perf_1m` + Stage 1 filters. Sort/cap. Pass 2 runs Stage 1b/2/3 only for capped survivors.

## Constraints

- **S01 must be merged first** — `perf_1m` field, `compute_monthly_performance()`, and `run_pipeline(top_n=)` all live on branch `gsd/M002/S01`. Without merging, there's nothing to wire to.
- **`top_n` must default to `None`** — D042 and TOPN-06 require backward compatibility. When omitted, all stocks process through the full pipeline (no cap).
- **`top_n` must be a positive integer** — Typer's `int` type handles basic parsing. A `min=1` validation via `typer.Option(min=1)` is available.
- **Column insertion order is positional** — Rich table `add_column`/`add_row` are positional. Adding "Perf 1M" between existing columns means updating the `add_row()` call to include the value at the right position.
- **345 existing tests must still pass** — S01 brings it to 357. S02 adds more. All must pass.
- **`_make_stock()` helper in test_display.py doesn't have `perf_1m`** — Tests that need it will set `stock.perf_1m = X` directly after `_make_stock()`, or the helper can gain the kwarg.

## Common Pitfalls

- **Forgetting to merge S01** — The current `gsd/M002/S02` branch has no `perf_1m`, `top_n`, or `compute_monthly_performance()`. Must merge before coding.
- **`fmt_pct()` drops `+` sign** — `fmt_pct(3.1)` → `"3.1%"` not `"+3.1%"`. For perf_1m clarity, positive values need explicit `+`. Use `f"{value:+.1f}%"` in a `fmt_signed_pct()` helper.
- **Patching `run_pipeline` in CLI tests** — Must patch at `scripts.run_screener.run_pipeline`, not `screener.pipeline.run_pipeline` (D019 pattern — module-level imports).
- **`add_row()` arg count mismatch** — Adding a column to the table requires adding a corresponding value in every `add_row()` call. Miss one → Rich raises.
- **`test_table_has_column_headers` assertion** — This test checks column names in output. Adding "Perf 1M" won't break it (checks known columns exist, not absence of others), but a new assertion for "Perf 1M" should be added.

## Open Risks

- **`top_n=0` edge case** — User passes `--top-n 0`, pipeline caps to 0 stocks (empty results). Mitigate with `typer.Option(min=1)` or a guard in the CLI handler. Low risk — user error.
- **Stage summary panel** — `render_stage_summary()` currently counts Stage 1 survivors, but with top_n cap, stocks that pass Stage 1 but are capped out have no Stage 1b/2/3 filter results. The summary should still be accurate (it counts filter_results, and capped-out stocks won't have those results — they just won't be counted in later stages). Verify after implementation.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer CLI | — | none found (simple usage, no skill needed) |
| Rich tables | — | none relevant (trivial column addition) |

## Sources

- S01 branch diff (`git diff gsd/M002/S02..gsd/M002/S01`) — confirmed all S01 deliverables: `perf_1m` field, `compute_monthly_performance()`, `run_pipeline(top_n=)`, 12 tests across 5 files
- Merge feasibility: `git merge-tree` — 0 conflicts, clean merge
- Existing code reads: `scripts/run_screener.py`, `screener/display.py`, `tests/test_cli_screener.py`, `tests/test_display.py`, `models/screened_stock.py` — confirmed patterns for CLI options, table columns, test approaches
- Test baseline: 345 tests pass on current branch (`pytest -q`)
