# S02: CLI Flag + Display — Research

**Date:** 2026-03-12

## Summary

S02 wires the S01 pipeline internals to user-visible surfaces: a `--top-n` CLI flag on `run-screener` and a "Perf 1M" column in the Rich results table. S01 code lives on branch `gsd/M002/S01` and must be merged into the current `gsd/M002/S02` branch before S02 implementation begins — S01 adds the `perf_1m` field on `ScreenedStock`, `compute_monthly_performance()` in `market_data.py`, and the `top_n` parameter + two-pass architecture in `run_pipeline()`.

The S02 implementation touches exactly three source files (`scripts/run_screener.py`, `screener/display.py`, and a new or existing test file) with well-established patterns. Both CLI and display changes are purely additive — no existing behavior changes. 345 tests pass on the current branch and should remain green.

One formatting nuance: TOPN-05 requires explicit sign on "Perf 1M" values (`-5.2%`, `+3.1%`). The existing `fmt_pct()` helper produces `"3.1%"` for positive values (no `+`). A new `fmt_pct_signed()` helper or inline `f"{value:+.1f}%"` with `None` guard handles this.

## Recommendation

1. **Merge S01 branch** — `git merge gsd/M002/S01` into `gsd/M002/S02`. S01 delivers: `perf_1m` field on `ScreenedStock`, `compute_monthly_performance()`, `run_pipeline(top_n=)`, and 12 new tests. The merge should be conflict-free: S01 only modified `pipeline.py`, `market_data.py`, `screened_stock.py`, and test files — no overlap with S02 targets (`run_screener.py`, `display.py`).
2. **Add `--top-n` CLI option** — Follow the existing `Annotated[..., typer.Option(...)]` pattern in `run_screener.py`. Pass through to `run_pipeline(top_n=top_n)`. Use `min=1` (confirmed working in Typer 0.24.1).
3. **Add "Perf 1M" column** — Insert between "HV%ile" and "Yield" in `render_results_table()`. Use a signed-percent formatter (`f"{value:+.1f}%"`).
4. **Test both surfaces** — CLI flag test via `typer.testing.CliRunner` with `@patch` stack; display column test via `Console(file=StringIO())` capture. Follow `test_cli_screener.py` and `test_options_chain.py:TestDisplayYieldColumn` patterns respectively.

## Requirements Owned by This Slice

| Requirement | Role | What S02 Must Deliver |
|-------------|------|-----------------------|
| TOPN-01 | primary | `--top-n N` CLI flag that passes through to `run_pipeline(top_n=N)` |
| TOPN-05 | primary | "Perf 1M" column in Rich results table with signed percentage format |
| TOPN-06 | primary | No flag = `top_n=None` = all stocks processed (backward compatible) |

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option parsing | `typer.Option` with `Annotated` type hints | Already used for `--verbose`, `--preset`, `--config`, `--update-symbols` — consistent pattern |
| Table rendering | `rich.table.Table` with `add_column` / `add_row` | Already used for 13 columns in `render_results_table()` |
| Number formatting | `fmt_pct()` in `screener/display.py` | Handles `None → "N/A"` and `%.1f%`; extend with signed variant |
| CLI testing | `typer.testing.CliRunner` + `@patch` stack | Used in all 5 existing CLI tests in `test_cli_screener.py` |
| Display testing | `Console(file=StringIO(), width=200)` capture | Used in `test_options_chain.py:TestDisplayYieldColumn` |

## Existing Code and Patterns

- `scripts/run_screener.py:55-73` — CLI option pattern: `Annotated[type | None, typer.Option("--flag", help="...")]` with default `= None` or `= False`. S02's `--top-n` follows this exactly.
- `scripts/run_screener.py:119-126` — `run_pipeline()` call site. S02 adds `top_n=top_n` kwarg. Currently passes `trade_client`, `stock_client`, `finnhub`, `cfg`, `on_progress`, `option_client`.
- `screener/display.py:169-193` — Column definitions in `render_results_table()`. 13 columns: `#, Symbol, Price, AvgVol, MktCap, D/E, Margin, Growth, RSI, HV%ile, Yield, Score, Sector`. S02 inserts "Perf 1M" after "HV%ile" (index 10) and before "Yield".
- `screener/display.py:195-215` — Row construction via `add_row()`. S02 adds `perf_1m` formatted value at the corresponding position (between `hv_pct_str` and `yield_str`).
- `screener/display.py:107-118` — `fmt_pct()` helper: `f"{value:.1f}%"` or `"N/A"`. Produces `"3.1%"` for positive values (NO `+` sign). S02 needs a `fmt_pct_signed()` variant using `f"{value:+.1f}%"`.
- `tests/test_cli_screener.py:36-74` — `test_default_no_file_writes`: canonical CLI test — patches 8 dependencies, invokes via `CliRunner`, asserts `run_pipeline` was called. S02 follows this pattern, asserting `top_n=20` in `call_args.kwargs`.
- `tests/test_display.py:30-57` — `_make_stock()` helper: creates `ScreenedStock` with keyword fields. Does NOT accept `perf_1m` — set `stock.perf_1m = value` directly after creation (matching `test_options_chain.py` approach).
- `tests/test_display.py:60-66` — `_all_pass_filters()`: returns passing `FilterResult` list. Reuse as-is.
- `tests/test_options_chain.py:634-680` — `TestDisplayYieldColumn`: display test pattern for a column added by a later slice. Creates stock, appends filter result, renders table to `StringIO`, asserts column header and value in output. **Exact pattern for "Perf 1M" column test.**

