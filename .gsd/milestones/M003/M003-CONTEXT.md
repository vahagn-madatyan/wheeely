# M003: Execution Cleanup — Unify Put & Call Paths — Context

**Gathered:** 2026-03-12
**Status:** Ready for planning

## Project Description

Wheeely is an automated options wheel strategy bot. It sells cash-secured puts, handles assignments, then sells covered calls — repeating the cycle. Currently has three CLI tools (`run-strategy`, `run-screener`, `run-call-screener`) and a 4-stage screening pipeline.

The put-selling and call-selling execution paths have diverged significantly. Call selling was rebuilt from scratch in M001/S10 with a clean screener pattern (`screen_calls()` → ranked recommendations → select best). Put selling still uses the older `core/strategy.py` + `core/execution.py` path with different filters, a different scoring formula, and different DTE ranges. Dead code from the old call path remains.

This milestone unifies both sides of the wheel into a consistent architecture before the SaaS web layer is built on top.

## Why This Milestone

The SaaS platform (premium-expansion.md) will wrap `screen_puts()` and `screen_calls()` in FastAPI endpoints. Those endpoints need a consistent interface — same filter patterns, same scoring metric, same recommendation dataclass shape. Building the web layer on top of the current asymmetric execution code would bake the inconsistencies into the API contract.

Additionally:
- Puts have no spread filter — wide-spread options pass and fill poorly
- Puts use a custom score formula that double-counts delta (already filtered); calls use annualized return
- Put DTE range includes 0-day expiries (gamma risk, no time value)
- Dead `sell_calls()` in `execution.py` creates confusion about which path is live
- No `screen_puts()` function exists — the web API needs one

## User-Visible Outcome

### When this milestone is complete, the user can:

- Run `run-strategy` and see put selection use the same filter quality (spread, OI, delta) and scoring (annualized return) as call selection
- See consistent DTE ranges (minimum 7 days) for both put and call screening
- Trust that the strategy engine is ready to be wrapped by a web API with a clean, symmetric interface

### Entry point / environment

- Entry point: `run-strategy` CLI command (unchanged interface, improved internals)
- Environment: local dev, paper trading account
- Live dependencies involved: Alpaca API (paper trading)

## Completion Class

- Contract complete means: all existing tests pass + new tests for `screen_puts()`, spread filter, annualized return scoring, DTE minimum
- Integration complete means: `run-strategy` exercises the new put path end-to-end against Alpaca paper
- Operational complete means: none (CLI tool, no service lifecycle)

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- `run-strategy` successfully screens and sells puts using the new `screen_puts()` path with spread filter, annualized return scoring, and DTE minimum ≥ 7
- `screen_puts()` returns `list[PutRecommendation]` with the same interface pattern as `screen_calls()` returns `list[CallRecommendation]`
- All existing tests pass (368 tests), plus new tests covering put screener, spread filter, unified scoring
- Dead code (`sell_calls()` in execution.py, unused import in run_strategy.py) is removed

## Risks and Unknowns

- **Scoring change may alter put selection** — switching from custom formula to annualized return could select different contracts. Need to verify the new scoring still picks reasonable contracts. Risk: medium, mitigation: compare old vs new selections on paper account.
- **DTE minimum increase may reduce available contracts** — raising minimum from 0 to 7 days removes near-expiry options. Risk: low — near-expiry options have poor risk/reward anyway.
- **Spread filter may be too aggressive** — using the same `spread_max` from screener config for puts. If put spreads are systematically wider than call spreads, this could filter too aggressively. Risk: low — can tune threshold if needed.

## Existing Codebase / Prior Art

- `core/strategy.py` — current put filtering/scoring (to be replaced by `screen_puts()`)
- `core/execution.py` — `sell_puts()` orchestrator (to be refactored), dead `sell_calls()` (to be removed)
- `screener/call_screener.py` — the clean pattern to mirror for puts (`screen_calls()`, `CallRecommendation`)
- `scripts/run_strategy.py` — consumer of both paths, imports dead `sell_calls`
- `config/params.py` — DTE ranges, delta ranges, yield ranges, score minimum
- `tests/test_call_screener.py` — 969 lines of call screener tests (pattern to follow for put screener tests)

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- No formal requirements yet for M003 — will be defined during planning
- Related decisions: D032 (DTE range hardcoded), D033 (nearest ATM selection), D037 (call screener reuses put thresholds), D038 (screen_calls replaces sell_calls)

## Scope

### In Scope

- Build `screener/put_screener.py` with `screen_puts()` mirroring `screen_calls()` pattern
- Add spread filter to put screening
- Unify scoring to annualized return for both puts and calls
- Set DTE minimum to 7 days for puts
- Refactor `run_strategy.py` to use `screen_puts()` instead of `sell_puts()`
- Remove dead `sell_calls()` from `execution.py`
- Remove unused `sell_calls` import from `run_strategy.py`
- Pull DTE bounds from config rather than hardcoding
- Full test coverage for new put screener

### Out of Scope / Non-Goals

- FMP or ORATS integration (future milestone)
- Web API / FastAPI wrapping (future milestone)
- Supabase / auth / multi-tenant (future milestone)
- Changes to `run-screener` or `run-call-screener` CLI tools
- Changes to the screening pipeline (`screener/pipeline.py`)
- Changing the screener config YAML format

## Technical Constraints

- Must not break existing 368 tests
- Must preserve `run-strategy` CLI interface (same flags, same behavior)
- `screen_puts()` must work with existing `BrokerClient` — same Alpaca SDK clients
- Scoring change should be justified by comparing old vs new selections

## Integration Points

- `BrokerClient` — `trade_client` for contract discovery, `option_client` for snapshots, `market_sell()` for execution
- `ScreenerConfig` — reuses existing preset thresholds for OI, spread, delta
- `config/params.py` — delta ranges, DTE ranges (may become configurable)
- `run_strategy.py` — primary consumer, needs to switch from `sell_puts()` to `screen_puts()` + execute

## Open Questions

- Should `sell_puts()` in `execution.py` be kept as a thin wrapper that calls `screen_puts()` + executes, or should `run_strategy.py` call `screen_puts()` directly and handle execution inline? — Leaning toward direct call in `run_strategy.py` (matches call pattern), but `sell_puts()` could become a convenience function.
- Should DTE min/max be added to `ScreenerConfig` presets, or stay in `config/params.py`? — Current call screener hardcodes them as module constants (D032). Could stay that way for now, make configurable later.
- Should `core/strategy.py` functions be removed entirely, or kept for backward compat? — `filter_options()`, `score_options()`, `select_options()` would become dead code. Clean removal preferred if nothing else imports them.
