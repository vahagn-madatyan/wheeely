# M003 Requirements — Execution Cleanup

## Active

### EXEC-01 — Put screener function exists with same interface pattern as call screener
- Class: core-capability
- Status: active
- Description: `screen_puts()` in `screener/put_screener.py` accepts `trade_client`, `option_client`, `symbols`, `buying_power`, and optional `ScreenerConfig`, returns `list[PutRecommendation]` sorted by annualized return descending
- Why it matters: Symmetric interface enables consistent web API wrapping and testability
- Source: user (premium-expansion.md E5)
- Primary owning slice: none yet
- Supporting slices: none
- Validation: unmapped
- Notes: Must handle multiple symbols (unlike call screener which takes single symbol)

### EXEC-02 — Put screening applies bid/ask spread filter
- Class: core-capability
- Status: active
- Description: `screen_puts()` rejects put contracts where `(ask - bid) / midpoint > spread_max` from screener config, matching call screener behavior
- Why it matters: Wide-spread puts fill poorly; current put path has no spread check
- Source: user (premium-expansion.md E1)
- Primary owning slice: none yet
- Supporting slices: none
- Validation: unmapped
- Notes: Uses same `options_spread_max` from ScreenerConfig presets

### EXEC-03 — Both put and call scoring use annualized return
- Class: core-capability
- Status: active
- Description: Puts scored by `(bid / strike) × (365 / DTE) × 100` — annualized return on capital at risk. Calls already use `(premium / cost_basis) × (365 / DTE) × 100`. Both are "annualized premium yield on capital deployed"
- Why it matters: Consistent scoring enables apples-to-apples comparison in dashboard; current put formula double-counts delta
- Source: user (premium-expansion.md E2)
- Primary owning slice: none yet
- Supporting slices: none
- Validation: unmapped
- Notes: Old formula `(1-|delta|) × (250/(DTE+5)) × (bid/strike)` is replaced

### EXEC-04 — Put DTE minimum is 7 days (not 0)
- Class: core-capability
- Status: active
- Description: Put contracts with DTE < 7 are excluded from screening. Minimum DTE raised from 0 to 7 for puts
- Why it matters: 0-6 DTE options have spiking gamma risk and negligible time value — poor risk/reward for premium selling
- Source: user (premium-expansion.md E3)
- Primary owning slice: none yet
- Supporting slices: none
- Validation: unmapped
- Notes: Call screener already uses 14-day minimum

### EXEC-05 — `run-strategy` uses `screen_puts()` for put selection
- Class: core-capability
- Status: active
- Description: `run_strategy.py` calls `screen_puts()` to get `list[PutRecommendation]` then executes best per underlying until buying power exhausted, replacing the `sell_puts()` → `filter_options()` → `score_options()` → `select_options()` chain
- Why it matters: Aligns put execution with call execution pattern in `run_strategy.py`
- Source: user (premium-expansion.md E5)
- Primary owning slice: none yet
- Supporting slices: none
- Validation: unmapped
- Notes: `run-strategy` CLI interface unchanged — same flags, same behavior

### EXEC-06 — Dead `sell_calls()` code removed
- Class: quality-attribute
- Status: active
- Description: `sell_calls()` in `core/execution.py` is deleted. Unused `from core.execution import sell_calls` in `run_strategy.py` is removed
- Why it matters: Dead code creates confusion about which path is live (D038 confirmed screen_calls is the live path)
- Source: inferred
- Primary owning slice: none yet
- Supporting slices: none
- Validation: unmapped
- Notes: D038 documents that screen_calls replaced sell_calls

### EXEC-07 — Dead strategy functions removed after put screener replaces them
- Class: quality-attribute
- Status: active
- Description: `filter_options()`, `score_options()`, `select_options()` in `core/strategy.py` are removed once `screen_puts()` replaces their usage. `filter_underlying()` may be retained if still useful
- Why it matters: Prevents confusion about which scoring/filtering path is active
- Source: inferred
- Primary owning slice: none yet
- Supporting slices: none
- Validation: unmapped
- Notes: Check for any other importers before removing

