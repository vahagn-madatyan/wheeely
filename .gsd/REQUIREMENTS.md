# Requirements

## Active

### WEB-01 — User can sign up with email and log into an authenticated web dashboard
- Class: primary-user-loop
- Status: active
- Description: Email signup/login via Supabase Auth, JWT-based session, protected routes redirect to login
- Why it matters: Gate to all web features; no auth = no multi-tenant isolation
- Source: user
- Primary owning slice: M004/S02
- Supporting slices: M004/S03
- Validation: unmapped

### WEB-02 — User can store Alpaca API keys (key + secret + paper/live toggle) with encryption at rest
- Class: compliance/security
- Status: active
- Description: Alpaca credentials encrypted via envelope encryption before storage. Decrypted only for API calls. Paper/live toggle controls which Alpaca environment is used.
- Why it matters: Storing brokerage credentials for other people's money — must be encrypted at rest
- Source: user
- Primary owning slice: M004/S02
- Supporting slices: M004/S04
- Validation: unmapped

### WEB-03 — User can store Finnhub API key with encryption at rest
- Class: compliance/security
- Status: active
- Description: Finnhub key encrypted identically to Alpaca keys. BYOK — user's own free-tier key.
- Why it matters: Consistent key management across all providers
- Source: user
- Primary owning slice: M004/S02
- Supporting slices: M004/S04
- Validation: unmapped

### WEB-04 — User can verify API key connectivity from the settings page
- Class: primary-user-loop
- Status: active
- Description: After storing keys, user clicks "Verify" and sees green/red status per provider. Verification makes a lightweight API call (e.g., Alpaca get_account, Finnhub company_profile for a known symbol).
- Why it matters: User must know if their keys work before attempting to screen
- Source: inferred
- Primary owning slice: M004/S04
- Supporting slices: none
- Validation: unmapped

### WEB-05 — User can run the put screener from a browser and see ranked results
- Class: primary-user-loop
- Status: active
- Description: Put screener UI accepts preset, symbols, buying power. Submits to API, polls for completion, displays sortable results table matching CLI columns (symbol, strike, DTE, premium, delta, OI, spread, annualized return).
- Why it matters: Core free-tier value — this is what users come for
- Source: user
- Primary owning slice: M004/S05
- Supporting slices: M004/S01
- Validation: unmapped

### WEB-06 — User can run the call screener from a browser and see ranked results
- Class: primary-user-loop
- Status: active
- Description: Call screener UI accepts symbol + cost basis + preset. Same async flow as put screener. Results table matches CLI columns.
- Why it matters: Second half of the wheel — users with assigned shares need call screening
- Source: user
- Primary owning slice: M004/S05
- Supporting slices: M004/S01
- Validation: unmapped

### WEB-07 — User can view their Alpaca positions with wheel state on the dashboard
- Class: primary-user-loop
- Status: active
- Description: Dashboard fetches positions via user's Alpaca keys, maps to wheel states (short_put / long_shares / short_call) using existing state_manager logic, displays in a table.
- Why it matters: Users need to see what they own before deciding what to screen
- Source: user
- Primary owning slice: M004/S06
- Supporting slices: M004/S01
- Validation: unmapped

### WEB-08 — User can see account summary (buying power, capital at risk)
- Class: primary-user-loop
- Status: active
- Description: Dashboard shows buying power from Alpaca account and capital at risk computed by existing calculate_risk() logic.
- Why it matters: Buying power determines which puts are affordable; risk determines exposure
- Source: user
- Primary owning slice: M004/S06
- Supporting slices: M004/S01
- Validation: unmapped

### WEB-09 — Free-tier rate limiting: 3 screening runs per day
- Class: constraint
- Status: active
- Description: Redis sliding window counter per user. 4th screening request in 24 hours returns 429 with clear message and time until reset.
- Why it matters: Free tier must have limits to differentiate from premium; prevents abuse of Alpaca/Finnhub APIs via our platform
- Source: user
- Primary owning slice: M004/S06
- Supporting slices: none
- Validation: unmapped

### WEB-10 — Multi-tenant data isolation: users cannot see each other's keys, results, or positions
- Class: compliance/security
- Status: active
- Description: Supabase RLS policies enforce per-user isolation on all tables. API endpoints filter by authenticated user ID. No shared state between users.
- Why it matters: Security fundamental — brokerage credentials and financial data must be isolated
- Source: inferred
- Primary owning slice: M004/S02
- Supporting slices: none
- Validation: unmapped

