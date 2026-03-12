# S02: CLI Flag + Display — Research

**Date:** 2026-03-11

## Summary

S02 is a low-risk, narrow-scope slice that wires the S01 pipeline changes (`top_n` parameter, `perf_1m` field) into user-facing surfaces: a `--top-n` Typer CLI option on `run-screener` and a "Perf 1M" column in the Rich results table.

All upstream work is done on the `gsd/M002/S01` branch: `run_pipeline(top_n=N)` already sorts/caps Stage 1 survivors, `ScreenedStock.perf_1m` is populated from `compute_monthly_performance()`, and pipeline tests cover sort/cap/backward-compat. S02 only needs to expose these via CLI and display — no computation or pipeline logic changes required.

The three target files (`scripts/run_screener.py`, `screener/display.py`, and their test files) follow well-established patterns from prior slices that are directly reusable. Adding a Typer option, passing it through to `run_pipeline()`, and adding a table column each have clear precedent.

## Recommendation

Merge `gsd/M002/S01` into `gsd/M002/S02` first, then make three surgical changes:

1. **CLI flag**: Add `top_n: Annotated[int | None, typer.Option("--top-n", ...)] = None` to `run()` and pass it through to `run_pipeline(..., top_n=top_n)`.
2. **Display column**: Add `table.add_column("Perf 1M", ...)` and a corresponding `add_row` value using `fmt_pct(stock.perf_1m)` with sign display (needs a small `fmt_signed_pct` helper or inline format since `fmt_pct` doesn't show `+` sign).
3. **Tests**: CLI flag parsing test, display column presence test, `perf_1m` formatting test (positive, negative, None cases).

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option parsing | `typer.Option("--top-n")` with `Annotated` | All existing options use this pattern; Typer handles validation, help text, type coercion |
| Results table column | `table.add_column()` + `fmt_pct()` in `render_results_table()` | HV%ile and Yield columns added in S08/S09 are direct precedent |
| CLI testing | `typer.testing.CliRunner` with `@patch` stack | `test_cli_screener.py` has exact pattern for mocked invocations |

## Existing Code and Patterns

- **`scripts/run_screener.py:run()`** — Four existing `Annotated[..., typer.Option()]` params. Add `top_n` in the same style. Pass it to `run_pipeline()` at line 119 as `top_n=top_n`.
- **`screener/display.py:render_results_table()`** — 12 existing columns. Insert "Perf 1M" after "HV%ile" (before "Yield") to keep technical indicators grouped. Format with `fmt_pct()` but need sign prefix for positive values (current `fmt_pct` omits `+`).
- **`screener/display.py:fmt_pct()`** — Returns `f"{value:.1f}%"` — no sign for positive. Either: (a) add a `fmt_signed_pct()` helper, or (b) inline `f"{value:+.1f}%"` at the call site. A helper is cleaner since the column semantics are "change" not "level".
- **`tests/test_cli_screener.py`** — `test_default_no_file_writes` is the template for CLI tests: 8-deep `@patch` stack, `CliRunner.invoke(app, args)`, assert `exit_code == 0`, assert `mock_pipeline.assert_called_once()`. New test adds `["--top-n", "20"]` args and verifies `top_n=20` in call kwargs.
- **`tests/test_display.py:TestRenderResultsTable`** — `test_table_has_column_headers` checks column names in output. Extend the assertion list. `_make_stock()` helper already takes kwargs; it needs `perf_1m` added.
- **`tests/test_options_chain.py:test_yield_column_in_results_table`** — Exact pattern for verifying a new column appears with correct formatted value. Copy for Perf 1M.

## Constraints

- **S01 branch must be merged first.** The `gsd/M002/S01` branch adds `perf_1m` to `ScreenedStock`, `compute_monthly_performance()`, and `top_n` param to `run_pipeline()`. S02's CLI and display code depends on all three.
- **`_make_stock()` test helper** in `test_display.py` doesn't accept `perf_1m` yet — it needs the kwarg added (or the field set after construction).
- **Typer `int | None` union** — Typer 0.24 supports `int | None = None` with `Annotated`. The existing `preset: PresetName | None = None` pattern confirms this works.
- **Column ordering matters** — Rich tables render columns in `add_column` order. "Perf 1M" should go between "HV%ile" and "Yield" to group technical/performance metrics together.
- **345 existing tests must pass** after changes.

## Common Pitfalls

- **Forgetting to pass `top_n` to `run_pipeline()`** — Easy to add the CLI option but forget to wire it through in the `run_pipeline(...)` call at line 119. Verify the kwarg appears in the test mock assertion.
- **`fmt_pct` doesn't show `+` sign** — Using `fmt_pct` for Perf 1M will show `-5.2%` correctly but `3.1%` instead of `+3.1%`. Performance columns conventionally show sign on both positive and negative. Use `f"{value:+.1f}%"` or a dedicated helper.
- **Typer `--top-n` hyphen vs underscore** — Typer maps `--top-n` to Python param `top_n` automatically. The `Option("--top-n")` explicit flag name is needed to get the hyphenated CLI form.
- **Test patch target for `run_pipeline`** — Must patch `scripts.run_screener.run_pipeline` (the import in the CLI module), not `screener.pipeline.run_pipeline`.

## Open Risks

- **S01 merge conflicts**: If main has changed since S01 branched, merging may require conflict resolution. Low risk — S01 only touches 4 files (model, market_data, pipeline, tests).
- **None**: No other significant risks. This is a display-only + CLI-wiring slice with no computation or API changes.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer | — | none found (standard Python CLI framework, no skill needed) |
| Rich | — | none found (standard Python TUI framework, no skill needed) |

## Sources

- `scripts/run_screener.py` — current CLI structure, Typer option patterns
- `screener/display.py` — current table columns, formatting helpers
- `tests/test_cli_screener.py` — CLI test patterns with CliRunner + mock stack
- `tests/test_display.py` — table rendering test patterns
- `tests/test_options_chain.py:test_yield_column_in_results_table` — precedent for column addition testing
- `git diff main..gsd/M002/S01` — S01 deliverables (perf_1m field, compute_monthly_performance, top_n pipeline param)
