# S02: CLI Flag + Display — Research

**Date:** 2026-03-12

## Summary

S02 adds three surface-level features: a `--top-n` Typer CLI option on `run-screener`, a "Perf 1M" column in the Rich results table, and tests for both. All three consume S01 deliverables (`run_pipeline(top_n=N)` parameter, `ScreenedStock.perf_1m` field).

**Critical finding:** S01 was marked complete but its code was never committed. The `ScreenedStock` dataclass has no `perf_1m` field, `run_pipeline` has no `top_n` parameter, and `compute_indicators` has no monthly performance computation. S02 implementation must either (a) implement S01's code changes inline as prerequisites, or (b) block until S01 is re-executed. The S01-SUMMARY.md is a doctor-created placeholder that explicitly warns its content is incomplete.

The S02-specific work itself is low-risk and mechanical — Typer option wiring, one table column addition, and straightforward tests following well-established patterns in the codebase.

## Recommendation

**Implement S01's missing code changes as prerequisite tasks within S02**, then layer the CLI and display work on top. The S01 scope is small (one dataclass field, one computation, one sort/cap block in pipeline) and well-defined by the roadmap. Treating them as S02 prerequisites avoids a blocking dependency on a re-run of S01 while keeping the work self-contained.

Task ordering:
1. Add `perf_1m: Optional[float] = None` to `ScreenedStock` (S01 prerequisite)
2. Add monthly perf computation in `compute_indicators()` or as standalone function (S01 prerequisite)
3. Populate `perf_1m` in `run_pipeline` Step 4 and add `top_n` parameter with sort/cap logic (S01 prerequisite)
4. Add `--top-n` Typer option to `run_screener.py` and pass through to `run_pipeline` (S02 proper — TOPN-01, TOPN-06)
5. Add "Perf 1M" column to `render_results_table()` (S02 proper — TOPN-05)
6. Tests for all new functionality

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option parsing | `typer.Option` with `Annotated` | Already used for all other flags in `run_screener.py` |
| Rich table column | `table.add_column()` + `fmt_pct()` | Exact pattern used for HV%ile and Yield columns |
| CLI test harness | `typer.testing.CliRunner` | Already used in `test_cli_screener.py` with mock patterns |
| Console capture for display tests | `Console(file=StringIO(), width=120)` | Already used in `test_display.py` |

## Existing Code and Patterns

- `scripts/run_screener.py` — Typer app with `@app.command()` decorator. Options use `Annotated[type, typer.Option(...)]` pattern. All patches in tests target `scripts.run_screener.<name>` (D019 module-level import pattern). **Add `--top-n` here.**
- `screener/display.py:render_results_table()` — Builds Rich `Table` with columns added via `table.add_column()`. Formatting helpers (`fmt_pct`, `fmt_large_number`) handle None → "N/A". HV%ile and Yield columns (lines 190-200) are the exact pattern for Perf 1M. **Add "Perf 1M" column after "HV%ile" or before "Yield".**
- `screener/pipeline.py:run_pipeline()` — Current signature has no `top_n`. The sort/cap insertion point is between Step 4 (build stocks + indicators) and Step 5 (filter stages), specifically after Stage 1 filters pass but before Stage 1b earnings calls (line ~1270). **S01 prerequisite: add `top_n=None` parameter and sort/cap logic.**
- `models/screened_stock.py:ScreenedStock` — Dataclass with `Optional[float]` fields. **S01 prerequisite: add `perf_1m: Optional[float] = None`.**
- `screener/market_data.py:compute_indicators()` — Returns dict with price, avg_volume, rsi_14, sma_200, above_sma200. Uses `bars_df["close"]`. **S01 prerequisite: add `perf_1m` key using `close[-1] / close[-22] - 1` when len(close) >= 22.**
- `tests/test_cli_screener.py` — 4 existing tests: help, default run, verbose flag, config error. Uses heavy `@patch` stacking on `scripts.run_screener.*` imports. `test_default_no_file_writes` is the template for a `--top-n` passthrough test.
- `tests/test_display.py` — 30+ tests covering formatters, score styling, results table, stage summary, filter breakdown. `TestRenderResultsTable` tests column headers, row count, sort order. **Add Perf 1M to column header assertions and stock fixture.**
- `tests/test_pipeline.py` — Tests for pipeline functions. **Add sort/cap tests here.**
- `tests/test_market_data.py` — Tests for `compute_indicators`. **Add perf_1m computation tests here.**

