---
id: S09
parent: M001
milestone: M001
provides:
  - filter_options_oi() — pure filter checking OI on nearest ATM put
  - filter_options_spread() — pure filter checking bid/ask spread on nearest ATM put
  - compute_put_premium_yield() — annualized yield from best put premium
  - run_stage_3_options() — Stage 3 pipeline runner fetching options chain data and running OI/spread filters
  - _find_nearest_atm_put() — ATM put selection by closest strike to stock price
  - _fetch_options_chain_data() — Alpaca API integration for option contracts and snapshots
  - Updated OptionsConfig with options_oi_min and options_spread_max (Pydantic validated)
  - Updated preset YAMLs with differentiated OI/spread thresholds (conservative strictest)
  - put_premium_yield column in Rich results table
  - Options stage in filter summary panel (shown only when option_client provided)
  - options_oi and options_spread in filter breakdown waterfall
  - option_client parameter on run_pipeline() (backward compatible, default None)
requires:
  - slice: S08
    provides: HV percentile + earnings filters in pipeline, preset YAML structure, FilterResult pattern
affects:
  - S10
key_files:
  - screener/pipeline.py
  - screener/config_loader.py
  - screener/display.py
  - models/screened_stock.py
  - config/presets/conservative.yaml
  - config/presets/moderate.yaml
  - config/presets/aggressive.yaml
  - scripts/run_screener.py
  - tests/test_options_chain.py
key_decisions:
  - D032: Options chain DTE range (14-60 days) hardcoded as module constants, not user-configurable — requirements specify OI/spread configurability only
  - D033: Nearest ATM put selection uses closest strike to stock price (min absolute distance)
  - D034: Spread computed as (ask - bid) / midpoint where midpoint = (bid + ask) / 2 — standard financial convention
  - D035: option_client is optional parameter to run_pipeline() (default None) — Stage 3 skipped when absent for backward compatibility
  - D036: OI sourced from contract listing (trade_client), bid/ask from snapshot (option_client) — avoids extra API call when OI fails early
patterns_established:
  - Stage 3 options chain validation follows same runner + pure-filter pattern as Stage 1 and Stage 2
  - API exceptions in options chain fetching caught and handled gracefully — stock fails filters but doesn't crash pipeline
observability_surfaces:
  - "Options" line in Filter Summary panel (only when option_client active)
  - options_oi and options_spread rows in Filter Breakdown waterfall
  - "Validating options chain" progress indicator during pipeline execution
  - put_premium_yield column shows N/A for stocks that pass without options data
drill_down_paths: []
duration: ~30 minutes
verification_result: passed
completed_at: 2026-03-11
---

# S09: Options Chain Validation

**Options chain OI/spread filtering and put premium yield display integrated as Stage 3 in the screening pipeline**

## What Happened

Added Stage 3 to the screening pipeline: options chain validation. After a stock passes all prior filters (Stage 1 technicals, Stage 1b earnings, Stage 2 fundamentals), the pipeline now fetches put option contracts from Alpaca within a 14–60 DTE range, identifies the nearest ATM put by closest strike to stock price, retrieves its snapshot for bid/ask data, and runs two new pure filter functions — `filter_options_oi()` checks that open interest meets the preset minimum, and `filter_options_spread()` checks that the bid/ask percentage spread is within the preset maximum. When both pass, `compute_put_premium_yield()` calculates the annualized premium yield.

The `OptionsConfig` Pydantic model was extended with `options_oi_min` and `options_spread_max` fields (validated: OI ≥ 0, spread in (0, 1.0]). All three preset YAMLs were updated with differentiated thresholds — conservative requires OI ≥ 500 and spread ≤ 5%, moderate OI ≥ 100 / spread ≤ 10%, aggressive OI ≥ 50 / spread ≤ 20%.

The `run_pipeline()` function gained an optional `option_client` parameter (default None). When None, Stage 3 is skipped entirely, preserving full backward compatibility with all 244 existing tests. The `run-screener` CLI now passes `broker.option_client` to enable options chain validation in production.

The Rich results table gained a "Yield" column showing annualized put premium yield. The filter summary panel conditionally shows an "Options" stage line. The filter breakdown waterfall includes `options_oi` and `options_spread` rows.

## Verification