### WEB-11 — Screening runs asynchronously (background task with status polling)
- Class: core-capability
- Status: active
- Description: Screening requests return a run_id immediately. Client polls GET /api/screen/runs/{id} for status (pending/running/completed/failed) and results. No HTTP timeout on 30-60s screening runs.
- Why it matters: CLI screening takes 30-60s — can't block an HTTP request that long
- Source: inferred
- Primary owning slice: M004/S01
- Supporting slices: M004/S05
- Validation: unmapped

### WEB-12 — App is deployed on Render with infrastructure-as-code (render.yaml)
- Class: operability
- Status: active
- Description: render.yaml defines web (Next.js), api (FastAPI), and redis services. Docker Compose for local dev. Services communicate via Render private network.
- Why it matters: Reproducible deployment; no manual infrastructure configuration
- Source: user
- Primary owning slice: M004/S07
- Supporting slices: none
- Validation: unmapped

### WEB-13 — User can delete stored API keys
- Class: primary-user-loop
- Status: active
- Description: User can remove any stored API key from settings page. Deletion is immediate and permanent.
- Why it matters: Users must be able to revoke access; data retention minimization
- Source: inferred
- Primary owning slice: M004/S04
- Supporting slices: none
- Validation: unmapped

### CLI-COMPAT-01 — CLI continues to work exactly as before with zero changes
- Class: constraint
- Status: validated
- Description: All console scripts (run-strategy, run-screener, run-call-screener, run-put-screener) work unchanged. 425 tests pass. No import path changes. No new dependencies required for CLI operation.
- Why it matters: CLI is the proven, working product — web is additive, not a migration
- Source: user
- Primary owning slice: M004/S01
- Supporting slices: none
- Validation: 425 CLI tests pass unchanged after adding apps/api/. Zero files outside apps/api/ modified.

## Validated

### TOPN-01 — `--top-n N` CLI flag caps stock count after Stage 1
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M002/S02
- Supporting Slices: M002/S01
- Proof: 3 CLI tests (help text, value forwarding, None default) in test_cli_screener.py; `--top-n` Typer option with min=1 forwarded to run_pipeline(top_n=)

### TOPN-02 — Monthly performance computed from existing bar data (~22 trading days)
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M002/S01
- Proof: 4 compute_monthly_performance tests in test_pipeline_topn.py; uses last 22 bars of existing 250-day data

### TOPN-03 — Stage 1 survivors sorted by ascending perf, top N proceed to expensive stages
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M002/S01
- Proof: 4 sort/cap tests in test_pipeline_topn.py; ascending sort with None-last ordering, cap applied before Stage 1b

### TOPN-04 — `perf_1m` field on ScreenedStock populated during indicator computation
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M002/S01
- Proof: ScreenedStock.perf_1m Optional[float] field; populated by compute_monthly_performance() during indicator step; 3 integration tests

### TOPN-05 — "Perf 1M" column visible in Rich results table
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M002/S02
- Proof: 4 display tests (header present, positive +sign, negative value, None→N/A) in test_display.py; fmt_signed_pct() helper

### TOPN-06 — No flag = all stocks processed (backward compatible)
- Status: validated
- Class: core-capability
- Source: user
- Primary Slice: M002/S02
- Proof: test_no_top_n_defaults_to_none in test_cli_screener.py; top_n=None in pipeline means no cap; 3 backward-compat tests in test_pipeline_topn.py

### FIX-01 — Screener produces non-zero results when run with moderate preset against live market data
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: M001/S07
- Proof: S07 fixed zero-results bug via D/E normalization (D027) and preset differentiation

### FIX-02 — Finnhub debt/equity values are normalized correctly
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: M001/S07
- Proof: D27 heuristic at pipeline.py:979

### FIX-03 — Missing Finnhub data does not eliminate a stock
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: M001/S07
- Proof: D28 pattern — 44 None-handling tests pass

### FIX-04 — avg_volume_min is differentiated across presets
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: M001/S07
- Proof: Preset YAML files verified

### PRES-01 — All three presets differ across ALL filter categories
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: M001/S07
- Proof: 15+ threshold differences across fundamentals, technicals, options, earnings, sectors

### PRES-02 — Conservative preset uses tighter thresholds
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: M001/S07
- Proof: Conservative values verified in YAML

### PRES-03 — Aggressive preset uses looser thresholds
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: M001/S07
- Proof: Aggressive values verified in YAML

### PRES-04 — Each preset includes default sector avoid/prefer lists
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: M001/S07
- Proof: Sector lists verified per preset

