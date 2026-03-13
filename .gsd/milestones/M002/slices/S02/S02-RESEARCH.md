# S02: CLI Flag + Display — Research

**Date:** 2026-03-12

## Summary

S02 wires the S01 backend (`run_pipeline(top_n=N)`, `ScreenedStock.perf_1m`) into the user-facing layer: a `--top-n` Typer CLI option on `run-screener` and a "Perf 1M" column in the Rich results table. This is low-risk mechanical work — all patterns are established by prior slices (HV%ile column in S08, Yield column in S09, `--verbose`/`--preset` CLI flags in S04/S05).

**Critical prerequisite:** S01's code lives on the `gsd/M002/S01` branch and has NOT been merged into the current `gsd/M002/S02` branch. The three source files changed by S01 (`models/screened_stock.py`, `screener/market_data.py`, `screener/pipeline.py`) plus two test files (`tests/test_market_data.py`, `tests/test_pipeline.py`) must be merged before S02 can begin implementation. A `git merge gsd/M002/S01` should be clean — there are zero overlapping changes.

## Recommendation

Merge S01 first, then implement in two small tasks:

1. **Display column** — Add "Perf 1M" column to `render_results_table()` with a signed-percentage formatter (`+3.1%` / `-5.2%`). Place it after "HV%ile" and before "Yield" since it's a market-data metric. Add tests for column header, value formatting, and N/A handling.

2. **CLI flag** — Add `--top-n` as `Annotated[int | None, typer.Option()]` with `default=None`. Pass through to `run_pipeline(top_n=top_n)`. Add tests for flag parsing, pipeline passthrough, and backward compatibility (no flag → `top_n=None`).

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option parsing | Typer `Annotated[int \| None, typer.Option()]` | Already used for `--config`, `--preset`; consistent UX |
| Rich table column | `table.add_column()` + `table.add_row()` pattern | Identical to HV%ile/Yield columns added in S08/S09 |
| CLI testing | `typer.testing.CliRunner` + `@patch` decorators | 5 existing tests in `test_cli_screener.py` use this exact pattern |
| Display testing | `Console(file=StringIO(), width=200)` capture | Used in `test_display.py` and `test_options_chain.py` display tests |

## Existing Code and Patterns

- `scripts/run_screener.py` — CLI entry point. Four existing `Annotated[..., typer.Option()]` declarations (lines 57-72). `run_pipeline()` call at line 119 already passes all other kwargs — just add `top_n=top_n`.
- `screener/display.py:render_results_table()` — 12 columns currently. Pattern: `table.add_column(name, justify)` then per-row formatting. HV%ile (line 190) and Yield (line 191) added by S08/S09 are the exact precedent.
- `screener/display.py:fmt_pct()` — Returns `f"{value:.1f}%"`. Does NOT include explicit `+` sign for positive values. TOPN-05 requires signed format (`+3.1%`), so need a new `fmt_signed_pct()` helper or inline format.
- `tests/test_cli_screener.py` — 5 CLI tests using `CliRunner` + heavy `@patch` stacking. The `test_default_no_file_writes` test (line 41) is the template for "flag passthrough" testing.
- `tests/test_display.py:_make_stock()` — Helper that builds a `ScreenedStock` for display tests. Does NOT currently accept `perf_1m` kwarg — must be extended or set directly on the returned object.
- `tests/test_options_chain.py:test_yield_column_in_results_table()` (line 637) — Exact pattern for testing a new display column: make stock, set field, render, assert column header + formatted value in output.
- `models/screened_stock.py` — `perf_1m: Optional[float] = None` field added by S01 (on S01 branch). S02 reads it, doesn't modify the model.

## Constraints

- **S01 merge required first** — `perf_1m` field, `compute_monthly_performance()`, and `run_pipeline(top_n=)` parameter exist only on `gsd/M002/S01` branch. No S02 code can compile without this merge.
- **`top_n` type must be `int | None`** — Typer needs `None` default to mean "no cap" (TOPN-06 backward compatibility). Using `0` as sentinel would be semantically wrong.
- **Column order matters** — "Perf 1M" is a price-based metric from Alpaca bar data (Stage 1). Place after HV%ile (also Stage 1 data) and before Yield (Stage 3 data) to maintain data-source ordering.
- **Signed percentage format** — TOPN-05 spec says `+3.1%` / `-5.2%`. The existing `fmt_pct()` only shows `-` (Python default). A new helper is needed — don't modify `fmt_pct()` since HV%ile, RSI, and Yield are always positive and shouldn't show `+`.
- **345 existing tests must still pass** — verified at 345 tests collected as of current HEAD.

## Common Pitfalls

- **Typer `int | None` default** — Typer before 0.9.0 had issues with `Optional[int]` defaults. Current pin is `typer>=0.9.0` (pyproject.toml line 24). Use `Annotated[int | None, typer.Option("--top-n", ...)] = None` — the same pattern as `preset: PresetName | None`.
- **Forgetting to pass `top_n` through** — The `run_pipeline()` call (line 119) has 6 kwargs already. Easy to forget adding `top_n=top_n`. The CLI test must assert the kwarg reaches `run_pipeline`.
- **Display `_make_stock()` helper lacks `perf_1m`** — The test helper in `test_display.py` builds a `ScreenedStock` but doesn't accept `perf_1m`. Either extend the helper or set `stock.perf_1m = value` after construction. Setting directly is simpler and doesn't break existing callers.
- **`_all_pass_filters()` in test_display.py** — Returns filter results for known filter names. If new display tests need full-pass stocks, this helper already works since `perf_1m` is display-only (not a filter).

## Open Risks

- **S01 branch merge conflicts** — While no overlapping source changes exist, `.gsd/` state files may conflict. These are non-code and resolvable trivially. Source file merge should be clean (verified: zero shared hunks).
- **Typer `int | None` edge case with `--top-n 0`** — Should `--top-n 0` be treated as "process zero stocks"? Likely a validation concern. Consider adding a Typer `min=1` constraint or documenting that 0 is degenerate. Minimal risk since user would need to intentionally pass 0.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer | — | none found (stdlib-level; no skill needed) |
| Rich | — | none found (stdlib-level; no skill needed) |
| Python/pytest | — | already installed patterns; no skill needed |

No skills are relevant — this slice uses only project-internal patterns (Typer CLI, Rich tables, pytest) that are already well-established in the codebase.

## Sources

- `scripts/run_screener.py` — current CLI structure with 4 Typer options
- `screener/display.py` — current 12-column results table with formatting helpers
- `tests/test_cli_screener.py` — 5 existing CLI tests with CliRunner + patch pattern
- `tests/test_display.py` — 45 display tests including column header and row format tests
- `tests/test_options_chain.py:637-690` — Yield column display test (precedent for new column test)
- `gsd/M002/S01` branch — S01 deliverables: `perf_1m` field, `compute_monthly_performance()`, `run_pipeline(top_n=)`, 6 math + 6 pipeline tests
- `.gsd/DECISIONS.md` — D042 (top_n CLI-only), D044 (None perf sorts last)
