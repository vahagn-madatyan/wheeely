# S01: Monthly Perf + Pipeline Cap — Research

**Date:** 2026-03-12

## Summary

S01's deliverables are **already fully implemented and tested**. The `compute_monthly_performance()` function, `perf_1m` field on `ScreenedStock`, `top_n` parameter on `run_pipeline()`, and the ascending-sort/cap logic all exist in production code with 12 passing tests covering math correctness, sort ordering, None handling, backward compatibility, and cap enforcement.

This slice's execution work is verification-only: confirm the existing implementation satisfies every requirement (TOPN-02, TOPN-03, TOPN-04), run the full test suite, and mark complete. No new code needs to be written.

The code was likely added incrementally during M002 context/roadmap preparation or as part of a prior exploratory pass. All 357 tests pass including the 12 S01-specific tests.

## Recommendation

**Verify and close.** The implementation is complete and well-tested. Execution should:
1. Audit each requirement (TOPN-02, TOPN-03, TOPN-04) against existing code and tests
2. Confirm all 357 tests pass (already verified — they do)
3. Confirm the boundary contract (what S02 consumes from S01) is satisfied
4. Mark S01 complete

No new code, no new tests, no refactoring needed.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Monthly perf math | `compute_monthly_performance()` in `screener/market_data.py:119-133` | Already implements 22-day lookback with None for insufficient data |
| Sort/cap logic | `run_pipeline()` in `screener/pipeline.py:1282-1290` | Already sorts ascending with `float('inf')` for None, slices to `[:top_n]` |
| Technical indicators | `ta` library (`RSIIndicator`, `SMAIndicator`) | Already used throughout `compute_indicators()` |

## Existing Code and Patterns

- `screener/market_data.py:119-133` — `compute_monthly_performance(bars_df)` returns `(close[-1] / close[-22] - 1) * 100` or None if < 22 bars. Clean, tested.
- `screener/market_data.py:75-117` — `compute_indicators(bars_df)` is the sister function; `compute_monthly_performance` follows the same pattern (takes DataFrame, returns simple value).
- `screener/pipeline.py:1282-1290` — Sort/cap block: `stage1_survivors.sort(key=lambda s: s.perf_1m if s.perf_1m is not None else float('inf'))` then `stage1_survivors[:top_n]`. Logs cap info.
- `screener/pipeline.py:1270-1277` — `perf_1m` populated in Pass 1 loop via `stock.perf_1m = compute_monthly_performance(bars[sym])`, right after HV computation.
- `models/screened_stock.py:35` — `perf_1m: Optional[float] = None` in the "Technical indicators" section of `ScreenedStock`.
- `tests/test_market_data.py:224-282` — `TestComputeMonthlyPerformance` (6 tests): exact 22 bars, 250 bars uses last 22, insufficient data, negative return, positive return, flat return.
- `tests/test_pipeline.py:1294-1566` — `TestTopNPipelineCap` (6 tests): caps Stage 2 calls, top_n=None processes all, sort ascending perf, None perf sorts last, perf_1m populated on stocks, all stocks still returned.
- Test pattern: Pipeline tests mock `compute_monthly_performance`, `fetch_daily_bars`, `compute_indicators`, `compute_hv_percentile`, and `compute_historical_volatility` at the module level. Market data tests use synthetic DataFrames directly.

## Constraints

- Monthly perf uses exactly 22 trading days — hardcoded per D041, not configurable
- `top_n=None` must remain the default (backward compat per TOPN-06 / D042)
- Sort/cap must happen after Stage 1 but before Stage 1b per D043
- None `perf_1m` sorts to end (not dropped) per D044

## Common Pitfalls

- **Assuming S01 needs new code** — All deliverables already exist. Verify, don't rebuild.
- **Mock ordering in pipeline tests** — The `TestTopNPipelineCap` tests use `@patch` decorators in reverse order (bottom decorator = first arg). The existing pattern patches 5 functions; follow the same order if adding tests.
- **`float('inf')` for None sort** — The sort key uses `float('inf')` to push None-perf stocks to the end. This is correct for ascending sort but would break if sort direction ever changed.

## Open Risks

- None. Implementation is complete, tested, and all 357 tests pass. S02 can consume the boundary contract immediately.

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Alpaca Trading API | `lacymorrow/openclaw-alpaca-trading-skill@alpaca-trading` (24 installs) | available — not needed for this slice (no API work) |
| Alpaca Trading API | `tradermonty/claude-trading-skills@portfolio-manager` (180 installs) | available — not needed for this slice (no API work) |
| pandas / ta | — | none found — not needed (simple computation already done) |

## Sources

- Codebase inspection: `screener/market_data.py`, `screener/pipeline.py`, `models/screened_stock.py`, `tests/test_market_data.py`, `tests/test_pipeline.py`
- Full test suite: 357 passed, 0 failed (verified 2026-03-12)