### HVPR-01 — User can filter stocks by HV Percentile rank
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: M001/S08
- Proof: 7 computation tests + 2 integration tests

### HVPR-02 — HV Percentile threshold is configurable per preset
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: M001/S08
- Proof: 3 preset YAML tests + 1 differentiation test

### HVPR-03 — HV Percentile value is displayed in screener results table
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: M001/S08
- Proof: HV%ile column in render_results_table()

### EARN-01 — User can filter stocks that have earnings within N days
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: M001/S08
- Proof: 8 filter boundary tests

### EARN-02 — Earnings data fetched via Finnhub earnings calendar
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: M001/S08
- Proof: 5 FinnhubClient earnings tests

### EARN-03 — Earnings day threshold configurable per preset
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: M001/S08
- Proof: 3 preset tests + 1 differentiation test

### OPTS-01 — User can filter stocks by options chain OI
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: M001/S09
- Proof: 7 filter tests + integration tests

### OPTS-02 — User can filter stocks by bid/ask spread
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: M001/S09
- Proof: 6 filter tests + integration tests

### OPTS-03 — OI and spread thresholds configurable per preset
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: M001/S09
- Proof: 5 preset threshold tests

### OPTS-04 — Options chain validation runs only on prior-stage passers
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: M001/S09
- Proof: test_stage3_only_for_stage2_passers

### OPTS-05 — Best put premium displayed in screener results table
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: M001/S09
- Proof: test_yield_column + 8 math tests

### CALL-01 — User can run run-call-screener standalone CLI
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: M001/S10
- Proof: 3 CLI tests in test_call_screener.py

### CALL-02 — Call screener accepts symbol + cost basis
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: M001/S10
- Proof: test_basic_screening + test_sorted_by_return

### CALL-03 — Call screener enforces strike >= cost basis
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: M001/S10
- Proof: 3 strike boundary tests

### CALL-04 — Call screener applies same DTE/OI/spread/delta filters
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: M001/S10
- Supporting Slices: M001/S09
- Proof: 6 filter tests in test_call_screener.py

### CALL-05 — Call screener displays Rich table with all columns
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: M001/S10
- Proof: test_table_renders_with_data + 3 edge case tests

### CALL-06 — run-strategy integrates call screener
- Status: validated
- Class: core-capability
- Source: inferred
- Primary Slice: M001/S10
- Proof: 3 strategy integration tests

## Deferred

### PREM-01 — Stripe billing with free/premium tiers ($29/mo)
- Class: core-capability
- Status: deferred
- Description: Stripe Checkout, webhooks, tier enforcement middleware, customer portal
- Why it matters: Revenue — differentiates free from premium
- Source: user
- Primary owning slice: none
- Validation: unmapped
- Notes: M005 — depends on free tier being functional first

### PREM-02 — FMP as additional data provider for premium users (BYOK)
- Class: differentiator
- Status: deferred
- Description: FMP client with server-side screening, bulk fundamentals, earnings. Additive to Finnhub — users can connect both. Pipeline adapts to which keys are present.
- Why it matters: Premium value — faster screening, cleaner fundamentals
- Source: user
- Primary owning slice: none
- Validation: unmapped
- Notes: M005+ — FMP keys are future purchases; build against mocks first

### PREM-03 — ORATS as additional data provider for premium users (BYOK)
- Class: differentiator
- Status: deferred
- Description: ORATS client with IV rank, IV/HV ratio, fair value, skew analysis, graduated earnings. Additive to existing providers.
- Why it matters: Premium value — real IV data instead of HV percentile proxy
- Source: user
- Primary owning slice: none
- Validation: unmapped
- Notes: M005+ — ORATS keys are future purchases; build against mocks first

### PREM-04 — Cloud auto-trading (scheduled wheel strategy per user)
- Class: differentiator
- Status: deferred
- Description: Celery/cron sweep during market hours, per-user risk limits, kill switch, audit trail
- Why it matters: Flagship premium feature — hands-off wheel execution
- Source: user
- Primary owning slice: none
- Validation: unmapped
- Notes: M006+ — requires billing, key storage, and screening to be solid first

### PREM-05 — LLM analysis agents (screening analysis, trade reasoning, risk assessment)
- Class: differentiator
- Status: deferred
- Description: LiteLLM + LangChain agents with regulatory language guardrails, Redis caching
- Why it matters: Premium value — AI-powered insights on screening results
- Source: user
- Primary owning slice: none
- Validation: unmapped
- Notes: M006+ — requires screening results to analyze

