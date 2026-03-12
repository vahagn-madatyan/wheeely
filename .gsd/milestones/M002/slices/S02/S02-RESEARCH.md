# S02: CLI Flag + Display — Research

**Date:** 2026-03-11

## Summary

S02 wires S01's `top_n` pipeline parameter to a `--top-n` CLI flag on `run-screener` and adds a "Perf 1M" column to the Rich results table. This is a thin integration slice — no new algorithmic logic, just plumbing and display.

S01's code lives on branch `gsd/M002/S01` (not yet merged into S02's branch). S02 must merge S01 first. The S01 diff adds: `perf_1m: Optional[float]` field on `ScreenedStock`, `compute_monthly_performance()` in `market_data.py`, `top_n` parameter on `run_pipeline()`, and two-pass pipeline architecture with sort/cap logic. S01 branch has 12 new tests (6 perf math + 6 pipeline cap). Both branches share the same merge-base (`cd06247`), so the merge should be clean — S02 has no `.py` changes, only GSD artifact files.

The three S02 code touchpoints are small: ~10 lines in `scripts/run_screener.py` (new Typer option + pass-through + validation), ~10 lines in `screener/display.py` (new column + formatter), and ~50-80 lines of tests.

## Requirements Covered

| Req | Description | This Slice's Role |
|-----|-------------|-------------------|
| TOPN-01 | `--top-n N` CLI flag | Primary owner — add the flag, validate, pass through |
| TOPN-05 | "Perf 1M" column in results table | Primary owner — add column + signed-pct formatter |
| TOPN-06 | No flag = all stocks processed | Primary owner — default `None` means no cap |

## Recommendation

1. Merge `gsd/M002/S01` into S02 branch first. Verify 357 tests pass (345 existing + 12 from S01).
2. Add `--top-n` as `Annotated[int | None, typer.Option('--top-n', ...)]` with in-body validation for `<= 0`. Typer 0.24.1 handles `int | None` natively (verified locally).
3. Add a `fmt_signed_pct()` formatter for the Perf 1M column — existing `fmt_pct()` produces `3.1%` without a plus sign, but TOPN-05 specifies `+3.1%` format.
4. Insert "Perf 1M" column between "HV%ile" and "Yield" — logically groups market data before scoring columns.
5. Tests: CLI flag parsing (~4 tests), display column presence (~2 tests), formatter (~3 tests).

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option parsing | `Annotated[int \| None, typer.Option()]` | Already used for all other flags; consistent pattern |
| Rich table columns | `table.add_column()` + `add_row()` in existing loop | Matches all other columns in `render_results_table` |
| CLI test harness | `typer.testing.CliRunner` | Already used in `test_cli_screener.py` |
| Console capture | `Console(file=StringIO())` | Already used in all display tests |

## Existing Code and Patterns

- **`scripts/run_screener.py:run()`** — All CLI options use `Annotated[T, typer.Option(...)]` pattern. The `run_pipeline(...)` call at ~line 120 needs `top_n=top_n` kwarg added. Error handling for bad config uses `Console(stderr=True)` + Rich Panel + `typer.Exit(code=1)` — reuse same pattern for `top_n <= 0` validation.
- **`screener/display.py:render_results_table()`** — Columns added sequentially with `table.add_column()`, data formatted inline in the `add_row()` loop. Current column order: #, Symbol, Price, AvgVol, MktCap, D/E, Margin, Growth, RSI, HV%ile, Yield, Score, Sector. "Perf 1M" inserts between HV%ile and Yield.
- **`screener/display.py:fmt_pct()`** — Formats `X.X%` without sign prefix. New `fmt_signed_pct()` needed: `+3.1%` / `-5.2%` / `0.0%`.
- **`tests/test_cli_screener.py`** — Uses `@patch("scripts.run_screener.<module>")` mock stack. The `test_default_no_file_writes` test patches 8 modules. New `--top-n` tests follow this pattern, verifying `run_pipeline` receives the `top_n` kwarg.
- **`tests/test_display.py:_make_stock()`** — Helper builds `ScreenedStock` with named kwargs. Will need `perf_1m` param added (or set directly since it's a dataclass).
- **`tests/test_display.py:test_table_has_column_headers()`** — Checks hardcoded column name list. Must be updated to include "Perf 1M".
- **S01 pipeline changes (on branch)** — `run_pipeline()` accepts `top_n: int | None = None`, `ScreenedStock` has `perf_1m: Optional[float]`. These are the contracts S02 consumes.

## Constraints

- **S01 must be merged first** — `gsd/M002/S01` branch contains `perf_1m` field and `top_n` parameter. S02 branch (`gsd/M002/S02`) currently diverges from S01 — only GSD artifacts, no Python changes, so merge will be clean.
- **Typer 0.24.1** — `int | None` with `typer.Option` works (verified). Default `None` = no cap (TOPN-06).
- **Validation must be in-body** — Typer doesn't support custom validators on `Option`. `top_n <= 0` → `Console(stderr=True)` + `typer.Exit(code=1)`, matching existing config validation pattern.
- **Column ordering** — Rich tables ordered by `add_column()` call sequence. "Perf 1M" must be inserted at position after "HV%ile" (index 9) and before "Yield" (index 10).
- **345 → 357 test count** — After merging S01, test count should be 357. S02 adds ~9 more → ~366 expected.

## Common Pitfalls

- **Forgetting to pass `top_n` kwarg to `run_pipeline()`** — The Typer option must be threaded. Easy to add the flag declaration but miss the pass-through on the `run_pipeline(...)` call.
- **Not merging S01 first** — Without `perf_1m` on `ScreenedStock` and `top_n` on `run_pipeline()`, the CLI and display code has nothing to connect to.
- **`fmt_pct` vs signed format** — Using existing `fmt_pct()` for Perf 1M would produce `3.1%` instead of `+3.1%`. Requirement TOPN-05 explicitly shows signed format.
- **`--top-n 0` edge case** — Typer parses `0` as valid int, not `None`. Body validation must catch `top_n <= 0`.
- **`--top-n` with `--update-symbols`** — No interaction issue, but worth a quick test to confirm they compose correctly.

## Open Risks

- **S01 merge conflicts** — Low risk. S01 modifies `pipeline.py`, `market_data.py`, `screened_stock.py`, and test files. S02 has no Python changes, only `.gsd/` artifacts. Merge should be fully clean.
- **Existing display test fragility** — `test_table_has_column_headers` only checks that listed columns exist (doesn't fail on extras), so it would pass vacuously without verifying "Perf 1M". Must explicitly add "Perf 1M" to the checked list.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer CLI | none found | — |
| Rich (Python) | none found | — |

## Sources

- Codebase: `scripts/run_screener.py`, `screener/display.py`, `models/screened_stock.py`, `screener/pipeline.py`, `tests/test_cli_screener.py`, `tests/test_display.py`
- S01 branch diff: `git diff main..gsd/M002/S01` — 921 insertions, 38 deletions across 16 files
- Typer 0.24.1 `int | None` behavior: verified locally with `CliRunner`
- Branch merge-base: `cd06247` (shared between S01 and S02)
