# S02: CLI Flag + Display — Research

**Date:** 2026-03-11

## Summary

S02 is a straightforward wiring slice: add a `--top-n` Typer option to `scripts/run_screener.py` that passes through to `run_pipeline(top_n=N)`, and add a "Perf 1M" column to the Rich results table in `screener/display.py` using the `ScreenedStock.perf_1m` field.

**Critical prerequisite:** S01's code lives on branch `gsd/M002/S01` but has **not been merged** into the current `gsd/M002/S02` branch. The three S01 deliverables S02 depends on — `perf_1m` field on `ScreenedStock`, `compute_monthly_performance()` in `market_data.py`, and `top_n` parameter on `run_pipeline()` — are all absent from the working tree. S02 must merge or cherry-pick S01 before any implementation work begins.

Both changes are mechanically simple with clear precedent in the existing codebase. No new libraries, no architectural decisions, no API calls. Risk is low.

## Recommendation

1. **Merge S01 first.** `git merge gsd/M002/S01` into `gsd/M002/S02` to bring in the `perf_1m` field, `compute_monthly_performance()`, `top_n` parameter, and their tests. Verify all 345+ existing tests still pass after merge.
2. **CLI flag:** Add `--top-n` as a `typer.Option` with `int | None` type, default `None`. Pass it to `run_pipeline(top_n=top_n)`. Follow the exact pattern of the existing `--verbose` and `--preset` options.
3. **Display column:** Insert a "Perf 1M" column into `render_results_table()` between "HV%ile" and "Yield". Format with `fmt_pct()` which already handles sign and None→"N/A".
4. **Tests:** Add CLI flag tests to `tests/test_cli_screener.py` (help text, passthrough to pipeline) and display column tests to `tests/test_display.py` (column header present, value formatting, None handling). Follow existing mock/capture patterns exactly.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option declaration | `typer.Option()` with `Annotated` type hints | Already used for `--verbose`, `--preset`, `--config`, `--update-symbols` |
| Percentage formatting | `display.fmt_pct()` | Handles None→"N/A" and sign; already used for RSI, HV%ile, Yield |
| Console capture in tests | `Console(file=StringIO(), width=120)` | Pattern from every existing display test |
| CLI test invocation | `typer.testing.CliRunner` + `runner.invoke(app, [...])` | Pattern from `test_cli_screener.py` |

## Existing Code and Patterns

- `scripts/run_screener.py:run()` — CLI entry point with 4 existing Typer options. Add `top_n` as 5th option, pass to `run_pipeline()`. The `run_pipeline()` call at line ~87 already passes `option_client` — just add `top_n=top_n`.
- `screener/display.py:render_results_table()` — 12 existing columns. Insert "Perf 1M" column after "HV%ile" (column 10) and before "Yield" (column 11). Use `fmt_pct(stock.perf_1m)` for the row value — identical to `hv_pct_str` pattern.
- `tests/test_cli_screener.py` — 5 existing tests. `test_screener_help()` checks for option text in help output. `test_default_no_file_writes()` patches `run_pipeline` and verifies it was called — extend to check `top_n` kwarg. Pattern: patch all external deps at `scripts.run_screener.*` level.
- `tests/test_display.py:TestRenderResultsTable` — 7 existing tests. `test_table_has_column_headers()` checks column names in captured output. `_make_stock()` helper creates `ScreenedStock` instances — add `perf_1m` parameter.
- `models/screened_stock.py` — (S01 adds) `perf_1m: Optional[float] = None` field after `hv_percentile`. No display-side changes needed to the model.
- `screener/pipeline.py:run_pipeline()` — (S01 adds) `top_n: int | None = None` parameter. S02 just needs to wire the CLI flag to this parameter.

## Constraints

- **S01 merge required first.** Without the `perf_1m` field and `top_n` parameter, S02 code has nothing to wire to.
- `fmt_pct()` returns `"-5.2%"` for negative values — sign is included automatically. The TOPN-05 requirement says "Formatted as percentage with sign (e.g. -5.2%, +3.1%)" — `fmt_pct()` does NOT add a `+` prefix for positive values. Either accept `"5.2%"` for positives (no `+` sign) or create a `fmt_signed_pct()` variant. This is a minor cosmetic decision.
- `typer.Option` type must be `int | None` (not `Optional[int]`) to match the project's Python 3.10+ style used elsewhere.
- Column insertion order matters for visual flow — "Perf 1M" fits logically between "HV%ile" (volatility context) and "Yield" (options premium).

## Common Pitfalls

- **Forgetting to pass `top_n` through in the `run_pipeline()` call** — The CLI flag must be forwarded as a keyword argument. Verify with a test that `mock_pipeline.call_args` includes `top_n=N` when `--top-n N` is passed.
- **Column count mismatch in tests** — Adding a column to the table means `_make_stock()` helper should set `perf_1m` on test stocks to avoid silent "N/A" values that could mask bugs. Update `_make_passing_stocks()` too.
- **Help text for `--top-n` must mention positive integer** — Typer doesn't enforce `> 0` by default for `int | None`. Either add a Typer callback validator or document in help text. The pipeline itself handles `top_n=0` gracefully (empty results), so this is low risk.

## Open Risks

- **S01 merge conflicts.** The S01 branch modifies `pipeline.py`, `market_data.py`, `screened_stock.py`, and both test files. If any of these were modified on the S02 branch independently (unlikely — only `.gsd/` files exist on S02 so far), there could be merge conflicts. Risk: very low.
- **Positive sign display.** Requirement TOPN-05 explicitly shows `+3.1%` but `fmt_pct()` produces `3.1%`. May need a small formatting tweak. Risk: trivial, cosmetic only.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer CLI | — | none found (standard library-level, no skill needed) |
| Rich tables | — | none found (standard library-level, no skill needed) |
| Python/pytest | — | available skills are React/Expo/SwiftUI focused, not relevant |

## Sources

- Codebase inspection: `scripts/run_screener.py`, `screener/display.py`, `tests/test_cli_screener.py`, `tests/test_display.py`
- S01 branch diff: `git diff gsd/M002/S02..gsd/M002/S01` — confirmed all 3 S01 deliverables exist and are well-tested
- Typer 0.24.1 installed; `typer.Option` with `Annotated` pattern already in use
