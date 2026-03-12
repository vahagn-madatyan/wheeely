# S02: CLI Flag + Display — Research

**Date:** 2026-03-11

## Summary

S02 wires two remaining surfaces: a `--top-n` CLI option on `run-screener` and a "Perf 1M" column in the Rich results table. All backend work lives on branch `gsd/M002/S01` (not yet merged into `gsd/M002/S02`): `perf_1m` field on ScreenedStock, `compute_monthly_performance()`, `run_pipeline(top_n=...)` parameter with sort/cap logic, and 11+ tests. S02 must merge S01 first, then add the CLI flag, display column, and tests.

Both changes are small (~30 LOC each) and follow established patterns exactly. The CLI uses `Annotated[Optional[int], typer.Option("--top-n")]` matching the 4 existing options. The display adds a column between Yield and Score using `table.add_column()` + `table.add_row()`. One design choice: TOPN-05 requires signed format (`+3.1%`, `-5.2%`) while the existing `fmt_pct` omits the sign — a new `fmt_signed_pct` helper avoids breaking existing columns.

## Recommendation

Merge S01 into S02 branch, then implement in two tasks:

- **T01:** `--top-n` CLI flag + validation + tests — add Typer option, validate `>= 1`, pass `top_n=top_n` to `run_pipeline()`, test flag parsing and backward compat
- **T02:** "Perf 1M" display column + `fmt_signed_pct` formatter + tests — add column to `render_results_table()`, test rendering

Both are small and low-risk.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option parsing | `typer.Option` with `Annotated` | Already used for all 4 existing CLI options (same pattern) |
| Table rendering | Rich `Table.add_column` + `add_row` | Already used in `render_results_table` with 13 columns |
| Number formatting | `fmt_pct` in `screener/display.py` | Extend with signed variant; don't modify original |
| CLI testing | `typer.testing.CliRunner` + `@patch` | Already used in `test_cli_screener.py` (4 tests) |
| Display testing | `Console(file=StringIO())` capture | Already used in `test_display.py` (45 tests) |

## Existing Code and Patterns

### S01 Deliverables (branch `gsd/M002/S01` — must merge first)

- `models/screened_stock.py:40` — `perf_1m: Optional[float] = None` field on ScreenedStock
- `screener/market_data.py` — `compute_monthly_performance(bars_df)` returning float percentage or None (22-bar lookback)
- `screener/pipeline.py:1191` — `run_pipeline(..., top_n: int | None = None)` parameter; sorts Stage 1 survivors ascending by `perf_1m` (None→`float('inf')`), caps to `top_n` when set
- `tests/test_market_data.py` — 6 tests in `TestComputeMonthlyPerformance` (exact 22, 250 bars, insufficient, negative, positive, flat)
- `tests/test_pipeline.py` — `TestTopNPipelineCap` class with 5 tests (`test_top_n_caps_stage2_calls`, `test_top_n_none_processes_all`, `test_sort_ascending_perf`, `test_none_perf_sorts_last`, `test_perf_1m_populated_on_stocks`)

### CLI Entry Point (`scripts/run_screener.py`)

- Uses `Annotated[type, typer.Option("--flag-name", help="...")]` for all 4 parameters (lines 56-72)
- `PresetName(str, Enum)` for preset validation
- `run_pipeline()` called at line 119 with keyword args — must add `top_n=top_n`
- Error handling: `ValidationError` → Rich `Panel` + `typer.Exit(code=1)` (D022)
- Tests in `test_cli_screener.py`: 4 tests using `CliRunner` + stacked `@patch` decorators on module-level imports (D019)

### Display (`screener/display.py`)

- `render_results_table()` filters to `passed_all_filters and score is not None`, sorts by score desc
- 13 current columns: #, Symbol, Price, AvgVol, MktCap, D/E, Margin, Growth, RSI, HV%ile, Yield, Score, Sector
- "Perf 1M" column should go after Yield, before Score — groups it with technical indicators
- `fmt_pct(value)` → `"3.1%"` (no sign for positive) — used for RSI, Margin, Growth, HV%ile, Yield
- Console injection via parameter (D015): `console: Console | None = None`
- Tests in `test_display.py`: 45 tests, `_capture_console()` returns `Console(file=StringIO(), width=120)`
- `_make_stock()` helper builds ScreenedStock; doesn't currently accept `perf_1m` or `hv_percentile` kwargs — test helper will need updating

### Typer Behavior (verified against 0.24.1)

- `Annotated[Optional[int], typer.Option("--top-n")]` with `default=None` works correctly
- Omitted flag → `None`, `--top-n 20` → `20`
- Typer does NOT reject negative values (`--top-n -5` → `-5`) — must validate in CLI code

## Constraints

- S01 branch must be merged into S02 before implementation — S02 depends on `perf_1m` field, `top_n` parameter, and pipeline sort/cap logic
- `top_n` must be `Optional[int]` defaulting to `None` — omitting flag means no cap (TOPN-06, D042)
- Must validate `top_n >= 1` since Typer accepts negative integers
- 345 existing tests must continue passing (verified on current S02 branch)
- Console injection pattern (D015) must be used in display functions
- Module-level imports for patchability (D019) must be followed in CLI

## Common Pitfalls

- **Modifying `fmt_pct` for signed format** — Would prepend `+` to RSI, Margin, Growth, Yield, HV%ile columns where it's unwanted. Create a separate `fmt_signed_pct` helper.
- **Column count mismatch** — Adding `add_column("Perf 1M")` without adding the corresponding value to every `add_row()` call causes Rich to crash or silently misalign data. Both additions are required together.
- **Test helper `_make_stock`** — Doesn't accept `perf_1m` kwarg. Either update the helper or set `stock.perf_1m` directly in tests. The helper also doesn't accept `hv_percentile` or `put_premium_yield`, which are handled inline in existing tests.
- **Patch decorator order** — `test_cli_screener.py` stacks 8 `@patch` decorators (applied bottom-up). Adding a new patch must go in the right position.
- **Negative top_n** — Typer passes `-5` through as a valid int. Pipeline `stage1_survivors[:top_n]` with negative `top_n` would silently drop the last N items. Validate early in the CLI.

## Open Risks

- None significant. All patterns are established, code paths are clear, and the feature is purely additive.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer | — | none needed (simple CLI option, established pattern) |
| Rich | — | none needed (simple table column, established pattern) |

## Sources

- `scripts/run_screener.py` — CLI entry point with 4 existing Typer option patterns
- `screener/display.py` — `render_results_table()` with 13-column table pattern
- `tests/test_cli_screener.py` — 4 CLI tests with `CliRunner` + stacked `@patch`
- `tests/test_display.py` — 45 display tests with `Console(file=StringIO())` capture
- `gsd/M002/S01` branch — S01 deliverables (perf_1m, top_n, compute_monthly_performance, 11 tests)
- Decisions D015 (console injection), D019 (CLI imports), D022 (error output), D042 (top_n CLI-only)
- Typer 0.24.1 behavior verified: `Optional[int]` + `typer.Option("--top-n")` works; negative values not rejected
