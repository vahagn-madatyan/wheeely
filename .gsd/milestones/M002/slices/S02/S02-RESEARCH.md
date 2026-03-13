# S02: CLI Flag + Display — Research

**Date:** 2026-03-12

## Summary

S02 is a low-risk, purely additive slice that wires S01's pipeline changes (`top_n` parameter, `perf_1m` field) into the user-facing CLI and display layers. Three touch points: (1) add a `--top-n` Typer option to `scripts/run_screener.py` and pass it through to `run_pipeline()`, (2) add a "Perf 1M" column to the Rich results table in `screener/display.py`, and (3) tests for both.

The codebase has well-established patterns for both changes. The CLI already has four Typer options (`--update-symbols`, `--verbose`, `--preset`, `--config`) using `Annotated` type hints, and tests use `typer.testing.CliRunner` with heavy `@patch` decorators. The display module already has 13 table columns with formatters (`fmt_pct`, `fmt_price`, etc.) and a consistent `_capture_console()` test pattern. This slice follows existing conventions exactly — no architectural decisions needed.

**Critical dependency note:** S01's code exists on branch `gsd/M002/S01` but has NOT been merged into the current `gsd/M002/S02` branch. The S02 branch currently lacks `perf_1m` on `ScreenedStock`, `compute_monthly_performance()` in `market_data.py`, and the `top_n` parameter on `run_pipeline()`. S01 changes must be merged or cherry-picked before S02 implementation can begin.

## Recommendation

Follow existing patterns exactly:

1. **Merge S01 first** — Cherry-pick or merge `gsd/M002/S01` into `gsd/M002/S02` to get the `perf_1m` field, `compute_monthly_performance()`, `top_n` pipeline parameter, and S01 tests.
2. **CLI flag** — Add `--top-n` as a `typer.Option` with `int | None` type and `None` default, matching the `--preset` pattern. Pass directly to `run_pipeline(top_n=top_n)`.
3. **Display column** — Insert "Perf 1M" column between "HV%ile" and "Yield" (logical grouping: technical indicators before options data). Use existing `fmt_pct()` for formatting, with sign prefix for clarity (e.g., `-5.2%`, `+3.1%`).
4. **Tests** — Add to existing `test_cli_screener.py` and `test_display.py` following their exact patterns.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option definition | `typer.Option` with `Annotated` type hints | Already used for all 4 existing options; consistent API |
| Percentage formatting | `screener.display.fmt_pct()` | Already handles None→"N/A", consistent decimal place |
| Console capture for tests | `Console(file=StringIO(), width=120)` pattern | All display tests use this; proven isolation |
| CLI test runner | `typer.testing.CliRunner` | All CLI tests use this; captures output + exit code |

## Existing Code and Patterns

- `scripts/run_screener.py:run()` — CLI entry point; add `top_n` parameter here following the `Annotated[..., typer.Option(...)]` pattern on lines 56-72. Pass to `run_pipeline()` call on line 113.
- `screener/display.py:render_results_table()` — Lines 181-193 define columns, lines 202-215 build rows. Insert "Perf 1M" column at line 191 (after HV%ile, before Yield). Add `perf_1m` value to `add_row()` call.
- `screener/display.py:fmt_pct()` — Returns `"{value:.1f}%"` or `"N/A"`. Works for `perf_1m` but needs sign prefix for positive values. Consider a `fmt_signed_pct()` or inline formatting.
- `tests/test_cli_screener.py` — Uses `CliRunner`, `@patch` stack targeting `scripts.run_screener.*` (D019 pattern). Test pattern: invoke CLI → assert exit code → assert mock calls.
- `tests/test_display.py:_make_stock()` — Helper builds `ScreenedStock` with specific fields. Must add `perf_1m` parameter.
- `tests/test_display.py:_all_pass_filters()` — Returns filter list for passing stocks. May need `hv_percentile` filter added (currently missing from the list but HV%ile column exists — check if this causes issues).
- `models/screened_stock.py` — `perf_1m: Optional[float]` field will exist after S01 merge (line 40 on S01 branch).
- `screener/pipeline.py:run_pipeline()` — `top_n: int | None = None` parameter will exist after S01 merge (line 1199 on S01 branch).

