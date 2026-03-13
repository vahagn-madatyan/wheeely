# S02: CLI Flag + Display — Research

**Date:** 2026-03-12

## Summary

S02 wires the `--top-n` CLI flag into `run-screener` and adds a "Perf 1M" column to the Rich results table. This is a low-risk, well-constrained slice with three clear deliverables: a Typer `Option`, a display column, and their tests.

**Critical finding:** S01 is marked complete but its source-code deliverables are **missing** from the repository. The `.pyc` bytecache confirms the work was done (a `compute_monthly_performance` function, `perf_1m` field on `ScreenedStock`, and `top_n` parameter on `run_pipeline` all exist in compiled bytecode) but the `.py` source files were never committed. S02 must therefore also implement the S01 deliverables before wiring the CLI and display.

The implementation pattern is well-established: Typer `Annotated` options with `typer.Option(...)`, console-injected `render_results_table` with `Console` parameter for testability, and `CliRunner` + `@patch` for CLI tests. All 345 existing tests pass. The total additional code is small — roughly 5 changed files and ~100 lines of production code plus ~150 lines of tests.

## Recommendation

Implement S01 + S02 as a single pass since S01's deliverables are missing but well-understood from `.pyc` inspection and the roadmap. The work decomposes into:

1. **Model:** Add `perf_1m: Optional[float] = None` to `ScreenedStock` (1 line)
2. **Computation:** Add `compute_monthly_performance(bars_df)` to `screener/market_data.py` — `(close[-1] / close[-22] - 1) * 100`, returns `None` if fewer than 22 bars
3. **Pipeline:** Add `top_n: int | None = None` parameter to `run_pipeline()`; after Stage 1, compute `perf_1m`, sort ascending, take first N; wire `stock.perf_1m = compute_monthly_performance(bars[sym])` in Step 4
4. **CLI:** Add `--top-n` Typer option in `scripts/run_screener.py`, pass through to `run_pipeline(top_n=N)`
5. **Display:** Add "Perf 1M" column to `render_results_table()` with signed percentage formatting (`+3.1%` / `-5.2%`)
6. **Tests:** Perf computation math, sort/cap logic, backward compatibility, CLI flag parsing, display column rendering

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option parsing | Typer `Annotated[int \| None, typer.Option(...)]` | Already used for `--preset`, `--config`, `--verbose` in this exact file |
| Rich table column | `table.add_column(...)` + `table.add_row(...)` | Pattern established with HV%ile and Yield columns in S08/S09 |
| CLI test harness | `typer.testing.CliRunner` + `@patch` decorators | 4 existing tests in `test_cli_screener.py` use this exact pattern |
| Console capture | `Console(file=StringIO(), width=120)` | Used in all `test_display.py` tests for output verification |

## Existing Code and Patterns

- `scripts/run_screener.py:run()` — Typer command with `Annotated` options. `--top-n` follows the same pattern as `preset: Annotated[PresetName | None, ...]`. The `run_pipeline()` call on line 119 is where `top_n=N` gets passed through.
- `screener/display.py:render_results_table()` — Rich table with 13 columns. "Perf 1M" inserts between "HV%ile" and "Yield" (or after "Yield" before "Score"). Follows the `hv_pct_str`/`yield_str` pattern for `None` handling.
- `screener/display.py:fmt_pct()` — Formats `12.3` as `12.3%` but does NOT add `+` sign for positives. TOPN-05 requires signed format (`+3.1%`, `-5.2%`). Either add a `fmt_signed_pct()` helper or inline the formatting.
- `screener/market_data.py:compute_indicators()` — Where `perf_1m` computation logically fits (or as a separate `compute_monthly_performance()` function). Uses `bars_df["close"]` series, same as needed for perf calculation.
- `screener/pipeline.py:run_pipeline()` — 130-line function; `top_n` parameter adds to signature. Sort/cap logic inserts after Stage 1 loop completes but before Stage 1b/2/3 processing. Current structure processes all stages inside a single `for sym in universe` loop, so the cap needs to happen by splitting the loop: first loop computes indicators + Stage 1, second loop (capped) does Stage 1b/2/3.
- `models/screened_stock.py:ScreenedStock` — Simple dataclass. `perf_1m` goes after `hv_percentile` in the technical indicators section.
- `tests/test_cli_screener.py` — 4 tests with heavy `@patch` decoration. Pattern: patch `run_pipeline`, `render_results_table`, `progress_context`, etc. at `scripts.run_screener.*` import path.
- `tests/test_display.py` — 29 tests covering formatters, score styling, results table, stage summary, filter breakdown, progress callback. `_make_stock()` helper creates test stocks. `_all_pass_filters()` creates passing filter results.

