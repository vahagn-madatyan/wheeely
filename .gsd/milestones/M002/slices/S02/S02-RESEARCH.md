# S02: CLI Flag + Display — Research

**Date:** 2026-03-11

## Summary

S02 wires the S01 backend (`top_n` parameter, `perf_1m` field) to the user-facing surface: a `--top-n` CLI flag on `run-screener` and a "Perf 1M" column in the Rich results table. This is low-risk, mechanically straightforward work with clear patterns to follow from existing CLI options and display columns.

The S01 branch (`gsd/M002/S01`) has not been merged into the current `gsd/M002/S02` branch. S02 must merge S01 first to get `run_pipeline(top_n=...)`, `ScreenedStock.perf_1m`, and `compute_monthly_performance()`. After that merge, the work is three discrete changes: (1) add `--top-n` Typer option, (2) pass it to `run_pipeline()`, (3) add "Perf 1M" column to the results table — plus tests for each.

One nuance: the TOPN-05 requirement specifies signed percentage format (e.g. `-5.2%`, `+3.1%`), but the existing `fmt_pct()` formatter does not include a `+` prefix for positive values. A dedicated `fmt_signed_pct()` function avoids changing behavior of the 6+ existing `fmt_pct()` call sites.

## Recommendation

Merge `gsd/M002/S01` into `gsd/M002/S02`, then implement three small changes:

1. **CLI flag**: Add `top_n: Annotated[int | None, typer.Option("--top-n", ...)] = None` to `run()` in `scripts/run_screener.py`, pass it to `run_pipeline(..., top_n=top_n)`.
2. **Display column**: Add `fmt_signed_pct()` helper and a "Perf 1M" column in `render_results_table()`, positioned after "HV%ile" and before "Yield".
3. **Tests**: CLI flag parsing test (verifies `run_pipeline` receives `top_n` kwarg), display column test (verifies "Perf 1M" appears with signed formatting), backward-compat test (no flag → `top_n=None`).

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option parsing | Typer `typer.Option` with `Annotated` | Project convention (see existing 4 options in `run_screener.py`) |
| Rich table columns | `table.add_column()` + `table.add_row()` | Existing pattern in `render_results_table()` |
| Test CLI invocations | `typer.testing.CliRunner` | Already used in `test_cli_screener.py` |
| Console capture for display tests | `Console(file=StringIO(), width=120)` | Pattern in `test_display.py:_capture_console()` |

## Existing Code and Patterns

- `scripts/run_screener.py:run()` — CLI entry point; follow existing `Annotated[..., typer.Option(...)]` pattern for `--top-n`. The `run_pipeline()` call at line 119 needs `top_n=top_n` kwarg added.
- `screener/display.py:render_results_table()` — Add column between "HV%ile" and "Yield". Follow the `hv_pct_str` pattern for conditional formatting. Needs `fmt_signed_pct()` helper since existing `fmt_pct()` omits `+` prefix.
- `screener/display.py:fmt_pct()` — Returns `f"{value:.1f}%"` (no sign for positive). Don't modify — 6+ call sites rely on unsigned formatting for RSI, margins, etc.
- `tests/test_cli_screener.py` — Patch-heavy CLI tests. `test_default_no_file_writes` shows the full mock stack. New `--top-n` test should verify `run_pipeline` is called with `top_n=N` kwarg.
- `tests/test_display.py:_make_stock()` — Helper for building `ScreenedStock` fixtures. Needs `perf_1m` parameter added.
- `tests/test_display.py:TestRenderResultsTable` — Column header assertion at `test_table_has_column_headers` checks all column names. Must add "Perf 1M" to the assertion list.
- `models/screened_stock.py` — `perf_1m: Optional[float]` field added by S01 (on `gsd/M002/S01` branch, not yet merged).
- `screener/pipeline.py:run_pipeline()` — `top_n: int | None = None` parameter added by S01 (on `gsd/M002/S01` branch).

## Constraints

- S01 branch must be merged before any implementation — `perf_1m` field and `top_n` parameter don't exist on current branch.
- `--top-n` must accept positive integers only. Typer's `int` type handles parsing; consider `min=1` validation or let pipeline handle naturally.
- `top_n=None` (no flag) must produce identical behavior to current codebase — backward compatibility per TOPN-06.
- `fmt_pct()` must not be modified — existing callers (RSI, margins, growth, HV%ile, yield) expect unsigned format.
- Column order in the table matters for readability — "Perf 1M" logically belongs near technical indicators, between "HV%ile" and "Yield".
- 345 existing tests must continue to pass after changes.

## Common Pitfalls

- **Breaking `fmt_pct()` callers** — Adding `+` sign to `fmt_pct()` would change output for RSI, margins, etc. Use a separate `fmt_signed_pct()` instead.
- **Forgetting to merge S01** — The `perf_1m` field and `top_n` parameter don't exist on the current branch. Implementation will fail without the merge.
- **CLI test mock stack order** — `test_cli_screener.py` uses stacked `@patch` decorators. The parameter order in the test function is reversed from decorator order (bottom decorator = first parameter). Adding a new patch requires careful ordering.
- **Typer `--top-n` hyphen handling** — Typer converts `--top-n` (kebab-case) to `top_n` (snake_case) for the Python parameter name. The Annotated pattern handles this, but the parameter name must be `top_n` not `top_n_`.

## Open Risks

- **S01 merge conflicts** — If `gsd/M002/S02` has diverged from `gsd/M002/S01`'s base, the merge could have conflicts in `pipeline.py` or `screened_stock.py`. Risk is low since S02 hasn't modified those files.
- **S01 placeholder summary** — The S01 summary is a doctor-created placeholder. The actual S01 code changes are verified by diffing `main..gsd/M002/S01` (done during this research). The code is correct and complete.

## Requirements Covered

| Requirement | This Slice's Role | Implementation Surface |
|-------------|-------------------|----------------------|
| TOPN-01 | Primary owner | `--top-n` CLI flag in `scripts/run_screener.py` |
| TOPN-05 | Primary owner | "Perf 1M" column in `screener/display.py:render_results_table()` |
| TOPN-06 | Primary owner | `top_n=None` default → no cap (backward compatible) |

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer CLI | `narumiruna/agent-skills@python-cli-typer` | available (13 installs) — not needed, project patterns are clear |
| Rich | — | none found — not needed, existing display code is the reference |

## Sources

- S01 diff: `git diff main..gsd/M002/S01` — verified `perf_1m` field, `compute_monthly_performance()`, `top_n` parameter, two-pass pipeline architecture, and 6 new tests
- Existing CLI pattern: `scripts/run_screener.py` lines 55-72 — Annotated + typer.Option convention
- Existing display pattern: `screener/display.py` lines 162-217 — column definitions and row formatting
- Existing test patterns: `tests/test_cli_screener.py` and `tests/test_display.py` — mock stacks and console capture