- 58 new tests in `tests/test_options_chain.py` covering:
  - 7 filter_options_oi tests (pass/fail/None/boundary/custom threshold)
  - 6 filter_options_spread tests (pass/fail/None/custom threshold)
  - 8 compute_put_premium_yield tests (math, edge cases, invalid inputs)
  - 5 _find_nearest_atm_put tests (closest, exact, empty, single, equidistant)
  - 9 run_stage_3_options integration tests (liquid passes, low OI fails, wide spread fails, no contracts, no snapshot, yield gating, API error handling, ATM selection, no price)
  - 6 OptionsConfig validation tests (defaults, invalid values, custom values)
  - 5 preset threshold tests (per-preset values, differentiation, strictness ordering)
  - 2 ScreenedStock field tests (defaults None, settable)
  - 2 display yield column tests (shown, N/A)
  - 2 filter breakdown tests (options filters appear)
  - 3 stage summary tests (Options line present/absent)
  - 3 pipeline integration tests (Stage 3 runs with option_client, skipped without, only for Stage 2 passers)
  - 2 spread computation math tests
- All 302 tests pass (244 existing + 58 new), zero failures
- No regressions in existing tests

## Requirements Advanced

- OPTS-01 → validated: filter_options_oi implemented and tested
- OPTS-02 → validated: filter_options_spread implemented and tested
- OPTS-03 → validated: options_oi_min and options_spread_max configurable per preset, differentiated
- OPTS-04 → validated: Stage 3 only runs after Stage 2 passes, proven by pipeline integration test
- OPTS-05 → validated: Yield column in results table, compute_put_premium_yield tested

## Requirements Validated

- OPTS-01 — 7 filter tests + integration tests prove OI filtering works
- OPTS-02 — 6 filter tests + integration tests prove spread filtering works
- OPTS-03 — 5 preset tests prove per-preset configurability with strict ordering
- OPTS-04 — Pipeline integration test proves Stage 3 only for Stage 2 passers
- OPTS-05 — Display test proves Yield column renders; 8 yield math tests prove computation

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

none

## Known Limitations

- Options chain DTE lookup range (14–60 days) is hardcoded, not user-configurable. This is sufficient for wheel strategy screening but could be made configurable if users need different DTE windows.
- OI comes from the option contract listing (may be end-of-day), not the real-time snapshot. This is acceptable for screening purposes.
- Only the single nearest ATM put is evaluated. Multiple near-ATM strikes could provide a richer view of liquidity, but single-contract validation is sufficient to eliminate illiquid underlyings.

## Follow-ups

- none — S10 picks up the options chain patterns established here for covered call screening

## Files Created/Modified

- `screener/pipeline.py` — Added filter_options_oi, filter_options_spread, compute_put_premium_yield, _find_nearest_atm_put, _fetch_options_chain_data, run_stage_3_options; updated run_pipeline with option_client parameter and Stage 3 call
- `screener/config_loader.py` — Extended OptionsConfig with options_oi_min, options_spread_max + Pydantic validators
- `screener/display.py` — Added Yield column to results table, Options stage to filter summary, options filters to breakdown waterfall
- `models/screened_stock.py` — Added 8 options chain fields (options_oi, options_spread, put_premium_yield, best_put_symbol/strike/dte/bid/ask)
- `config/presets/conservative.yaml` — Added options_oi_min=500, options_spread_max=0.05
- `config/presets/moderate.yaml` — Added options_oi_min=100, options_spread_max=0.10
- `config/presets/aggressive.yaml` — Added options_oi_min=50, options_spread_max=0.20
- `scripts/run_screener.py` — Passes broker.option_client to run_pipeline
- `tests/test_options_chain.py` — 58 new tests covering all S09 functionality

## Forward Intelligence

### What the next slice should know
- The `_fetch_options_chain_data` helper and `_find_nearest_atm_put` are reusable for call screening — the same pattern (fetch contracts, find nearest strike, get snapshot) applies for OTM calls
- `OptionsConfig` already has the OI/spread fields S10 needs for call screening thresholds — S10 can reuse these or add call-specific ones
- `run_pipeline` now has `option_client` threaded through, so `BrokerClient.option_client` is available in the pipeline context

### What's fragile
- `_fetch_options_chain_data` wraps two API calls (get_option_contracts + get_option_snapshot) in try/except — if the Alpaca SDK changes response shapes, the mock pattern in tests would need updating but the exception handling prevents crashes
- The spread computation assumes midpoint > 0 — zero-bid, zero-ask options (truly dead contracts) return spread=None and fail the spread filter

### Authoritative diagnostics
- `python -m pytest tests/test_options_chain.py -v` — 58 tests cover every code path introduced in S09
- Filter Summary panel "Options" line — visible in CLI when options chain validation is active

### What assumptions changed
- Original plan had empty tasks/must-haves — actual implementation was straightforward following established Stage 1/2 patterns
- `option_client` was made optional (not required) to preserve backward compatibility — this was not specified in the plan but is essential for test isolation
