# S02: CLI Flag + Display — Research

**Date:** 2026-03-12

## Summary

S02 is a low-risk, purely additive slice that wires S01's pipeline changes (`top_n` parameter, `perf_1m` field) into the user-facing CLI and display layers. Three touch points: (1) add a `--top-n` Typer option to `scripts/run_screener.py` and pass it through to `run_pipeline()`, (2) add a "Perf 1M" column to the Rich results table in `screener/display.py`, and (3) tests for both.

The codebase has well-established patterns for both changes. The CLI already has four Typer options (`--update-symbols`, `--verbose`, `--preset`, `--config`) using `Annotated` type hints, and tests use `typer.testing.CliRunner` with heavy `@patch` decorators. The display module already has 13 table columns with formatters (`fmt_pct`, `fmt_price`, etc.) and a consistent `_capture_console()` test pattern. This slice follows existing conventions exactly — no architectural decisions needed.

**Critical dependency note:** S01's code exists on branch `gsd/M002/S01` but has NOT been merged into the current `gsd/M002/S02` branch. The S02 branch currently lacks `perf_1m` on `ScreenedStock`, `compute_monthly_performance()` in `market_data.py`, and the `top_n` parameter on `run_pipeline()`. S01 changes must be merged or cherry-picked before S02 implementation can begin.

## Targeted Requirements

| Req ID | Description | This slice's role |
|--------|-------------|-------------------|
| TOPN-01 | `--top-n N` CLI flag caps stock count after Stage 1 | **Primary owner** — adds the CLI flag and passes it to pipeline |
| TOPN-05 | "Perf 1M" column visible in Rich results table | **Primary owner** — adds column to `render_results_table()` |
| TOPN-06 | No flag = all stocks processed (backward compatible) | **Primary owner** — `top_n=None` default preserves current behavior |

## Recommendation

Follow existing patterns exactly:

1. **Merge S01 first** — Merge `gsd/M002/S01` into `gsd/M002/S02` to get the `perf_1m` field, `compute_monthly_performance()`, `top_n` pipeline parameter, and S01 tests.
2. **CLI flag** — Add `--top-n` as a `typer.Option` with `int | None` type and `None` default, matching the `--preset` Annotated pattern. Pass directly to `run_pipeline(top_n=top_n)`.
3. **Display column** — Insert "Perf 1M" column between "HV%ile" and "Yield" (line 191, logical grouping: technical indicators before options data). Create a `fmt_signed_pct()` helper for sign-prefixed formatting (e.g., `-5.2%`, `+3.1%`) — do NOT modify existing `fmt_pct()` to avoid regressing other columns.
4. **Tests** — Add to existing `test_cli_screener.py` and `test_display.py` following their exact patterns.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option definition | `typer.Option` with `Annotated` type hints | Already used for all 4 existing options; consistent API |
| Percentage formatting | `screener.display.fmt_pct()` as base | Already handles None→"N/A", consistent decimal place |
| Console capture for tests | `Console(file=StringIO(), width=120)` pattern | All 45 display tests use this; proven isolation |
| CLI test runner | `typer.testing.CliRunner` | All 5 CLI tests use this; captures output + exit code |

## Existing Code and Patterns

- `scripts/run_screener.py:run()` lines 56-72 — CLI entry point with 4 existing Typer options using `Annotated[..., typer.Option(...)]` pattern. Add `top_n` parameter here. Pass to `run_pipeline()` call on line 119.
- `scripts/run_screener.py` line 119 — `run_pipeline()` call site. Currently passes `trade_client`, `stock_client`, `finnhub`, `cfg`, `on_progress`, `option_client`. Add `top_n=top_n`.
- `screener/display.py` lines 181-193 — 13 column definitions: `#, Symbol, Price, AvgVol, MktCap, D/E, Margin, Growth, RSI, HV%ile, Yield, Score, Sector`. Insert "Perf 1M" at line 191 (after HV%ile, before Yield).
- `screener/display.py` lines 195-215 — Row construction loop. Add `perf_1m` formatted value in matching position.
- `screener/display.py:fmt_pct()` — Returns `f"{value:.1f}%"` or `"N/A"`. No `+` prefix for positive values. Need separate `fmt_signed_pct()`.
- `tests/test_cli_screener.py` — 5 tests using `CliRunner` with `@patch` decorators targeting `scripts.run_screener.*` (D019 module-level import pattern). `test_default_no_file_writes` is the primary template for verifying pipeline call arguments.
- `tests/test_display.py:_make_stock()` — Helper builds `ScreenedStock` with specific fields. Must add `perf_1m` kwarg for new tests.
- `tests/test_display.py:_all_pass_filters()` — Returns filter list with 11 filter names. Used by all passing-stock tests.
- `models/screened_stock.py` line 40 (S01 branch) — `perf_1m: Optional[float] = None` field exists after S01 merge.
- `screener/pipeline.py` line 1199 (S01 branch) — `top_n: int | None = None` parameter exists after S01 merge.

