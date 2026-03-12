# S02: CLI Flag + Display — Research

**Date:** 2026-03-11

## Summary

S02 is the terminal slice for M002. It wires the `top_n` pipeline parameter (built in S01) to the CLI via a `--top-n` Typer option, and adds a "Perf 1M" column to the Rich results table showing each stock's 1-month performance percentage.

All S01 code changes exist on the `gsd/M002/S01` branch but are **not yet merged** into the current `gsd/M002/S02` branch. The diff confirms: `perf_1m` field on ScreenedStock, `compute_monthly_performance()` in market_data.py, `top_n` parameter on `run_pipeline()`, and 6 pipeline tests + 6 perf computation tests — all present on S01, absent on S02. **S02 must merge S01 first** before any implementation can work.

The actual S02 work is straightforward: one new CLI option (~5 lines), one new table column (~4 lines), and tests for both. No architectural decisions, no new dependencies, no API calls.

## Recommendation

Merge `gsd/M002/S01` into `gsd/M002/S02` as the first task. Then implement:

1. **CLI flag** — Add `--top-n` Typer `Option` to `scripts/run_screener.py:run()`, pass it through to `run_pipeline(top_n=N)`. Follow the existing pattern of `--verbose`, `--preset`, etc.
2. **Display column** — Add "Perf 1M" column to `render_results_table()` in `screener/display.py`. Format with sign prefix: `+3.1%`, `-5.2%`. Place after "HV%ile" and before "Yield" (logically groups technical indicators together).
3. **Tests** — CLI tests in `test_cli_screener.py` (flag parsed, passed to pipeline, help text). Display tests in `test_display.py` (column present, None handling, sign formatting).

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI flag definition | Typer `Option` with type annotation | Already used for `--verbose`, `--preset`, `--config`, `--update-symbols` |
| Percentage formatting | `fmt_pct()` in `screener/display.py` | Already formats `X.X%`; need sign-aware variant or inline formatting for `+/-` |
| Test CLI invocation | `typer.testing.CliRunner` | Already used in `test_cli_screener.py` with established mock pattern |
| Console capture in tests | `Console(file=StringIO(), width=120)` via `_capture_console()` | Already used in `test_display.py` |

## Existing Code and Patterns

- `scripts/run_screener.py` — CLI entry point with Typer app. All options use `Annotated[type, typer.Option(...)]` pattern. The `run_pipeline()` call at line 119 is where `top_n=N` must be passed through.
- `screener/display.py:render_results_table()` — Rich table with 13 columns. Columns added via `table.add_column()`, rows via `table.add_row()`. HV%ile and Yield columns were added in S08/S09 (M001) using the same pattern S02 will follow.
- `tests/test_cli_screener.py` — 5 existing tests. `test_default_no_file_writes` is the reference pattern: patches 8 module-level imports, invokes with `runner.invoke(app, [])`, asserts on `mock_pipeline.assert_called_once()`. S02's test will assert `top_n=N` appears in the pipeline call kwargs.
- `tests/test_display.py` — 45 existing tests. `_make_stock()` helper creates ScreenedStock with specified fields. `test_table_has_column_headers` checks column names in output. S02 will add `perf_1m` kwarg to `_make_stock()` and assert "Perf 1M" appears.
- `screener/display.py:fmt_pct()` — Formats `float → "X.X%"`. Does NOT include sign prefix. For "Perf 1M" we need `+3.1%` / `-5.2%` formatting. Options: (a) new `fmt_signed_pct()` helper, or (b) inline format string. Prefer (a) for consistency.
- `models/screened_stock.py` — ScreenedStock will gain `perf_1m` from S01 merge. No additional field changes needed for S02.

## Constraints

- **S01 merge required** — Current S02 branch lacks `perf_1m` field, `compute_monthly_performance()`, and `top_n` parameter. These must be present before any S02 code can reference them.
- **`top_n` type must be `int | None`** — Typer maps this to an optional integer flag. When omitted, `None` passes through to pipeline (backward compatible, per TOPN-06/D042).
- **Column count already high (13)** — Adding "Perf 1M" makes 14 columns. Terminal width ~120 chars may wrap. Place column strategically (after HV%ile, near other technicals) and keep header short.
- **Test count** — Currently 345+ tests across the project (67 in test_pipeline.py alone). S01 added ~12 more. All must continue passing.
- **`fmt_pct` doesn't show sign** — It uses `f"{value:.1f}%"` which shows `-5.2%` but not `+3.1%`. Need explicit sign formatting for "Perf 1M" to distinguish positive from negative performance at a glance.

## Common Pitfalls

- **Forgetting `top_n` in pipeline call kwargs** — The `run_pipeline()` call in `run_screener.py` already has 6 keyword args. Easy to add `top_n` to the function signature but forget to wire it through in the actual call. Test must assert on `call_kwargs`.
- **Typer `None` default gotcha** — `typer.Option(None)` with `int | None` annotation works correctly in Typer ≥0.9. The existing `preset: PresetName | None = None` pattern confirms this works. Follow the same pattern.
- **Mock stack order in CLI tests** — `test_default_no_file_writes` uses 8 stacked `@patch` decorators. Python applies them bottom-up, so the function parameter order is reversed from decorator order. Adding a new `@patch` or modifying call assertions requires careful attention to parameter mapping.
- **Display test `_make_stock` helper** — Currently lacks `perf_1m` parameter. Must be extended to accept it, otherwise new display tests can't set the field on ScreenedStock.

## Open Risks

- **S01 merge conflict** — The S02 branch has had multiple auto-commits (research). If any touched `pipeline.py`, `market_data.py`, or `screened_stock.py`, the S01 merge could conflict. Risk is low since S02 auto-commits are only `.gsd/` artifacts, but should verify.
- **S01 placeholder summary** — S01's summary is a doctor-created placeholder. Task summaries are the authoritative source. If S01 had implementation gaps, they'd surface during merge/test. The S01 branch diff shows complete implementation with 12 tests, so this risk is low.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer (CLI) | — | none found (no installed skill; standard library, docs not needed) |
| Rich (tables) | — | none found (no installed skill; pattern already established in codebase) |
| Python/pytest | — | none found (standard tooling, well-established patterns in project) |

No skill discovery needed — this slice uses only Typer and Rich, both already established with clear patterns in the codebase.

## Sources

- `scripts/run_screener.py` — Current CLI structure, Typer option patterns, pipeline call site
- `screener/display.py` — Current table columns, formatting helpers, render_results_table implementation
- `tests/test_cli_screener.py` — Existing CLI test patterns with CliRunner and mock stacks
- `tests/test_display.py` — Display test helpers (_make_stock, _capture_console), column assertion pattern
- `git diff main..gsd/M002/S01` — Full S01 implementation diff confirming perf_1m, top_n, compute_monthly_performance, and 12 new tests
- `git diff gsd/M002/S01..gsd/M002/S02` — Confirms S01 changes not yet on S02 branch
