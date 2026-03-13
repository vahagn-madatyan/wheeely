# S02: CLI Flag + Display — Research

**Date:** 2026-03-12

## Summary

S02 is a low-risk wiring slice: plumb `top_n` from CLI to pipeline, add "Perf 1M" to the results table, and test both. All hard work (perf computation, sort/cap logic, `perf_1m` field) is already done in S01. S02 touches three files (`scripts/run_screener.py`, `screener/display.py`, `tests/`) and follows patterns already established across 345 existing tests.

The main prerequisite is that S01's branch (`gsd/M002/S01`) must be merged into S02's branch (`gsd/M002/S02`) before implementation begins — they currently share a common ancestor at `main` but S02 doesn't have S01's code changes (the `perf_1m` field, `compute_monthly_performance`, `top_n` parameter on `run_pipeline`, and the two-pass pipeline refactor).

## Recommendation

Merge `gsd/M002/S01` into `gsd/M002/S02` first. Then implement in two small tasks:

1. **CLI flag:** Add `--top-n` Typer option to `scripts/run_screener.py`, pass through to `run_pipeline(top_n=N)`. Test with `typer.testing.CliRunner`.
2. **Display column:** Add "Perf 1M" column to `render_results_table()` in `screener/display.py`. Test column appears with formatted values.

Both tasks are trivial — each is ~10 lines of production code plus tests following existing patterns.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option parsing | Typer `Annotated[int \| None, typer.Option()]` | Already used for `--verbose`, `--preset`, `--config` in same file |
| CLI testing | `typer.testing.CliRunner` | Already used in `test_cli_screener.py` with same patch pattern |
| Rich table columns | `table.add_column()` + `table.add_row()` | Already used for 12 columns in `render_results_table()` |
| Percentage formatting | `fmt_pct()` in `screener/display.py` | Already formats `rsi_14`, `net_margin`, `sales_growth`, `hv_percentile` |

## Existing Code and Patterns

- `scripts/run_screener.py:run()` — Typer command with 4 existing `Annotated` options. Add `--top-n` as 5th option following identical pattern. Pass to `run_pipeline(top_n=top_n)`.
- `screener/display.py:render_results_table()` — 12 existing columns. Add "Perf 1M" column between "HV%ile" and "Yield" (or similar position). Use `fmt_pct(stock.perf_1m)` — handles `None → "N/A"` automatically.
- `tests/test_cli_screener.py` — 5 existing CLI tests using `CliRunner` + `@patch("scripts.run_screener.X")`. Follow `test_default_no_file_writes` pattern for `--top-n` tests.
- `tests/test_display.py` — `_make_stock()` helper, `_all_pass_filters()`, `_capture_console()` pattern. Extend `_make_stock()` to accept `perf_1m` kwarg, or set it directly on the stock object.
- `screener/display.py:fmt_pct()` — Formats `float | None → "X.X%" | "N/A"`. Handles negative values correctly (e.g., `-5.2%`). Sign is inherent in the float; no `+` prefix for positive values unless we add it.

### S01 Deliverables (on `gsd/M002/S01` branch)

- `models/screened_stock.py` — `perf_1m: Optional[float] = None` field added after `hv_percentile`
- `screener/market_data.py` — `compute_monthly_performance(bars_df) → float | None` (22-bar lookback)
- `screener/pipeline.py` — `run_pipeline(..., top_n=None)` parameter; two-pass architecture with sort/cap between Stage 1 and Stage 1b
- `tests/test_market_data.py` — 6 new tests in `TestComputeMonthlyPerformance`
- `tests/test_pipeline.py` — 6 new tests in `TestTopNPipelineCap` (caps stage2 calls, None processes all, sort ascending, None sorts last, perf populated, all stocks returned)

## Constraints

- **Merge S01 first:** S02 branch diverges from S01 at `main`; S01's `perf_1m` field, `compute_monthly_performance`, and `top_n` pipeline parameter are not on S02's branch yet.
- **`top_n` type:** Must be `int | None` (not `int` with default 0). `None` = no cap (backward compat per D042/TOPN-06).
- **`run_strategy.py` unchanged:** It calls `run_pipeline()` without `top_n` and without `option_client` — must not be affected (TOPN-06).
- **Perf 1M display format:** `fmt_pct()` produces `-5.2%` for negative values. Requirements say "percentage with sign (e.g. -5.2%, +3.1%)". The `fmt_pct()` function does NOT add `+` prefix for positive. Decide: use `fmt_pct` as-is (negative shows `-`, positive shows bare number) or create `fmt_signed_pct` for explicit `+`/`-`. Recommendation: add a small helper or inline format `f"{value:+.1f}%"` for signed display — clearer for the user.
- **Column position:** "Perf 1M" should appear near HV%ile since both are technical indicators. After "HV%ile" and before "Yield" makes logical sense in the existing column order.
- **D019 (module-level imports):** CLI entry points use module-level imports for patchability. No new imports needed for `--top-n` (Typer/typing already imported).

## Common Pitfalls

- **Forgetting to merge S01** — Implementation will fail immediately if `perf_1m` field and `top_n` parameter don't exist. Merge first, verify tests pass.
- **Typer `int | None` default** — Typer handles `Optional[int]` well with `typer.Option(default=None)`. The `int | None` union syntax is fine on Python 3.10+ (project uses 3.13). Don't accidentally use `default=0` which would always cap.
- **Positive perf display ambiguity** — `fmt_pct(3.1)` → `"3.1%"` without `+` sign. Users may not realize this means +3.1%. A signed format (`+3.1%`) is more explicit for performance values where direction matters.
- **Existing test count** — 345 tests must still pass after S02. Existing `test_display.py` tests check for column headers by name — adding a new column won't break them unless it changes the table structure in unexpected ways.
- **`_make_stock()` in test_display.py** — The helper doesn't currently accept `perf_1m`. Either add it as a kwarg or set `stock.perf_1m = X` after creation (dataclass allows direct attribute assignment).

## Open Risks

- **S01 merge conflicts:** S01 modifies `screener/pipeline.py` significantly (two-pass refactor). If `gsd/M002/S02` has any `.py` changes from other work, merge could conflict. Current check shows S02 has zero `.py` diffs from `main`, so merge should be clean.
- **`fmt_pct` sign behavior:** If we add `+` prefix for positive perf_1m, we need to ensure it doesn't affect other uses of `fmt_pct` (RSI, margins, etc. should NOT show `+`). Safest: create a separate `fmt_signed_pct()` or inline the format string.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer CLI | `0xdarkmatter/claude-mods@python-cli-patterns` (29 installs) | available — not needed (existing patterns sufficient) |
| Rich tables | none found | N/A — existing patterns sufficient |

## Sources

- S01 branch code (`gsd/M002/S01`) — inspected via `git show` for all deliverables
- Existing test patterns in `tests/test_cli_screener.py` (5 tests) and `tests/test_display.py` (30+ tests)
- Typer `Annotated` usage already established in `scripts/run_screener.py` lines 57-73
