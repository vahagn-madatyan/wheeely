# S02: CLI Flag + Display — Research

**Date:** 2026-03-11

## Summary

S02 adds a `--top-n` Typer CLI option to `run-screener` and a "Perf 1M" column to the Rich results table. Both are thin integration layers consuming `run_pipeline(top_n=N)` and `ScreenedStock.perf_1m` — outputs that S01 is supposed to provide.

**Critical finding: S01 is not implemented.** The roadmap marks S01 as `[x]` but this is a doctor-created placeholder — no code exists. `ScreenedStock` has no `perf_1m` field, `run_pipeline()` has no `top_n` parameter, and no monthly perf computation exists in `compute_indicators()`. The S01 directory doesn't even exist on disk. `STATE.md` confirms S01 is still in "planning" phase.

S02 cannot begin until S01 is implemented, or S02's scope must absorb S01's work. Assuming S01 is delivered as specified in the boundary map, S02 itself is straightforward — two insertion points, clear existing patterns, low risk.

## Recommendation

**Block on S01 completion first, then implement S02.** Do not merge scopes — S01 is medium-risk (perf computation math, sort/cap logic in pipeline loop, `perf_1m` dataclass field) while S02 is low-risk (CLI flag pass-through, display column). Keeping them separate preserves clean verification.

Once S01 delivers:
1. Add `--top-n` as `typer.Option(int | None, default=None)` in `run_screener.py` and pass through to `run_pipeline(top_n=N)`.
2. Add "Perf 1M" column in `render_results_table()` using existing `fmt_pct()` helper — follows exact pattern of HV%ile and Yield columns added in S08/S09.
3. Test CLI flag parsing with `CliRunner` (pattern: `test_cli_screener.py`), test column rendering with `Console(file=StringIO())` (pattern: `test_options_chain.py::TestDisplayYieldColumn`).

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| CLI option | `typer.Option` with `Annotated[int \| None]` | Already used for all other flags in `run_screener.py` |
| Percentage formatting | `fmt_pct()` in `screener/display.py` | Handles None→"N/A", sign, consistent decimal places |
| Test CLI invocation | `typer.testing.CliRunner` | Already used in `test_cli_screener.py` for all CLI tests |
| Test display capture | `Console(file=StringIO(), width=200)` | Pattern from `test_options_chain.py::TestDisplayYieldColumn` |

## Existing Code and Patterns

- **`scripts/run_screener.py:run()`** — Target for `--top-n` option. All existing options use `Annotated[type, typer.Option(...)]` pattern. The `run_pipeline()` call on line ~89 is where `top_n=N` gets passed through.
- **`screener/display.py:render_results_table()`** — Target for "Perf 1M" column. Columns added with `table.add_column("Name", justify="right")` then values emitted in `table.add_row()`. HV%ile and Yield columns (added in S08/S09) are the exact precedent — both use `fmt_pct()` with None→"N/A" fallback.
- **`tests/test_cli_screener.py`** — CLI test pattern: patch `run_pipeline`, `load_config`, `create_broker_client`, etc. at module level (`scripts.run_screener.X`), invoke via `runner.invoke(app, ["--flag"])`, assert on `result.exit_code` and mock call args.
- **`tests/test_options_chain.py::TestDisplayYieldColumn`** — Display column test pattern: construct a `ScreenedStock` with the field populated, add a passing `FilterResult`, render to `Console(file=StringIO())`, assert column header and formatted value appear in output.
- **`tests/test_display.py::TestRenderResultsTable.test_table_has_column_headers`** — Asserts all expected column names appear; must be updated to include "Perf 1M".
- **`models/screened_stock.py`** — Where `perf_1m: Optional[float] = None` will live (S01's job). S02 only reads this field for display.

## Constraints

- **S01 must be complete first.** `ScreenedStock.perf_1m` and `run_pipeline(top_n=)` don't exist yet. S02 cannot be coded or tested without them.
- **Typer 0.24.1** — `int | None` union type works natively; no `Optional[int]` gymnastics needed. Already proven by `preset: PresetName | None` on line 56 of `run_screener.py`.
- **`--top-n` must accept positive integers only.** Typer doesn't enforce `> 0` by default — add a `typer.Option(min=1)` constraint or validate manually.
- **Backward compatibility is critical.** `--top-n` defaults to `None`, which passes `top_n=None` to `run_pipeline()`, which means no cap (TOPN-06).
- **Column order matters.** "Perf 1M" should appear near Score/Sector (end of table) since it's a sort-key, not a filter metric. Logical placement: after HV%ile, before Yield.
- **`test_table_has_column_headers`** in `test_display.py` line 205 asserts specific column names — must be updated to include "Perf 1M" or the test will fail.

## Common Pitfalls

- **Forgetting to pass `top_n` through the call chain** — The CLI option must flow from `run()` → `run_pipeline()` kwargs. Easy to add the option but forget to wire it into the actual call.
- **Column/row mismatch in `add_row()`** — `render_results_table()` has 13 `add_column()` calls matched by 13 positional args in `add_row()`. Adding a column without adding the corresponding row value (or adding in wrong position) causes a silent misalignment. Count carefully.
- **Not updating `test_table_has_column_headers`** — This test explicitly lists expected column names. Adding the column to display without updating this test will cause a false-negative (test passes but doesn't verify the new column) — worse, it won't catch regressions.
- **Typer `min` validation** — `typer.Option(min=1)` works for `int` but not for `int | None`. Need to handle `None` (no flag) vs `0` (invalid) explicitly if using union type.

## Open Risks

- **S01 not implemented** — The only real risk. If S01's API surface differs from the boundary map (different function signature, different field name), S02 plans need adjustment. Mitigated by S01 having a clear contract in the roadmap.
- **Perf 1M sign convention** — The boundary map says percentage values (e.g. -5.2 for a 5.2% decline). `fmt_pct()` already handles sign correctly (`-5.2%`), but explicit `+` prefix for positive values would improve readability. Need to decide: use `fmt_pct()` as-is or add a signed variant. Minor — can be decided during execution.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Typer CLI | — | none found (standard library-level usage, no skill needed) |
| Rich tables | — | none found (standard library-level usage, no skill needed) |

## Sources

- `scripts/run_screener.py` — current CLI structure and Typer patterns
- `screener/display.py` — current table rendering and `fmt_pct()` helper
- `tests/test_cli_screener.py` — CLI test patterns
- `tests/test_options_chain.py:630-690` — display column test pattern (Yield column)
- `tests/test_display.py:205` — column header assertion that needs updating
- `models/screened_stock.py` — current ScreenedStock dataclass (no `perf_1m` yet)
- `screener/pipeline.py:1191` — current `run_pipeline()` signature (no `top_n` yet)