### PREM-06 — Manual trade execution from web UI
- Class: core-capability
- Status: deferred
- Description: Select contracts from screener results, review order summary, confirm execution
- Why it matters: Completes the loop — screen → decide → execute without leaving the browser
- Source: user
- Primary owning slice: none
- Validation: unmapped
- Notes: M005+ — requires billing (premium only) and solid key management

### PREM-07 — Watchlist manager
- Class: core-capability
- Status: deferred
- Description: Add/remove symbols, import from screener, per-symbol mini-cards, "Screen All"
- Why it matters: Persistent symbol tracking between screening sessions
- Source: user
- Primary owning slice: none
- Validation: unmapped
- Notes: M005+

### PREM-08 — Trade journal with AI reasoning
- Class: differentiator
- Status: deferred
- Description: Every trade with context, P&L per trade/symbol/aggregate, charts, CSV export
- Why it matters: Premium value — performance tracking and learning
- Source: user
- Primary owning slice: none
- Validation: unmapped
- Notes: M006+ — requires trade execution and LLM integration

## Out of Scope

### OOS-01 — Modifying the CLI in any way
- Class: constraint
- Status: out-of-scope
- Description: CLI entry points, imports, behavior, and dependencies must not change. Web is additive.
- Why it matters: CLI is the proven product; web is a new layer, not a migration
- Source: user
- Primary owning slice: none
- Validation: n/a

### OOS-02 — Self-hosted Postgres (must use Supabase managed)
- Class: constraint
- Status: out-of-scope
- Description: Database is Supabase-managed Postgres, not self-hosted
- Why it matters: Reduces operational burden; auth + RLS + vault built in
- Source: user
- Primary owning slice: none
- Validation: n/a

### OOS-03 — AWS/GCP deployment
- Class: constraint
- Status: out-of-scope
- Description: Deploy on Render, not AWS/GCP
- Why it matters: Simpler, cheaper at this scale; infrastructure-as-code via render.yaml
- Source: user
- Primary owning slice: none
- Validation: n/a

## Traceability

| ID | Class | Status | Primary owner | Supporting | Proof |
|---|---|---|---|---|---|
| WEB-01 | primary-user-loop | active | M004/S02 | M004/S03 | unmapped |
| WEB-02 | compliance/security | active | M004/S02 | M004/S04 | unmapped |
| WEB-03 | compliance/security | active | M004/S02 | M004/S04 | unmapped |
| WEB-04 | primary-user-loop | active | M004/S04 | none | unmapped |
| WEB-05 | primary-user-loop | active | M004/S05 | M004/S01 | unmapped |
| WEB-06 | primary-user-loop | active | M004/S05 | M004/S01 | unmapped |
| WEB-07 | primary-user-loop | active | M004/S06 | M004/S01 | unmapped |
| WEB-08 | primary-user-loop | active | M004/S06 | M004/S01 | unmapped |
| WEB-09 | constraint | active | M004/S06 | none | unmapped |
| WEB-10 | compliance/security | active | M004/S02 | none | unmapped |
| WEB-11 | core-capability | validated | M004/S01 | M004/S05 | 31 API tests |
| WEB-12 | operability | active | M004/S07 | none | unmapped |
| WEB-13 | primary-user-loop | active | M004/S04 | none | unmapped |
| CLI-COMPAT-01 | constraint | validated | M004/S01 | none | 425 CLI tests pass |
| PREM-01 | core-capability | deferred | none | none | unmapped |
| PREM-02 | differentiator | deferred | none | none | unmapped |
| PREM-03 | differentiator | deferred | none | none | unmapped |
| PREM-04 | differentiator | deferred | none | none | unmapped |
| PREM-05 | differentiator | deferred | none | none | unmapped |
| PREM-06 | core-capability | deferred | none | none | unmapped |
| PREM-07 | core-capability | deferred | none | none | unmapped |
| PREM-08 | differentiator | deferred | none | none | unmapped |
| OOS-01 | constraint | out-of-scope | none | none | n/a |
| OOS-02 | constraint | out-of-scope | none | none | n/a |
| OOS-03 | constraint | out-of-scope | none | none | n/a |

## Coverage Summary

- Active requirements: 14
- Mapped to slices: 14
- Validated (prior milestones): 30
- Deferred: 8
- Out of scope: 3
- Unmapped active requirements: 0
14
- Validated (prior milestones): 30
- Deferred: 8
- Out of scope: 3
- Unmapped active requirements: 0
