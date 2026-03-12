# S02: CLI Flag + Display — Research

**Date:** 2026-03-11

## Summary

S02 is a low-risk terminal slice that wires S01's pipeline `top_n` parameter into the `run-screener` CLI via a `--top-n` Typer option, and adds a "Perf 1M" column to the Rich results table. All the hard work (perf computation, sort/cap logic, two-pass pipeline refactor) was done in S01. S02 is purely surface-level: one CLI option, one table column, and tests for both.

**Critical prerequisite:** The `gsd/M002/S01` branch must be merged into `gsd/M002/S02` before implementation. S01 delivers `run_pipeline(top_n=N)`, `ScreenedStock.perf_1m`, and `compute_monthly_performance()`. All three are consumed by S02 without modification. The S01 branch has 12 new tests (6 pipeline cap + 6 market data perf computation); after merge, baseline should be 357 tests.

Requirements owned by this slice: **TOPN-01** (CLI flag), **TOPN-05** (Perf 1M column), **TOPN-06** (backward compat). All three are straightforward additions following existing patterns in the codebase.

## Recommendation

Merge S01 into S02 branch first, then implement in two small tasks:

1. **CLI flag** — Add `--top-n` Typer option to `scripts/run_screener.py`, pass through to `run_pipeline(top_n=N)`. Add Typer `min=1` constraint. Write tests: flag passes to pipeline, no flag = `top_n=None`, `--help` shows `--top-n`, invalid value rejected.
2. **Display column** — Add "Perf 1M" column to `render_results_table()` in `screener/display.py` with signed percentage formatting (`+3.1%`, `-5.2%`, `N/A`). Add `fmt_signed_pct()` helper. Write tests: column appears, positive/negative formatting, None shows N/A.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option parsing | Typer `Annotated[int \| None, typer.Option()]` | Already used for all other flags in `run_screener.py` — Typer 0.24.1 installed |
| Terminal table rendering | Rich `Table.add_column()` + `table.add_row()` | Already used for all 13 columns in `render_results_table()` |
| Percentage formatting | `screener/display.py:fmt_pct()` | Exists but lacks `+` prefix for positive values — need new `fmt_signed_pct()` |
| CLI testing | `typer.testing.CliRunner` + `@patch` | Established pattern in `tests/test_cli_screener.py` (5 existing tests) |
| Display testing | `_capture_console()` + string assertions | Established pattern in `tests/test_display.py` (45 existing tests) |

## Existing Code and Patterns

- `scripts/run_screener.py:run()` — CLI entry point using Typer `Annotated` options with `PresetName | None` union type pattern. All existing flags (`--update-symbols`, `--verbose`, `--preset`, `--config`) follow identical pattern. Add `--top-n` the same way. Lines 119–126 have the `run_pipeline()` call site where `top_n=top_n` kwarg will be added.
- `screener/display.py:render_results_table()` — Builds Rich Table with 13 columns: #, Symbol, Price, AvgVol, MktCap, D/E, Margin, Growth, RSI, HV%ile, Yield, Score, Sector. Insert "Perf 1M" column after HV%ile (index 10), before Yield.
- `screener/display.py:fmt_pct()` — Formats `float | None → str` as `"X.X%"` or `"N/A"`. Does NOT add `+` prefix for positive values. Perf 1M needs signed output per TOPN-05 (`-5.2%`, `+3.1%`). New `fmt_signed_pct()` is the clean solution — Python's `f"{value:+.1f}%"` handles sign natively.
- `tests/test_cli_screener.py` — 5 existing CLI tests. Pattern: heavy `@patch("scripts.run_screener.X")` decoration, `CliRunner.invoke(app, args)`, assert on `exit_code` and `mock.assert_called_*`. The `test_default_no_file_writes` test verifies `mock_pipeline.assert_called_once()` — will need to extend to check `top_n` kwarg.
- `tests/test_display.py` — 45 existing display tests. Pattern: `_capture_console()` → call render function → string assertions on `console.file.getvalue()`. `_make_stock()` helper builds ScreenedStock with controllable fields but lacks `perf_1m` param — set directly via `stock.perf_1m = X` after creation (follows `hv_percentile` and `put_premium_yield` precedent where those are also set directly in tests, not via `_make_stock`).
- `models/screened_stock.py` — After S01 merge, has `perf_1m: Optional[float] = None` field between `hv_percentile` and `next_earnings_date`. Dataclass default is None, so all existing test fixtures continue working.

