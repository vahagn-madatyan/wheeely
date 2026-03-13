# S02: CLI Flag + Display — UAT

**Milestone:** M002
**Written:** 2026-03-12

## UAT Type

- UAT mode: mixed (artifact-driven + live-runtime)
- Why this mode is sufficient: CLI flag is testable via help output and mocked pipeline; live run confirms end-to-end behavior with Perf 1M column visible.

## Preconditions

- `.env` has valid `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, and `FINNHUB_API_KEY`
- `uv pip install -e .` completed
- Market data available (weekday during/after market hours, or use paper account with historical bars)

## Smoke Test

Run `run-screener --help` and confirm `--top-n` appears in the options list.

## Test Cases

### 1. Top-N flag limits results

1. Run `run-screener --top-n 5 --preset aggressive`
2. Wait for pipeline to complete
3. **Expected:** Results table shows ≤5 scored stocks. Completion time is significantly faster than a full run. "Perf 1M" column is visible with signed percentage values.

### 2. No flag processes all stocks

1. Run `run-screener --preset aggressive` (no `--top-n`)
2. Wait for pipeline to complete
3. **Expected:** All Stage 1 survivors proceed through the full pipeline. Results table includes "Perf 1M" column.

### 3. Perf 1M column shows correct format

1. Examine the results table from either test case above
2. **Expected:** "Perf 1M" column shows values like `-5.2%` (negative with sign) or `+3.1%` (positive with `+` prefix). Stocks with no performance data show `N/A`.

## Edge Cases

### Top-N larger than survivor count

1. Run `run-screener --top-n 9999 --preset conservative`
2. **Expected:** All Stage 1 survivors proceed (cap is larger than actual count). No error.

### Top-N of 1

1. Run `run-screener --top-n 1 --preset aggressive`
2. **Expected:** Only 1 stock proceeds past Stage 1 into expensive stages. Table shows 0 or 1 scored results.

## Failure Signals

- `--top-n` not shown in `run-screener --help`
- Results table missing "Perf 1M" column
- More than N stocks in results when `--top-n N` is specified
- Perf 1M values showing raw floats instead of formatted percentages
- Pipeline crashes when `--top-n` is provided

## Requirements Proved By This UAT

- TOPN-01 — `--top-n N` flag accepted and limits stock count
- TOPN-05 — "Perf 1M" column visible with formatted percentages
- TOPN-06 — No flag = all stocks processed (backward compatible)

## Not Proven By This UAT

- TOPN-02, TOPN-03, TOPN-04 — Computation accuracy and sort/cap logic are proved by S01 unit tests, not by visual UAT
- Performance improvement magnitude (depends on symbol list size and API conditions)

## Notes for Tester

- The `--top-n` flag controls how many stocks enter the expensive Finnhub/options stages. The final scored count may be lower if some stocks fail Stage 2/3 filters.
- Use `--preset aggressive` for the best chance of seeing results (loosest filters).
- If all stocks show `N/A` for Perf 1M, that indicates insufficient bar data — try with a symbol list containing well-known large-cap tickers.
