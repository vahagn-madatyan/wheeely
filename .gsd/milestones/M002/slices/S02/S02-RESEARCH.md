# S02: CLI Flag + Display — Research

**Date:** 2026-03-11

## Summary

S02 is the terminal slice for M002. It wires the `top_n` pipeline parameter (delivered by S01) to a `--top-n` CLI flag on `run-screener` and adds a "Perf 1M" column to the Rich results table. This is low-risk, well-scoped work touching three files (`scripts/run_screener.py`, `screener/display.py`, plus tests). All interfaces are already defined by S01.

S01 is implemented on the `gsd/M002/S01` branch (not yet merged into the current branch). It delivers: `ScreenedStock.perf_1m: Optional[float]`, `compute_monthly_performance()`, and `run_pipeline(top_n=N)`. S02's first task must merge S01 into the S02 branch before making changes.

The existing codebase has clear, consistent patterns for both CLI options (Typer `Annotated` style) and display columns (Rich Table with `add_column` / `add_row`). No new libraries, no architectural decisions, no API calls — this is pure wiring.

## Recommendation

Follow the established patterns exactly:
1. Add `--top-n` as a `typer.Option` with `Annotated[int | None, ...]` defaulting to `None`, consistent with the existing `--verbose`, `--preset`, etc. pattern.
2. Pass `top_n=top_n` to `run_pipeline()` in the CLI handler.
3. Add "Perf 1M" column to `render_results_table()` between "HV%ile" and "Yield" — uses existing `fmt_pct()` with sign formatting.
4. Tests follow existing patterns: `CliRunner` + `@patch` for CLI tests in `test_cli_screener.py`, `_make_stock` + `_capture_console` for display tests in `test_display.py`.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option parsing | Typer `Annotated[..., typer.Option()]` | Already used for all flags in `run_screener.py` |
| Percentage formatting | `fmt_pct()` in `screener/display.py` | Handles None → "N/A", consistent formatting |
| Table rendering | Rich `Table.add_column()` / `.add_row()` | Already used for all 12 existing columns |
| CLI test harness | `typer.testing.CliRunner` | Already used in `test_cli_screener.py` |

## Existing Code and Patterns

- `scripts/run_screener.py:run()` — CLI handler using `Annotated[..., typer.Option()]` pattern. The `run_pipeline()` call at line ~120 needs `top_n=top_n` kwarg added. Follow the existing `option_client=broker.option_client` pattern.
- `screener/display.py:render_results_table()` — Builds a Rich Table with 13 columns. "Perf 1M" column inserts between "HV%ile" and "Yield". Format: `fmt_pct(stock.perf_1m)` but needs sign prefix (+/-) per TOPN-05.
- `screener/display.py:fmt_pct()` — Returns `f"{value:.1f}%"` — already includes the negative sign for negative values but does NOT add `+` for positives. Need a `fmt_pct_signed()` or inline formatting for the sign requirement.
- `tests/test_cli_screener.py` — 5 existing tests using `CliRunner` and `@patch("scripts.run_screener.X")`. New tests add `--top-n 20` flag and verify it's passed to `run_pipeline`.
- `tests/test_display.py` — `_make_stock()` helper builds `ScreenedStock` with arbitrary fields. Currently does NOT accept `perf_1m` kwarg — needs to be extended (or set directly on the object). `_all_pass_filters()` provides passing filter results.
- `models/screened_stock.py` — `perf_1m: Optional[float]` field added by S01, positioned after `hv_percentile` in the technical indicators section.
- `screener/pipeline.py:run_pipeline(top_n=None)` — S01 added the `top_n` parameter. CLI just passes it through.

## Constraints

- S01 branch (`gsd/M002/S01`) must be merged into the S02 branch before any code changes — S02 depends on `perf_1m` field and `top_n` parameter.
- `--top-n` must accept positive integers only. Typer will handle type validation natively for `int | None`.
- `top_n=None` when flag is omitted — backward compatible, no default cap (TOPN-06).
- `fmt_pct()` shows `-3.7%` but shows `0.0%` not `+0.0%`. TOPN-05 says "formatted as percentage with sign (e.g. -5.2%, +3.1%)". Need explicit `+` for positive values.
- Display column position matters — "Perf 1M" goes between "HV%ile" and "Yield" for logical grouping (technical indicators → performance → options data).
- 345 existing tests must continue to pass.

## Common Pitfalls

- **Forgetting to merge S01 first** — `perf_1m` field and `top_n` parameter don't exist on the current branch. Merge `gsd/M002/S01` before coding.
- **Missing `+` sign on positive percentages** — `fmt_pct()` doesn't add `+` for positives. Either create `fmt_pct_signed()` or use inline formatting like `f"+{value:.1f}%" if value > 0 else fmt_pct(value)`.
- **`_make_stock()` helper doesn't accept `perf_1m`** — Test helper needs updating or tests should set `stock.perf_1m = X` directly after construction (consistent with how `hv_percentile` and `put_premium_yield` were handled in later test additions).
- **Typer `int | None` default** — Must use `None` as default, not `0`. Typer handles `Optional[int]` / `int | None` natively but the option must be explicitly optional.

## Open Risks

- **S01 merge conflicts** — S01 touches `pipeline.py`, `market_data.py`, `screened_stock.py`, and test files. Merge should be clean since S02 touches different files (`run_screener.py`, `display.py`), but verify test files don't conflict.
- **Typer `int | None` edge case** — Typer sometimes requires explicit `None` handling for optional typed arguments. If `--top-n` doesn't accept bare integers cleanly, may need `typer.Option(None, "--top-n")` syntax. Low risk — same pattern works for `--preset` which is `PresetName | None`.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer | — | none found (well-documented, simple API) |
| Rich | — | none found (well-documented, simple API) |
| Python/pytest | — | standard tooling, no skill needed |

## Sources

- S01 branch diff (`git diff main..gsd/M002/S01`) — confirmed `perf_1m` field, `compute_monthly_performance()`, `run_pipeline(top_n=N)` interfaces
- Existing CLI tests (`tests/test_cli_screener.py`) — 5 tests showing `CliRunner` + `@patch` pattern
- Existing display tests (`tests/test_display.py`) — `_make_stock()` helper, `_capture_console()`, column assertion patterns
- S01 pipeline tests (`tests/test_pipeline.py` on S01 branch) — 6 tests for top_n behavior confirming the interface contract
