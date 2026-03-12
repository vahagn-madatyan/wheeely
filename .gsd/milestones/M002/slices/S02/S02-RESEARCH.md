# S02: CLI Flag + Display — Research

**Date:** 2026-03-11

## Summary

S02 adds two thin layers on top of S01's pipeline work: a `--top-n N` Typer option in `scripts/run_screener.py` that passes through to `run_pipeline(top_n=N)`, and a "Perf 1M" column in `screener/display.py`'s `render_results_table()`. Both changes are straightforward — the CLI follows the exact pattern of existing `--verbose`, `--update-symbols`, and `--preset` options, and the display column follows the existing column pattern (HV%ile, Yield, etc.).

**Critical prerequisite:** S01's code changes exist on the `gsd/M002/S01` branch but have **not been merged** into the current `gsd/M002/S02` branch. The current branch lacks `perf_1m` on ScreenedStock, `compute_monthly_performance()` in market_data.py, the `top_n` parameter on `run_pipeline()`, and the two-pass pipeline refactor. S01 must be merged before S02 implementation begins.

## Recommendation

Merge `gsd/M002/S01` into `gsd/M002/S02` first, confirm all 345+ existing tests + S01's new tests pass, then implement S02 as two small tasks: (1) `--top-n` CLI flag + tests, (2) "Perf 1M" display column + tests. Both are low-risk, well-patterned changes.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI flag parsing | Typer `typer.Option` with type annotation | Project already uses Typer for all CLI entry points; consistent pattern |
| CLI test harness | `typer.testing.CliRunner` | Already used in `test_cli_screener.py`; proven mock-and-invoke pattern |
| Table column display | Rich `Table.add_column` + `add_row` | Existing `render_results_table` already has 12 columns using this pattern |
| Percentage formatting | `screener.display.fmt_pct()` | Already exists, formats `float → "X.X%"`, handles None → "N/A" |

## Existing Code and Patterns

- `scripts/run_screener.py:run()` — CLI entry point with Typer. New `--top-n` option follows exact pattern of `--verbose` and `--preset` options (Annotated type + `typer.Option`). Must pass `top_n=` kwarg to `run_pipeline()` call at line ~100.
- `screener/display.py:render_results_table()` — Rich table with 12 existing columns. New "Perf 1M" column inserts after "HV%ile" and before "Yield". Uses `fmt_pct()` for formatting. Access via `stock.perf_1m`.
- `tests/test_cli_screener.py` — CLI tests use `typer.testing.CliRunner`, patch module-level imports at `scripts.run_screener.*` path, verify exit codes and mock calls. New test verifies `run_pipeline` receives `top_n=20` kwarg.
- `tests/test_display.py` — Display tests use `_make_stock()` helper (must add `perf_1m` kwarg), `_capture_console()` for StringIO capture, `_all_pass_filters()` for passing filter sets. Check column header presence in rendered output string.
- `models/screened_stock.py` — On S01 branch, `perf_1m: Optional[float] = None` sits after `hv_percentile` in the Technical indicators section.
- `screener/pipeline.py` — On S01 branch, `run_pipeline()` accepts `top_n: int | None = None` as last parameter.

## Constraints

- S01 branch (`gsd/M002/S01`) must be merged first — it provides the `perf_1m` field, `compute_monthly_performance()`, `top_n` parameter, and two-pass pipeline structure.
- `--top-n` must accept positive integers only. Typer's `int` type handles parsing; validation for `>0` should use Typer's `min=1` or a callback.
- Omitting `--top-n` must result in `top_n=None` passed to `run_pipeline()` — backward compatible, processes all stocks (TOPN-06).
- "Perf 1M" display must show sign: negative values like `-5.2%`, positive like `+3.1%`. The existing `fmt_pct()` does NOT include the `+` sign for positives — need a small formatting tweak or inline format.
- The `_make_stock` helper in `test_display.py` does not currently accept `perf_1m` — needs to be extended.

## Common Pitfalls

- **`fmt_pct` lacks `+` sign** — `fmt_pct(-5.2)` returns `"-5.2%"` but `fmt_pct(3.1)` returns `"3.1%"` (no `+`). For the "Perf 1M" column, positive values should show `+` to distinguish from negative. Use a dedicated `fmt_perf` helper or inline `f"{value:+.1f}%"` format. Avoid modifying `fmt_pct` itself since it's used by other columns where `+` is unwanted.
- **Typer `--top-n` naming** — Typer converts underscores to hyphens by default. A parameter named `top_n` with `typer.Option("--top-n")` will work. The existing pattern uses explicit flag names in `typer.Option()` strings, so follow suit.
- **Test mock stack order** — `test_cli_screener.py` uses heavy `@patch` decorator stacks. The decorator order is bottom-up (last decorator = first mock arg). When adding new patches (e.g., for verifying `top_n` kwarg), maintain this convention.
- **`_all_pass_filters` missing HV/earnings/options filters** — The helper in `test_display.py` only includes bar_data through optionable. It was written before S08/S09 added `hv_percentile`, `earnings_proximity`, `options_oi`, `options_spread` filter names. This won't break "Perf 1M" tests since the column renders from `stock.perf_1m` field, not filter results, but be aware for test clarity.

## Open Risks

- **S01 merge conflicts** — S01 modifies `pipeline.py`, `market_data.py`, `screened_stock.py`, and test files. Since S02 was branched before S01 code existed, merge should be clean (S02 hasn't modified those files yet), but verify after merge.
- **`perf_1m` is None for <22 bars stocks that pass all filters** — If a stock passes all filters but has `perf_1m=None` (unlikely with 250 bars fetched, but edge case), the display column should show "N/A" gracefully. `fmt_pct(None)` already returns `"N/A"`.

## Requirements Owned by This Slice

| Requirement | What S02 Must Deliver |
|---|---|
| **TOPN-01** (primary) | `--top-n N` CLI flag on `run-screener`, passed through to `run_pipeline(top_n=N)` |
| **TOPN-05** (primary) | "Perf 1M" column in Rich results table with signed percentage values |
| **TOPN-06** (primary) | No `--top-n` flag → `top_n=None` → all stocks processed (backward compatible) |

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer (CLI) | — | none found (simple enough; no skill needed) |
| Rich (tables) | — | none found (existing patterns sufficient) |

## Sources

- `scripts/run_screener.py` — existing CLI flag patterns (Typer Options, Annotated types)
- `tests/test_cli_screener.py` — CLI test patterns (CliRunner, mock stacks)
- `screener/display.py` — existing table column and formatting patterns
- `tests/test_display.py` — display test patterns (_make_stock, _capture_console, header assertions)
- `gsd/M002/S01` branch — S01 implementation (perf_1m field, compute_monthly_performance, top_n param, two-pass pipeline)