## Constraints

- **S01 must be merged first.** `perf_1m` field, `compute_monthly_performance()`, and `run_pipeline(top_n=)` all live on branch `gsd/M002/S01`. Without merge, any reference to these will error. Confirmed: current S02 branch `pipeline.py` has no `top_n` param and `screened_stock.py` has no `perf_1m` field.
- **`top_n` type: `int | None`, default `None`.** Per D042, `None` = no cap (backward compatible, TOPN-06). Typer 0.24.1 handles this natively.
- **`top_n` must be ≥ 1 when set.** `typer.Option(min=1)` confirmed working: `--top-n 0` produces `"Invalid value ... 0 is not in the range x>=1"` with exit code 2.
- **Column position: "Perf 1M" between "HV%ile" and "Yield".** Both `add_column()` and `add_row()` must align. Currently 13 columns → becomes 14. Mismatch causes silent misalignment.
- **Signed format for Perf 1M.** TOPN-05 specifies `-5.2%`, `+3.1%`. Python `f"{value:+.1f}%"` produces this. For `None`, return `"N/A"`.
- **345 existing tests must pass.** S02 changes are additive — no existing function signatures change.

## Common Pitfalls

- **Column/row position mismatch** — Adding `add_column("Perf 1M")` at one index but inserting the value in `add_row()` at a different index silently misaligns the entire table right of that point. Count carefully: both must be at index 10 (after HV%ile).
- **Using `fmt_pct()` directly for Perf 1M** — `fmt_pct(-5.2)` → `"-5.2%"` (correct), but `fmt_pct(3.1)` → `"3.1%"` (missing `+`). Need a signed variant.
- **Not asserting `top_n` passthrough in CLI test** — The key test must verify that `run_pipeline` receives `top_n=20` when `--top-n 20` is passed. Check `mock_pipeline.call_args.kwargs['top_n']`.
- **`_make_stock()` helper in `test_display.py` lacks `perf_1m`** — Set `stock.perf_1m = value` directly after creation rather than extending the helper (simpler, matches `test_options_chain.py` precedent).
- **Forgetting `--help` text assertion** — The `test_screener_help` test asserts all option names appear in help output. Need to add `--top-n` assertion or the test will pass but coverage is incomplete.

## Open Risks

- **S01 merge conflicts** — Low probability. S01 modified `pipeline.py` (refactored loop), `market_data.py` (added function), `screened_stock.py` (added field), and test files. None overlap with S02's targets (`run_screener.py`, `display.py`). Only risk: if `run_screener.py` diverged on S01, but S01's diff shows no changes to that file.
- **`render_stage_summary` doesn't show top-N cap line** — When `top_n` is active, the count drops between Stage 1 and Earnings due to the cap, but the summary panel doesn't label this. Not in requirements — acceptable to defer. Users may notice the unexplained gap.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer | N/A | Standard pattern already in codebase — no specialized skill needed |
| Rich | N/A | `Table.add_column` pattern already established — no skill needed |
| Alpaca | N/A | No Alpaca API changes in S02 |

No skills to install — all technologies have well-established patterns in the codebase.

## Sources

- S01 branch diff (`git diff cd062474..gsd/M002/S01 -- '*.py'`): 5 files, +407/-29 lines. Confirmed `perf_1m` field, `compute_monthly_performance()`, `run_pipeline(top_n=)`, two-pass architecture, and new tests.
- `scripts/run_screener.py` — CLI option patterns and `run_pipeline()` call site (lines 55-126)
- `screener/display.py` — column definitions, row construction, formatter helpers (lines 107-215)
- `tests/test_cli_screener.py` — 5 CLI tests using `CliRunner` + `@patch` stack pattern
- `tests/test_display.py` — 17 display tests with `_make_stock()` helper and `Console(file=StringIO())` capture
- `tests/test_options_chain.py:634-680` — `TestDisplayYieldColumn` as precedent for column-addition display tests
- Typer 0.24.1 `Option(min=1)` — confirmed via live test: `int | None` with `min=1` works correctly (None when omitted, validates ≥1 when set)
- Test collection: 345 tests pass on current `gsd/M002/S02` branch