## Constraints

- **S01 code is missing**: `perf_1m` field, `top_n` parameter, and monthly perf computation must be implemented before S02 work can begin. The doctor placeholder summary confirms this gap.
- **`top_n` is a positive integer or None** (D042): No default cap when flag is omitted; `None` means process all stocks (backward compatible per TOPN-06).
- **Sort/cap placement** (D043): After Stage 1 (all Alpaca-based filters) but before Stage 1b (Finnhub earnings) — this is between the `stage1_passed` check and the `earnings_for_symbol` call in the pipeline loop.
- **None perf_1m sorts last** (D044): Stocks with insufficient bar data sort to end of list, not dropped.
- **Monthly perf lookback is fixed at ~22 trading days** (D041): `close[-1] / close[-22] - 1`, yielding percentage (e.g., -5.2 for 5.2% decline per TOPN-04).
- **Perf 1M display format** (TOPN-05): Percentage with sign (e.g., "-5.2%", "+3.1%"). `fmt_pct()` already handles this for negative values but doesn't add "+" prefix for positives — may need a `fmt_signed_pct()` or inline format.
- **Module-level imports required** (D019): The `--top-n` flag value must reach `run_pipeline` through the existing call chain, not via new imports in the function body.
- **345 existing tests must continue passing**: No regressions allowed.

## Common Pitfalls

- **`fmt_pct` doesn't add "+" prefix** — TOPN-05 specifies format like "+3.1%". Either add a new `fmt_signed_pct()` helper or use inline `f"{'+' if v > 0 else ''}{v:.1f}%"`. Don't modify `fmt_pct` itself as it's used elsewhere without sign prefix.
- **Pipeline loop sort/cap is outside the per-symbol loop** — The sort/cap must happen after ALL symbols complete Stage 1, not inside the per-symbol iteration. Current pipeline iterates symbols sequentially; sort/cap must collect Stage 1 survivors first, then sort and cap before re-entering the loop for Stage 1b+. This likely requires restructuring the single loop into two passes (or collecting survivors into a separate list).
- **`_make_stock` helper in test_display.py lacks `perf_1m`** — Adding the field to `ScreenedStock` won't break existing tests (default None), but display tests asserting column headers will need updating to include "Perf 1M".
- **Typer `int | None` type for `--top-n`** — Must use `Optional[int]` with `default=None`. Typer 0.24.1 handles this correctly with `Annotated[int | None, typer.Option(...)]`.
- **`top_n=0` edge case** — Should be treated as "no cap" or raise an error. Negative values too. Add validation (e.g., `top_n >= 1` or None).

## Open Risks

- **Pipeline loop restructuring complexity**: The current `run_pipeline` iterates symbols once, running all stages per symbol. Inserting a sort/cap between Stage 1 and Stage 1b requires collecting all Stage 1 results first, then selecting the top N, then running Stage 1b+ only on those N. This is a structural change to the loop, not a simple insertion. The approach is sound but the implementation touches ~40 lines of pipeline orchestration.
- **S01 placeholder summary may mask other issues**: The doctor summary warns it's incomplete. If S01 had other deliverables beyond what the roadmap boundary map specifies (e.g., additional test fixtures or shared helpers), they won't be discovered until implementation.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer CLI | `0xdarkmatter/claude-mods@python-cli-patterns` (29 installs) | available — not needed; patterns are clear from existing code |
| Rich tables | N/A | none found — not needed; existing `test_display.py` provides complete patterns |

## Sources

- Codebase exploration: `scripts/run_screener.py`, `screener/display.py`, `screener/pipeline.py`, `models/screened_stock.py`, `screener/market_data.py`
- Test pattern reference: `tests/test_cli_screener.py` (4 CLI tests), `tests/test_display.py` (30+ display tests)
- Decisions register: D041 (22-day lookback), D042 (CLI-only flag), D043 (cap placement), D044 (None sorts last)
- Requirements: TOPN-01 (CLI flag), TOPN-05 (Perf 1M column), TOPN-06 (backward compat)
- S01 gap confirmed via: `ScreenedStock.__dataclass_fields__` (no `perf_1m`), `run_pipeline` signature (no `top_n`), `compute_indicators` source (no monthly perf)
