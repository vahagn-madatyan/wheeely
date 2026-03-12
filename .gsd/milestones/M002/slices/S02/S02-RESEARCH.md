# S02: CLI Flag + Display — Research

**Date:** 2026-03-11

## Summary

S02 is a low-risk, well-scoped wiring slice. It connects S01's `run_pipeline(top_n=N)` parameter and `ScreenedStock.perf_1m` field to the user-facing CLI and display layers. The three deliverables are: (1) a `--top-n` Typer option on `run-screener`, (2) a "Perf 1M" column in the Rich results table, and (3) tests for both. All patterns already exist in the codebase — this slice replicates them.

The main prerequisite is that S01's branch (`gsd/M002/S01`) must be merged into the S02 branch before implementation begins, since S02's working copy currently lacks the `perf_1m` field, `compute_monthly_performance()`, and the `top_n` parameter on `run_pipeline()`.

## Recommendation

Merge `gsd/M002/S01` into `gsd/M002/S02` first. Then implement in two small tasks: (1) CLI flag + passthrough, (2) display column + tests. Both are mechanical — follow existing patterns exactly.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option declaration | Typer `Annotated[int \| None, typer.Option()]` | Already used for `--preset`, `--config`, `--verbose` in `run_screener.py` |
| Table column rendering | `table.add_column()` + `fmt_pct()` in `screener/display.py` | HV%ile and Yield columns are identical patterns |
| CLI test pattern | `typer.testing.CliRunner` + `@patch` in `test_cli_screener.py` | 4 existing tests demonstrate the exact mock stack |
| Display test pattern | `Console(file=StringIO())` capture in `test_display.py` | `_capture_console()` helper already exists |

## Existing Code and Patterns

- `scripts/run_screener.py:run()` — CLI entry point. Has 4 existing `typer.Option` parameters (`update_symbols`, `verbose`, `preset`, `config`). The `--top-n` option follows the same pattern. The `run_pipeline()` call at line 119 needs `top_n=top_n` kwarg added.
- `screener/display.py:render_results_table()` — Results table with 13 columns. "Perf 1M" column inserts naturally between "HV%ile" and "Yield" (or at any position — order is aesthetic). Uses `fmt_pct()` which already handles sign display (e.g. `-5.2%`).
- `tests/test_cli_screener.py` — CLI tests use `typer.testing.CliRunner` with a stack of `@patch` decorators mocking `load_config`, `create_broker_client`, `require_finnhub_key`, `FinnhubClient`, `run_pipeline`, `progress_context`, and the display functions. New `--top-n` tests follow this exact pattern.
- `tests/test_display.py` — Display tests use `Console(file=StringIO(), width=120)` to capture output, then assert on string content. `_make_stock()` and `_all_pass_filters()` helpers construct test data. The `perf_1m` kwarg needs to be added to `_make_stock()`.
- `models/screened_stock.py` — S01 adds `perf_1m: Optional[float] = None` after `hv_percentile`. Already on `gsd/M002/S01` branch.
- `screener/pipeline.py` — S01 adds `top_n: int | None = None` parameter to `run_pipeline()`. Already on `gsd/M002/S01` branch.

## Constraints

- **S01 merge required first**: The S02 branch currently diverges from S01 — it has none of S01's code changes (`perf_1m` field, `compute_monthly_performance()`, `top_n` parameter). Must merge `gsd/M002/S01` before writing any code.
- **Typer >= 0.9.0**: Project uses `Annotated` style for Typer options (modern syntax). The `--top-n` option must use the same pattern.
- **`int | None` type annotation**: Typer handles `Optional[int]` / `int | None` as nullable options (no default value means `None` when omitted). This matches TOPN-06 backward compatibility.
- **345 existing tests must pass**: Any change must not break the existing test suite.
- **D019 pattern**: Module-level imports in CLI entry points for `@patch` compatibility. All imports in `run_screener.py` are at module level — maintain this.
- **D015 pattern**: Console injection for testability. `render_results_table()` accepts `console` parameter.

## Common Pitfalls

- **Typer snake_case → kebab-case mapping**: Typer automatically converts `top_n` parameter name to `--top-n` CLI flag. The function parameter must be `top_n`, not `top-n`. This is standard Typer behavior.
- **Signed percentage display**: `fmt_pct()` returns `-5.2%` for negative values but `5.2%` for positive (no explicit `+` sign). TOPN-05 specifies `+3.1%` format for positive values. Either modify `fmt_pct()` (would affect all callers) or use a local formatter in the perf_1m row rendering.
- **None perf_1m display**: Stocks that have no bar data won't have `perf_1m`. The column should show "N/A" for these, consistent with all other nullable columns.
- **Column ordering**: The existing table has Score as the second-to-last column and Sector last. "Perf 1M" should go before Score to maintain the pattern of data columns → composite score → sector.

## Open Risks

- **None**: This is a straightforward wiring slice. All APIs are defined by S01, all patterns exist in the codebase, and no new external dependencies are needed.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer | — | none needed (simple CLI option, well-documented in codebase) |
| Rich | — | none needed (existing table patterns sufficient) |

## Sources

- S01 branch diff (`git diff main..gsd/M002/S01`) — confirmed `perf_1m`, `compute_monthly_performance()`, and `top_n` parameter implementations
- `scripts/run_screener.py` — existing CLI option patterns
- `screener/display.py` — existing table column patterns
- `tests/test_cli_screener.py` — existing CLI test patterns with mock stack
- `tests/test_display.py` — existing display test patterns with console capture
