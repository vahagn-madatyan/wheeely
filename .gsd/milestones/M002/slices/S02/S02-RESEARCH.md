# S02: CLI Flag + Display — Research

**Date:** 2026-03-11

## Summary

S02 is a low-risk terminal slice adding three things: a `--top-n` Typer CLI option on `run-screener`, a "Perf 1M" column in the Rich results table, and tests for both. All upstream plumbing exists on the `gsd/M002/S01` branch — `run_pipeline(top_n=N)` parameter, `ScreenedStock.perf_1m` field, and `compute_monthly_performance()`. S02 just wires the CLI flag to the pipeline parameter and reads `perf_1m` from `ScreenedStock` into a new display column.

The current `gsd/M002/S02` branch does **not** have S01's changes merged yet. S01 must be merged (or rebased onto) before S02 implementation begins, otherwise `top_n` and `perf_1m` won't exist in the codebase.

## Recommendation

1. Merge `gsd/M002/S01` into `gsd/M002/S02` first.
2. Add `--top-n` as an `Annotated[int | None, typer.Option()]` parameter following the existing CLI pattern, passing it through to `run_pipeline(top_n=top_n)`.
3. Add "Perf 1M" column to `render_results_table()` using the existing `fmt_pct()` helper with sign prefix.
4. Write tests following established patterns in `test_cli_screener.py` (mock-heavy Typer runner tests) and `test_display.py` (StringIO console capture).

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option parsing | Typer `Annotated[..., typer.Option()]` | Already used for all 4 existing flags |
| Percentage formatting | `screener.display.fmt_pct()` | Returns "N/A" for None, handles sign |
| Console capture in tests | `Console(file=StringIO(), width=120)` | Pattern used in all 46 display tests |
| CLI test invocation | `typer.testing.CliRunner` | Pattern used in all 5 CLI screener tests |

## Existing Code and Patterns

- `scripts/run_screener.py:run()` — 4 existing `Annotated` Typer options. Add `top_n` the same way. The `run_pipeline()` call already passes `option_client=broker.option_client`; add `top_n=top_n` alongside it.
- `screener/display.py:render_results_table()` — 12 existing columns. "Perf 1M" inserts naturally after "HV%ile" and before "Yield". Use `fmt_pct()` but need sign prefix (e.g. "+3.1%", "-5.2%") — `fmt_pct()` currently does not add `+` for positive values, so either extend it or format inline.
- `tests/test_cli_screener.py` — 5 tests using `CliRunner` + `@patch` on module-level imports. Pattern: patch `run_pipeline`, `FinnhubClient`, `require_finnhub_key`, `create_broker_client`, `progress_context`, `render_*` functions. Add test that `--top-n 20` passes `top_n=20` to `run_pipeline()`.
- `tests/test_display.py` — `_make_stock()` helper, `_all_pass_filters()`, `_capture_console()`. Add `perf_1m` kwarg to `_make_stock()`, add test that "Perf 1M" column appears in output.
- `models/screened_stock.py` — `perf_1m: Optional[float]` already exists on S01 branch. No model changes needed in S02.
- `screener/pipeline.py:run_pipeline(top_n=None)` — Already exists on S01 branch. No pipeline changes needed in S02.

## Constraints

- S01 branch must be merged into S02 before implementation — `perf_1m` field and `top_n` parameter don't exist on current branch.
- `--top-n` must accept positive integers only; `None` when omitted (backward compatible per TOPN-06).
- Typer doesn't have built-in `min` validation on `int` options — need manual validation or Typer callback to reject `--top-n 0` or negative values.
- The `_make_stock()` helper in `test_display.py` doesn't currently accept `hv_percentile` or `put_premium_yield` kwargs — it was written before those columns were added. Need to extend it for `perf_1m` (and optionally backfill the other missing kwargs).
- The `_all_pass_filters()` helper doesn't include `hv_percentile` or `earnings_proximity` filter names — current branch is behind S01. After merge, these will be present on the S01 version. Need to verify the test helper matches the actual filter set.

## Common Pitfalls

- **Forgetting sign prefix on Perf 1M** — `fmt_pct()` outputs "3.1%" for positive values, but the requirement says "+3.1%". Either add a sign-aware variant or format inline with `f"{value:+.1f}%"`.
- **Typer Option name collision** — `--top-n` with a hyphen maps to Python param `top_n` via Typer's auto-conversion. This works by default; no special handling needed.
- **Stale test helpers after S01 merge** — `_all_pass_filters()` in `test_display.py` currently has 11 filter names. S01 branch adds `hv_percentile` and `earnings_proximity` to the pipeline. After merge, display tests may fail if the helper doesn't match the actual filter set. Verify and update.
- **top_n=0 edge case** — Should be rejected (zero stocks makes no sense). Validate at CLI level.
- **Mock depth in CLI tests** — The existing pattern patches 8 decorators deep. Adding `top_n` only requires verifying it's passed through to `run_pipeline()` — no new mocks needed, just asserting `mock_pipeline.call_args`.

## Open Risks

- **S01 merge conflicts** — S01 modified `screener/pipeline.py` heavily (restructured `run_pipeline` into two-pass architecture). If current branch has any divergent edits to the same file, merge will conflict. Low risk since S02 branch appears to only have `.gsd/` changes so far.
- **Display test fragility** — `_all_pass_filters()` and `_make_stock()` helpers are tightly coupled to the exact set of filter names and stock fields. Adding a column without updating helpers will cause false test failures.

## Requirements Coverage

| Requirement | Owned by S02? | Implementation Target |
|-------------|---------------|----------------------|
| TOPN-01 | Primary owner | `scripts/run_screener.py` — `--top-n` option |
| TOPN-05 | Primary owner | `screener/display.py` — "Perf 1M" column |
| TOPN-06 | Primary owner | `scripts/run_screener.py` — omitting flag = no cap |

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer | N/A | none found — simple API, no skill needed |
| Rich | N/A | none found — existing patterns sufficient |

## Sources

- `scripts/run_screener.py` — existing CLI option patterns (4 Annotated Typer options)
- `screener/display.py` — existing column structure and formatting helpers
- `tests/test_cli_screener.py` — 5 existing CLI tests with CliRunner + mock patterns
- `tests/test_display.py` — 46 existing display tests with console capture pattern
- `git diff gsd/M001/S07..gsd/M002/S01` — S01 changes: `perf_1m` field, `top_n` param, `compute_monthly_performance()`, two-pass pipeline, 5 pipeline top-n tests