## Constraints

- **S01 merge required** — Current branch lacks `perf_1m` field, `compute_monthly_performance()`, and `top_n` pipeline parameter. Must merge `gsd/M002/S01` before any S02 code changes.
- **Column/row positional coupling** — Rich Table `add_column()` and `add_row()` are positionally coupled. The new column at position 11 (0-indexed, after HV%ile) requires the new value at position 11 in every `add_row()` call. Currently only one `add_row()` call exists (line 202).
- **`fmt_pct()` lacks sign prefix** — `fmt_pct(3.1)` returns `"3.1%"` (no plus). TOPN-05 specifies `+3.1%`. Create a new `fmt_signed_pct()` to avoid regressing HV%ile, Yield, Margin, Growth, RSI columns that all use `fmt_pct()`.
- **Typer `int | None` default** — `typer.Option` with `None` default requires `Annotated[int | None, typer.Option("--top-n", ...)] = None`. The existing `PresetName | None` on line 67 confirms this pattern works.
- **Backward compatibility (TOPN-06)** — `top_n=None` must produce identical behavior. Tests must verify `run_pipeline` called without `top_n` when flag omitted.
- **345 existing tests** — All must continue passing after S02 changes plus S01 merge.

## Common Pitfalls

- **Column/row positional mismatch** — Adding a column without the matching value in `add_row()` (or at the wrong position) shifts all subsequent columns. Count: new column is #11 (after HV%ile at #10, before Yield at current #11). The `add_row()` currently has 13 values (positions 0-12); new value goes at position 10 (after `hv_pct_str`).
- **Patching `run_pipeline` in CLI tests** — Mock target must be `scripts.run_screener.run_pipeline` (not `screener.pipeline.run_pipeline`) because the CLI uses module-level imports (D019). Same for any new imports.
- **Typer `None` default serialization** — When `--top-n` is not passed, Typer delivers `None` to the function. The test must verify `run_pipeline` is called with `top_n=None` (not that `top_n` kwarg is absent).
- **Modifying `fmt_pct` globally** — Tempting but dangerous. `fmt_pct` is used by 5 columns (Margin, Growth, RSI, HV%ile, Yield). Adding `+` prefix would change all of them. Use a dedicated `fmt_signed_pct()` for Perf 1M only.

## Open Risks

- **S01 merge conflicts** — S01 modifies `pipeline.py` extensively (two-pass refactor), `screened_stock.py` (new field), `market_data.py` (new function), and adds to `tests/test_pipeline.py`. Merge into S02 branch could conflict if the S02 branch has diverged. Risk is low since S02 branch has only `.gsd/` file changes, no code changes.
- **Sign formatting decision** — TOPN-05 says "Formatted as percentage with sign (e.g. -5.2%, +3.1%)". Creating `fmt_signed_pct()` is the safest approach. If we decide `0.0%` should show as `+0.0%` or `0.0%` (no sign), this is a minor detail to settle during implementation.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer CLI | `narumiruna/agent-skills@python-cli-typer` (13 installs) | available — low value for single option addition |
| Rich tables | none found | n/a — existing codebase patterns are sufficient |
| Python testing | none relevant found | n/a — existing test patterns well-established |

No skills recommended for installation — the codebase has clear, repeatable patterns for both CLI options and display columns that are more authoritative than generic skills.

## Sources

- `scripts/run_screener.py` — existing CLI structure with 4 Typer options (lines 56-72)
- `screener/display.py` — existing table with 13 columns and formatter functions (lines 181-215)
- `tests/test_cli_screener.py` — 5 existing CLI tests with CliRunner + @patch pattern
- `tests/test_display.py` — 45 existing display tests with console capture pattern
- `git show gsd/M002/S01:screener/pipeline.py` — S01 two-pass refactor, `top_n` parameter at line 1199
- `git show gsd/M002/S01:models/screened_stock.py` — `perf_1m: Optional[float]` field at line 40
- `git show gsd/M002/S01:screener/market_data.py` — `compute_monthly_performance()` function (22-day lookback)
- `.gsd/DECISIONS.md` — D041 (22-day lookback), D042 (CLI-only), D043 (cap placement), D044 (None sorts last)