## Constraints

- **S01 merge required** — Current branch lacks `perf_1m` field, `compute_monthly_performance()`, and `top_n` pipeline parameter. Must merge S01 before any S02 code changes.
- **Column ordering matters** — Rich Table columns must match `add_row()` positional arguments exactly. Adding a column requires adding the corresponding value in the same position in every `add_row()` call.
- **`fmt_pct()` lacks sign prefix** — Current `fmt_pct(-5.2)` returns `"-5.2%"` (negative sign from Python formatting), but `fmt_pct(3.1)` returns `"3.1%"` (no plus sign). TOPN-05 specifies sign format (`+3.1%`). Need a small formatting helper or inline `f"+{v:.1f}%"` logic.
- **Typer `int | None` default** — `typer.Option` with `None` default requires explicit annotation. Pattern: `Annotated[int | None, typer.Option("--top-n", ...)] = None`.
- **Backward compatibility** — `top_n=None` must produce identical behavior to current (no cap). Tests must verify pipeline called without `top_n` when flag omitted.
- **345 existing tests** — All must continue passing after changes.

## Common Pitfalls

- **Column/row positional mismatch** — Adding a column without adding the corresponding value in `add_row()` shifts all subsequent columns. Count carefully: new column goes at position 11 (0-indexed), value at the same position in the `add_row()` call.
- **Patching `run_pipeline` in CLI tests** — The mock target must be `scripts.run_screener.run_pipeline` (not `screener.pipeline.run_pipeline`) because the CLI uses a module-level import (D019). Same applies to any new imports.
- **Typer `None` default with int** — Typer needs `int | None` (not `Optional[int]`) in the `Annotated` type hint for proper CLI argument parsing. The existing `PresetName | None` pattern on line 67 confirms this works.
- **`_all_pass_filters()` in test_display.py** — Currently missing `hv_percentile` and `earnings_proximity` in its filter list (lines 62-67). The `_all_pass_filters` helper returns specific filter names — if any display logic checks for these filters, tests could have subtle issues. Verify this doesn't affect the new tests.

## Open Risks

- **S01 merge conflicts** — S01 modifies `pipeline.py` extensively (two-pass refactor), `screened_stock.py` (new field), `market_data.py` (new function), and adds `tests/test_pipeline.py` changes. Merge into S02 branch could conflict if S02 branch has diverged. Risk is low since S02 branch has no code changes yet.
- **Sign formatting decision** — TOPN-05 says "Formatted as percentage with sign (e.g. -5.2%, +3.1%)". The existing `fmt_pct()` doesn't add `+` prefix. Need to decide: modify `fmt_pct()` globally (risks changing existing column displays) or create a new `fmt_signed_pct()` for Perf 1M only. Recommend new helper to avoid regression.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer CLI | `0xdarkmatter/claude-mods@python-cli-patterns` (29 installs) | available — not directly Typer-specific, low value for this simple addition |
| Rich tables | none found | n/a — existing codebase patterns are sufficient |
| Python testing | none relevant found | n/a — existing test patterns are well-established |

No skills recommended for installation — the codebase has clear, repeatable patterns for both CLI options and display columns that are more authoritative than generic skills.

## Sources

- `scripts/run_screener.py` — existing CLI structure with 4 Typer options
- `screener/display.py` — existing table with 13 columns and formatter functions
- `tests/test_cli_screener.py` — 5 existing CLI tests with CliRunner + @patch pattern
- `tests/test_display.py` — 30+ display tests with console capture pattern
- `git show gsd/M002/S01:*` — S01 branch changes (pipeline two-pass, perf_1m field, top_n parameter, compute_monthly_performance)
- `models/screened_stock.py` — ScreenedStock dataclass structure (perf_1m on S01 branch at line 40)