## Constraints

- **S01 merge required** — `gsd/M002/S01` branch must be merged into `gsd/M002/S02` before any code changes. S01 provides `run_pipeline(top_n=)`, `ScreenedStock.perf_1m`, and `compute_monthly_performance` import in `pipeline.py`. S01 branch has commits `815541d` (T01: perf function + field) and `94af363` / `500af27` (T02: two-pass pipeline with top_n sort/cap).
- **Typer 0.24.1** — `Annotated` syntax and `int | None` union type fully supported. Python 3.10+ used (confirmed by existing `PresetName | None` pattern in same file).
- **Backward compat (TOPN-06)** — `--top-n` omitted must result in `top_n=None` passed to pipeline. Default `= None` on the Typer option handles this.
- **No default cap** — Per D042, `top_n` is CLI-only, not preset-configurable. No preset YAML changes needed.
- **Existing test count** — 345 on S02 branch currently. After S01 merge: 357. S02 must not break any of them.

## Common Pitfalls

- **Typer hyphen/underscore conversion** — Typer automatically converts `--top-n` CLI flag to `top_n` Python parameter. Define the parameter as `top_n` with `typer.Option("--top-n", ...)` to be explicit. The existing `--update-symbols` → `update_symbols` pattern in the same file confirms this works.
- **fmt_pct lacks sign prefix** — Using `fmt_pct()` directly for perf_1m would show `3.1%` instead of `+3.1%`. Python's `+` format spec (`f"{value:+.1f}%"`) handles this natively. Create `fmt_signed_pct()` for testability rather than inlining the format.
- **Display test helper lacks perf_1m** — `_make_stock()` in `tests/test_display.py` doesn't accept `perf_1m`. Set `stock.perf_1m = X` directly after creation. This matches the existing pattern for `hv_percentile` and `put_premium_yield` which are also set directly in specific tests, not via `_make_stock`.
- **Column count in existing tests** — Tests that check for specific column headers (`test_table_has_column_headers`) check for column name presence, not column count. Adding "Perf 1M" column won't break them.
- **Typer min=1 validation** — `typer.Option(min=1)` prevents `--top-n 0` or negative values. Without this, `run_pipeline(top_n=0)` would return 0 stocks with no error. Typer 0.24.1 supports `min`/`max` for numeric options.
- **Existing test_default_no_file_writes mock coverage** — This test patches `run_pipeline` and calls `mock_pipeline.assert_called_once()`. After S02 changes, the call will include `top_n=None` kwarg. The `assert_called_once()` check passes regardless of kwargs, but we should add a targeted assertion for `top_n` in a new or updated test.

## Open Risks

- **None** — This is the lowest-risk slice in the milestone. All patterns are established, all dependencies are delivered by S01, and the implementation is purely additive (one option, one column, one formatter). The S01 branch has 12 new tests confirming the API contract S02 consumes.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer | — | none found (pattern established in codebase) |
| Rich | — | none found (pattern established in codebase) |
| Alpaca SDK | — | not needed for this slice (no API changes) |

No skill discovery needed — this slice uses only Typer and Rich, both already well-established with clear patterns in the codebase. No external search was required.

## Sources

- `scripts/run_screener.py` — existing CLI option patterns (Typer `Annotated` with `typer.Option`, `PresetName | None` union)
- `screener/display.py` — existing table column patterns (13 columns) and `fmt_pct` limitation (no sign prefix)
- `tests/test_cli_screener.py` — existing mock-heavy CLI test pattern with `CliRunner` (5 tests)
- `tests/test_display.py` — existing display test pattern with `_capture_console()` and `_make_stock()` (45 tests)
- `gsd/M002/S01` branch — confirmed `run_pipeline(top_n=N)` signature, `ScreenedStock.perf_1m` field, 12 new tests in `test_pipeline.py` (class `TestTopNPipelineCap`) and `test_market_data.py`
- D041 (fixed 22 trading day lookback), D042 (CLI-only, not preset), D043 (cap after Stage 1), D044 (None perf sorts last) — all decisions from DECISIONS.md governing this implementation
