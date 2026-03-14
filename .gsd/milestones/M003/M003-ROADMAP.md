# M003: Execution Cleanup — Unify Put & Call Paths

**Vision:** Both sides of the wheel use the same screener architecture — `screen_puts()` mirrors `screen_calls()` with spread filter, annualized return scoring, and consistent DTE ranges. Dead code is removed. The engine is ready for web API wrapping.

## Success Criteria

- `screen_puts()` returns `list[PutRecommendation]` with the same interface shape as `screen_calls()` returns `list[CallRecommendation]`
- Put screening applies spread filter, annualized return scoring, and DTE minimum of 7 days
- `run-strategy` uses `screen_puts()` for put selection (same pattern as call selection)
- Dead `sell_calls()` and unused strategy functions are removed
- All tests pass (existing + new put screener tests)

## Key Risks / Unknowns

- **Scoring change alters contract selection** — switching from custom formula to annualized return may pick different contracts. Need to verify reasonable selections on paper account. Medium risk.
- **Spread filter reduces put universe too aggressively** — puts may have systematically wider spreads than calls. Low risk — threshold is configurable per preset.

## Proof Strategy

- Scoring change → retire in S01 by proving annualized return scoring picks contracts with similar characteristics (delta range, DTE range, strike proximity) to old formula on representative test data
- Spread filter → retire in S01 by proving reasonable pass rate on mock data matching real market conditions

## Verification Classes

- Contract verification: pytest (existing 368 + new put screener tests)
- Integration verification: `run-strategy` exercises new put path against Alpaca paper account
- Operational verification: none (CLI tool)
- UAT / human verification: compare old vs new put selections visually on paper account

## Milestone Definition of Done

This milestone is complete only when all are true:

- `screen_puts()` exists with full test coverage and returns sorted `PutRecommendation` list
- `run-strategy` uses `screen_puts()` for put selection and execution
- Dead code (`sell_calls`, old strategy functions) is removed
- All tests pass (existing + new)
- Success criteria re-checked by running `run-strategy` against Alpaca paper

## Requirement Coverage

- Covers: EXEC-01, EXEC-02, EXEC-03, EXEC-04, EXEC-05, EXEC-06, EXEC-07, EXEC-08, EXEC-09
- Partially covers: none
- Leaves for later: EXEC-D01 (configurable DTE per preset), EXEC-D02 (put strike floor guard)
- Orphan risks: none

## Slices

- [ ] **S01: Put Screener** `risk:high` `depends:[]`
  > After this: `screen_puts()` exists with spread filter, annualized return scoring, DTE minimum 7, full test suite — callable from a Python REPL but not yet wired into `run-strategy`
- [ ] **S02: Strategy Integration + Dead Code Removal** `risk:medium` `depends:[S01]`
  > After this: `run-strategy` uses `screen_puts()` for put selection; dead `sell_calls()` and old strategy functions removed; all tests pass; CLI verified against Alpaca paper

## Boundary Map

### S01 → S02

Produces:
- `screener/put_screener.py` with `screen_puts(trade_client, option_client, symbols, buying_power, config?) → list[PutRecommendation]`
- `PutRecommendation` dataclass with: symbol, underlying, strike, dte, premium, delta, oi, spread, annualized_return
- `compute_put_annualized_return(bid, strike, dte) → float|None`
- `test_put_screener.py` with comprehensive coverage

Consumes:
- nothing (first slice)

### S02 consumes S01

Consumes:
- `screen_puts()` function and `PutRecommendation` dataclass from S01
- Existing `run_strategy.py`, `core/execution.py`, `core/strategy.py` (to refactor/remove)
