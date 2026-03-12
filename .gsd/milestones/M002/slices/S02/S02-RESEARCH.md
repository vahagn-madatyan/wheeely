# S02: CLI Flag + Display — Research

**Date:** 2026-03-11

## Summary

S02 is a low-risk slice that wires up the `--top-n` CLI flag on `run-screener` and adds a "Perf 1M" column to the Rich results table. All backend work (perf computation, sort/cap logic, `run_pipeline(top_n=N)` parameter, `ScreenedStock.perf_1m` field) was delivered by S01 on its branch (`gsd/M002/S01`). S02 only needs to merge S01, add the Typer option, add the display column with a signed percentage formatter, and test both.

The main prerequisite risk is that S01's branch has not been merged into the current `gsd/M002/S02` branch. The merge should be clean — S02's branch only has `.gsd/` metadata and `uv.lock` changes, while S01 modified `models/screened_stock.py`, `screener/market_data.py`, `screener/pipeline.py`, and test files.

## Recommendation

Merge S01 first, then implement in two tasks: (1) CLI flag + tests, (2) display column + tests. Both are small and low-risk. Follow the exact patterns already established by `--verbose`, `--preset`, and the HV%ile/Yield column additions.

## Requirements Owned

| Req | Description | This Slice Role |
|-----|-------------|-----------------|
| TOPN-01 | `--top-n N` CLI flag caps stock count after Stage 1 | Primary owner |
| TOPN-05 | "Perf 1M" column visible in Rich results table | Primary owner |
| TOPN-06 | No flag = all stocks processed (backward compatible) | Primary owner |

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option definition | Typer `Option` with `Annotated` type hints | Exact pattern used by `--verbose`, `--preset`, `--config` in same file |
| Rich table column | `table.add_column()` + per-row formatting | Exact pattern used by HV%ile and Yield columns added in S08/S09 |
| Test CLI invocation | `typer.testing.CliRunner` + `@patch` on `scripts.run_screener.*` | Exact pattern in `tests/test_cli_screener.py` |
| Test display output | `Console(file=StringIO())` capture pattern | Exact pattern in `tests/test_display.py` |

## Existing Code and Patterns

### S01 deliverables (on `gsd/M002/S01` branch, not yet merged)

- `models/screened_stock.py` — `perf_1m: Optional[float] = None` field at line 40
- `screener/market_data.py:119` — `compute_monthly_performance(bars_df)` returning float percentage or None
- `screener/pipeline.py:1199` — `run_pipeline(..., top_n: int | None = None)` parameter; sorts Stage 1 survivors by ascending `perf_1m`, caps to N
- `tests/test_pipeline.py` — 5 tests for top_n sort/cap, perf_1m population
- `tests/test_market_data.py` — 6 tests for `compute_monthly_performance()` math

### S02 touch points (current branch)

- **`scripts/run_screener.py:54-58`** — Typer `@app.command()` parameter block. Add `top_n` option here using `Annotated[int | None, typer.Option("--top-n", ...)]`. Pass to `run_pipeline(..., top_n=top_n)` at line ~100.
- **`screener/display.py:180-213`** — `render_results_table()`. Add `table.add_column("Perf 1M", ...)` after HV%ile (line 190). Format with signed percentage in per-row block (lines 199-213).
- **`screener/display.py:121-132`** — Formatter block. Need new `fmt_pct_signed()` that shows `+3.1%` for positive and `-5.2%` for negative (existing `fmt_pct` omits the `+` sign, per TOPN-05 spec).
- **`tests/test_cli_screener.py`** — Add tests: `--top-n 20` passes value to pipeline, omitting flag passes None, `--help` shows `--top-n`.
- **`tests/test_display.py`** — Add tests: "Perf 1M" column header present, positive/negative/None formatting correct.

### Established patterns to follow

- **CLI option pattern** (D019, D022): Module-level imports for patchability. `Annotated[type, typer.Option(...)]` for options. `Console(stderr=True)` for errors.
- **Display column pattern** (D015): Console parameter injection for testability. `fmt_pct(stock.field) if stock.field is not None else "N/A"` for nullable fields.
- **Test pattern** (D006): Fixed data, no `datetime.now()`. `@patch("scripts.run_screener.run_pipeline")` for CLI tests.

## Constraints

- **S01 must be merged first.** The `gsd/M002/S01` branch adds `perf_1m` to `ScreenedStock`, `compute_monthly_performance()` to `market_data.py`, and `top_n` to `run_pipeline()`. Without these, S02 has nothing to wire up.
- **Typer 0.24.1** is installed. `int | None` union type syntax works with this version for `Option`.
- **Existing 345 tests must pass.** No regressions.
- **`fmt_pct` doesn't show `+` for positive values.** TOPN-05 requires signed display (e.g. `+3.1%`). Need a new `fmt_pct_signed()` helper rather than changing `fmt_pct` (which is used by HV%ile, RSI, etc. where `+` is inappropriate).
- **Table width.** Adding "Perf 1M" as the 13th data column. Table already has 13 columns (# through Sector). One more is fine at typical terminal widths (120+), but the column should be compact (`justify="right"`, no `max_width` needed).

## Common Pitfalls

- **Forgetting to merge S01 branch** — S02 branch was created from `main` without S01's code. Must merge `gsd/M002/S01` into `gsd/M002/S02` before any implementation.
- **Changing `fmt_pct` globally** — Adding `+` prefix to `fmt_pct` would break HV%ile and other percentage columns. Use a separate `fmt_pct_signed` formatter.
- **Typer Option type mismatch** — `--top-n` must accept a positive integer or be absent. Use `int | None` with `default=None`. Typer handles this natively — no custom callback needed.
- **Column insertion order** — "Perf 1M" should go after "HV%ile" and before "Yield" (logical grouping: technicals → perf → options yield → score). Verify column order matches `add_row()` argument order.

## Open Risks

- **S01 merge conflicts** — Low probability. S02 branch only changed `.gsd/` files and `uv.lock`. S01 changed source and test files. Should merge cleanly.
- **S01 test breakage on current main** — S01 was developed against a specific main state. If main changed since, S01's tests might need minor fixes after merge. Mitigate by running full test suite immediately after merge.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer (CLI) | none relevant | No Typer-specific skills found; standard Python patterns sufficient |
| Rich (display) | none relevant | No Rich-specific skills found; codebase has established patterns |

## Sources

- `scripts/run_screener.py` — existing CLI option pattern (lines 42-58)
- `screener/display.py` — existing column/formatter pattern (lines 121-213)
- `tests/test_cli_screener.py` — existing CLI test pattern (CliRunner + @patch)
- `tests/test_display.py` — existing display test pattern (Console capture)
- `tests/test_options_chain.py:630-680` — Yield column test pattern (reference for Perf 1M column test)
- `gsd/M002/S01` branch diff — S01 deliverables verified via `git show`