## Constraints

- **Pipeline loop restructuring required.** The current `run_pipeline()` processes all stages in a single `for sym in universe` loop. To cap after Stage 1, the loop must split: first pass does indicators + Stage 1 filtering, then sort/cap, then second pass does Stage 1b/2/3 on survivors only. This is the biggest structural change.
- **`perf_1m` computation happens during the first pass** (Step 4, alongside other indicators), before sorting.
- **`top_n=None` must be fully backward compatible.** All 345 existing tests must pass without modification. The `run_pipeline` signature gains `top_n=None` as a kwarg with default.
- **Typer `int | None` with default `None`.** Typer 0.24.1 supports `Annotated[int | None, typer.Option(...)] = None`. When omitted, value is `None` (no cap).
- **`fmt_pct` doesn't add `+` sign.** Need either a new `fmt_signed_pct()` or inline `f"{value:+.1f}%"` for the Perf 1M column. Python's `+` format spec handles this natively.
- **Validation:** `--top-n 0` or `--top-n -5` should error. Typer's `min=1` constraint or a manual `typer.BadParameter` check.

## Common Pitfalls

- **Pipeline loop split breaks existing behavior.** The sort/cap must only affect which stocks proceed to Stage 1b/2/3 — Stage 1 filtering must still run on all stocks so that `render_stage_summary()` counts remain accurate. Stocks that fail Stage 1 but aren't in the top-N should still be in the returned list (they just have no Stage 2+ results). Test with `top_n=None` to ensure all 345 tests still pass.
- **`None` perf_1m sorting.** `sorted(stocks, key=lambda s: s.perf_1m)` will crash on `None` values. Must use `key=lambda s: (s.perf_1m is None, s.perf_1m or 0)` to sort `None` to end (D044).
- **Typer option naming.** `--top-n` with hyphen becomes `top_n` in Python. Typer handles this automatically when using `typer.Option("--top-n", ...)`.
- **Test patches for `run_pipeline` must still work.** The `@patch("scripts.run_screener.run_pipeline", return_value=[])` in existing CLI tests patches the import in the CLI module. Adding `top_n` to the signature doesn't break this since it has a default.

## Open Risks

- **S01 deliverables are missing from source.** The `.pyc` files confirm the work was done but source was never committed. This slice must re-implement S01's changes (perf computation, model field, pipeline cap). The `.pyc` bytecache provides a reliable reference for the intended implementation. Risk is low but scope is larger than originally planned for S02 alone.
- **Pipeline loop split complexity.** Splitting the single loop into two passes is the most structurally complex change. Need to ensure stocks that fail Stage 1 are still appended to the `stocks` list with their filter results intact for summary display.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer | n/a | no skill needed — simple Option addition following existing patterns |
| Rich | n/a | no skill needed — simple column addition following existing patterns |
| Alpaca SDK | n/a | no changes to API calls |

No professional agent skills are needed — this work uses well-established patterns already present in the codebase.

## Sources

- `scripts/run_screener.py` — existing CLI with Typer Annotated pattern
- `screener/display.py` — existing render_results_table with 13 columns
- `screener/pipeline.py:run_pipeline()` — pipeline function to gain `top_n` parameter
- `screener/market_data.py` — where `compute_monthly_performance()` will be added
- `models/screened_stock.py` — dataclass gaining `perf_1m` field
- `tests/test_cli_screener.py` — 4 existing CLI tests as pattern reference
- `tests/test_display.py` — 29 existing display tests as pattern reference
- `.pyc` bytecache — confirmed S01's intended implementation (22-day lookback, `close[-1]/close[-22]-1`, `top_n` param)
- D041–D044 in DECISIONS.md — governing decisions for perf lookback, CLI-only flag, cap placement, None sorting