### EXEC-08 — All existing tests continue to pass
- Class: quality-attribute
- Status: active
- Description: The 368 existing tests pass unchanged or with justified modifications
- Why it matters: Refactoring must not break existing functionality
- Source: inferred
- Primary owning slice: none yet
- Supporting slices: none
- Validation: unmapped
- Notes: Tests that directly test removed functions (score_options, filter_options) will need removal/replacement

### EXEC-09 — New put screener has comprehensive test coverage
- Class: quality-attribute
- Status: active
- Description: `test_put_screener.py` covers spread filter, DTE minimum, annualized return scoring, multiple symbols, buying power constraint, empty results, edge cases — following the pattern established in `test_call_screener.py`
- Why it matters: Put screener is a critical execution path — must be thoroughly tested
- Source: inferred
- Primary owning slice: none yet
- Supporting slices: none
- Validation: unmapped
- Notes: Aim for comparable coverage to test_call_screener.py (969 lines)

## Validated

(none yet — M003 has not started)

## Deferred

### EXEC-D01 — DTE ranges configurable per preset in ScreenerConfig YAML
- Class: core-capability
- Status: deferred
- Description: DTE min/max could be made configurable per preset instead of module-level constants
- Why it matters: Different presets might benefit from different DTE windows (conservative=30-45, aggressive=7-21)
- Source: inferred
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: D032 explicitly noted this as "Yes — revisable if users need different windows." Defer to avoid scope creep — current constants work well

### EXEC-D02 — Put strike floor guard (avoid deep ITM assignments)
- Class: core-capability
- Status: deferred
- Description: Add a guard rejecting put strikes significantly above current stock price to limit assignment overpay risk
- Why it matters: A put at a strike far above market price guarantees deep-ITM assignment at a bad price
- Source: inferred (premium-expansion.md mentions this as a missing guard)
- Primary owning slice: none
- Supporting slices: none
- Validation: unmapped
- Notes: Current delta filter (0.15-0.30) already limits this somewhat — deep ITM puts have high delta and get filtered. Explicit guard is nice-to-have

## Out of Scope

### EXEC-X01 — FMP/ORATS integration
- Class: core-capability
- Status: out-of-scope
- Description: Premium data source integration is a separate milestone
- Why it matters: Prevents scope creep — this milestone is about execution path unification
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: n/a
- Notes: premium-expansion.md E6 maps where FMP/ORATS slots into screen_puts/screen_calls — but that's later

### EXEC-X02 — Web API / FastAPI wrapping
- Class: core-capability
- Status: out-of-scope
- Description: Building the SaaS web layer is a separate milestone
- Why it matters: This milestone produces the clean engine; the web layer milestone wraps it
- Source: user
- Primary owning slice: none
- Supporting slices: none
- Validation: n/a
- Notes: screen_puts() and screen_calls() will have symmetric interfaces ready for wrapping

## Traceability

| ID | Class | Status | Primary owner | Supporting | Proof |
|---|---|---|---|---|---|
| EXEC-01 | core-capability | active | none yet | none | unmapped |
| EXEC-02 | core-capability | active | none yet | none | unmapped |
| EXEC-03 | core-capability | active | none yet | none | unmapped |
| EXEC-04 | core-capability | active | none yet | none | unmapped |
| EXEC-05 | core-capability | active | none yet | none | unmapped |
| EXEC-06 | quality-attribute | active | none yet | none | unmapped |
| EXEC-07 | quality-attribute | active | none yet | none | unmapped |
| EXEC-08 | quality-attribute | active | none yet | none | unmapped |
| EXEC-09 | quality-attribute | active | none yet | none | unmapped |
| EXEC-D01 | core-capability | deferred | none | none | unmapped |
| EXEC-D02 | core-capability | deferred | none | none | unmapped |
| EXEC-X01 | core-capability | out-of-scope | none | none | n/a |
| EXEC-X02 | core-capability | out-of-scope | none | none | n/a |

## Coverage Summary

- Active requirements: 9
- Mapped to slices: 0
- Validated: 0
- Unmapped active requirements: 9
