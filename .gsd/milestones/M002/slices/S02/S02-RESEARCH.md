# S02: CLI Flag + Display — Research

**Date:** 2026-03-12

## Summary

S02 adds the `--top-n` CLI flag to `run-screener` and a "Perf 1M" column to the Rich results table. It owns requirements TOPN-01 (CLI flag), TOPN-05 (display column), and TOPN-06 (backward compat).

**Critical finding: S01 code exists but is not merged.** S01's implementation is complete on the `gsd/M002/S01` branch (2 feat commits: `perf_1m` field + `compute_monthly_performance()` in T01, pipeline two-pass split + `top_n` sort/cap in T02, plus 12 new tests). However, S01 was never squash-merged to main. Both S01 and S02 forked from the same main commit (`cd06247`). **S02's first task must merge S01's changes into this branch** before adding CLI and display work.

After the merge, S02's own scope is small: one new Typer option, one new table column, and ~8-10 new tests. All 345 existing tests pass on the current branch; S01's branch brings the count to 351 (345 + 6 perf math tests; S01 also modified 6 existing pipeline tests to accommodate the two-pass split).

## Recommendation

Execute in this order:

1. **Merge S01** — `git merge gsd/M002/S01` into `gsd/M002/S02`. Resolve any conflicts (expected only in `.gsd/` metadata files — source code should merge cleanly since S02 has no source changes yet). Run full test suite to confirm 351+ tests pass.
2. **CLI flag** — Add `--top-n` Typer option to `scripts/run_screener.py` (positive int, default None), pass through to `run_pipeline(top_n=N)`.
3. **Display column** — Add "Perf 1M" column to `render_results_table()` in `screener/display.py` between "HV%ile" and "Yield". Use a local `fmt_signed_pct()` helper for `+3.1%` / `-5.2%` formatting.
4. **Tests** — CLI flag parsing (help text, passthrough to pipeline), display column (header present, values formatted, None → "N/A"), backward compat (no flag = no cap).

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Percentage formatting | `screener.display.fmt_pct()` | Handles `None` → "N/A" and `{value:.1f}%`; extend with sign prefix for perf display |
| CLI option parsing | Typer `Annotated[int \| None, typer.Option()]` | Matches 4 existing options in `run_screener.py` |
| Console capture in tests | `Console(file=StringIO(), width=120)` | Established in `test_display.py` |
| CLI test pattern | `typer.testing.CliRunner` + `@patch` stack | Established in `test_cli_screener.py` (5 tests) |

## Existing Code and Patterns

- `scripts/run_screener.py` — CLI uses `Annotated[type, typer.Option()]` for all flags. The `run_pipeline()` call at line ~108 passes keyword args. `--top-n` follows the exact same pattern. Note: Typer does not accept `int | None` union syntax directly for CLI options; use `Optional[int]` with `typer.Option("--top-n", ...)`.
- `screener/display.py:render_results_table()` — Columns added via `table.add_column()` at lines 184-196, row values via `table.add_row()` at lines 201-216. "Perf 1M" inserts after "HV%ile" (line 190) and before "Yield" (line 191).
- `screener/display.py:fmt_pct()` — Returns `f"{value:.1f}%"` for non-None values, `"N/A"` for None. Does NOT include `+` prefix for positives. A dedicated `fmt_signed_pct()` avoids touching 4 existing callers.
- `models/screened_stock.py` — After S01 merge, gains `perf_1m: Optional[float] = None` at line 40. Already follows the pattern of optional float fields.
- `screener/pipeline.py` — After S01 merge, has `top_n: int | None = None` param, two-pass architecture, and sort/cap logic between passes. The `run()` CLI function just needs to pass `top_n=top_n` to `run_pipeline()`.
- `tests/test_cli_screener.py` — 5 tests using `CliRunner`. `test_verbose_shows_filter_breakdown` is the closest pattern for testing `--top-n` flag passthrough (verifies a specific kwarg was forwarded to `run_pipeline`).
- `tests/test_display.py` — `_make_stock()` helper at line 30 needs `perf_1m` parameter added. Column header test at line 205 checks `for col in [...]`.
- `tests/test_market_data.py` — After S01 merge, has `TestMonthlyPerformance` class with 6 tests. No new market_data tests needed for S02.
- `tests/test_pipeline.py` — After S01 merge, has 6 new top_n/perf tests (73 total, up from 67). No new pipeline tests needed for S02.

## Constraints

- **S01 merge is prerequisite** — All S02 work depends on `perf_1m` field, `compute_monthly_performance()`, and `run_pipeline(top_n=)` existing in the working tree.
- **Typer int|None syntax** — Typer requires `Optional[int]` with explicit `None` default, not `int | None` union. See existing `preset` param pattern (`PresetName | None` works because it's an Enum, but raw `int | None` needs `Optional[int]`).
- **top_n must be positive** — Add validation: if user passes `--top-n 0` or negative, error early. Typer's `min=1` constraint or a manual check.
- **Sign formatting** — `fmt_pct()` returns `"-5.2%"` for negatives but `"5.2%"` for positives (no `+`). Perf column wants `"+5.2%"`. Use `f"{value:+.1f}%"` format spec (Python's `+` sign flag).
- **Backward compat (TOPN-06)** — All 345 existing tests call CLI/pipeline without `--top-n`. They must pass unchanged after this slice.

## Common Pitfalls

- **Merge conflicts in `.gsd/` files** — S01 and S02 both touched `.gsd/` metadata. Accept S02's versions (current branch) for state/roadmap files since S02 is the later state.
- **`_make_stock()` missing `perf_1m` kwarg** — `test_display.py`'s helper doesn't accept `perf_1m`. New display tests must either extend the helper or set the attribute directly after construction.
- **Pipeline mock missing `top_n` kwarg check** — Existing `test_default_no_file_writes` asserts `mock_pipeline.assert_called_once()` but doesn't check kwargs. The new test for `--top-n` should verify `top_n=N` is in the call kwargs.
- **Typer `--top-n` hyphen vs underscore** — Typer auto-converts `top_n` parameter to `--top-n` CLI flag. The function parameter must be `top_n` (underscore), and the CLI flag will be `--top-n` (hyphen). This is standard Typer behavior.

## Open Risks

- **S01 merge may have test failures** — S01's pipeline restructure changed progress callback patterns (totals changed from `len(universe)` to `len(stage1_survivors)` for post-cap stages). Two existing progress tests may have been updated on S01's branch, but verify after merge.
- **S01 branch may be stale** — If main has received commits since S01 forked, the merge into S02 could conflict in source files. The git log shows both branches fork from the same commit, so this is unlikely but worth checking at merge time.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer (Python CLI) | none relevant | Low-install-count skill found; not recommended — codebase has established patterns |
| Rich (terminal UI) | none found | none found |

No skills recommended for installation. The codebase has 5 CLI tests and 30+ display tests as reference.

## Sources

- `gsd/M002/S01` branch: 2 feat commits (`815541d`, `94af363`) with 12 new tests, fully implements TOPN-02/03/04
- `scripts/run_screener.py`: 4 existing Typer options as pattern reference
- `screener/display.py`: `render_results_table()` with 12 existing columns
- `tests/test_cli_screener.py`: 5 tests using `CliRunner` + `@patch` pattern
- `tests/test_display.py`: 30+ tests with `_make_stock()` / `_capture_console()` helpers
- Decision register: D041 (22-day lookback), D042 (CLI-only flag), D043 (cap after Stage 1), D044 (None sorts last)
