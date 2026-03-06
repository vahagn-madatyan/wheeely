# Architecture

**Analysis Date:** 2026-03-06

## Pattern Overview

**Overall:** Pipeline / Procedural Script with Layered Modules

**Key Characteristics:**
- Single entry-point CLI script that orchestrates a linear pipeline: read state, act on positions, scan for new trades
- Clear separation between API access (`core/broker_client.py`), pure strategy logic (`core/strategy.py`), and orchestration (`core/execution.py`)
- No web server, no event loop, no async -- runs once per invocation (designed to be cron-scheduled or manually triggered)
- State is read from the broker API on each run; no local database or persistent state beyond JSON strategy logs

## Layers

**CLI / Entry Point:**
- Purpose: Parse arguments, wire dependencies, orchestrate the top-level run flow
- Location: `scripts/run_strategy.py`
- Contains: `main()` function registered as `run-strategy` console script
- Depends on: every other layer (config, core, models, logging)
- Used by: end user via CLI

**Configuration:**
- Purpose: Provide credentials and strategy tuning parameters
- Location: `config/`
- Contains: `credentials.py` (loads `.env`), `params.py` (strategy constants), `symbol_list.txt` (tradeable tickers)
- Depends on: `.env` file, `python-dotenv`
- Used by: `core/broker_client.py`, `core/strategy.py`, `scripts/run_strategy.py`

**Broker Client (API Adapter):**
- Purpose: Wrap Alpaca SDK clients into a single facade with pagination and batching
- Location: `core/broker_client.py`
- Contains: `BrokerClient` class with methods for positions, orders, option contracts, snapshots, stock trades
- Depends on: `alpaca-py` SDK, `config/params.py` (expiration range), `core/user_agent_mixin.py`
- Used by: `core/execution.py`, `models/contract.py` (lazy update), `scripts/run_strategy.py`

**Strategy (Pure Logic):**
- Purpose: Filter, score, and select option contracts -- no API calls
- Location: `core/strategy.py`
- Contains: `filter_underlying()`, `filter_options()`, `score_options()`, `select_options()` -- all pure functions (except `filter_underlying` which calls client for latest trade prices)
- Depends on: `config/params.py` for thresholds
- Used by: `core/execution.py`

**Execution (Orchestration):**
- Purpose: Wire together broker client + strategy functions to execute trades
- Location: `core/execution.py`
- Contains: `sell_puts()` and `sell_calls()` functions
- Depends on: `core/strategy.py`, `models/contract.py`, `core/broker_client.py`
- Used by: `scripts/run_strategy.py`

**State Manager:**
- Purpose: Interpret current positions to determine wheel state per symbol
- Location: `core/state_manager.py`
- Contains: `update_state()` (maps positions to wheel states), `calculate_risk()` (computes capital at risk)
- Depends on: `core/utils.py` (option symbol parsing), `alpaca.trading.enums`
- Used by: `scripts/run_strategy.py`

**Models:**
- Purpose: Normalize Alpaca SDK objects into a consistent internal representation
- Location: `models/contract.py`
- Contains: `Contract` dataclass with two constructors and serialization
- Depends on: `core/broker_client.py` (optional lazy update), `core/utils.py`
- Used by: `core/execution.py`

**Logging:**
- Purpose: Dual logging system -- Python stdlib logger + custom JSON strategy logger
- Location: `logging/`
- Contains: `logger_setup.py` (configures Python logging), `strategy_logger.py` (`StrategyLogger` class for JSON audit trail)
- Depends on: Python stdlib `logging`, `core/utils.py`
- Used by: `scripts/run_strategy.py`, `core/execution.py`

## Data Flow

**Normal Run (no --fresh-start):**

1. `main()` loads symbols from `config/symbol_list.txt` and creates `BrokerClient`
2. `client.get_positions()` fetches all current positions from Alpaca
3. `calculate_risk(positions)` computes total capital at risk
4. `update_state(positions)` categorizes each symbol as `short_put`, `long_shares`, or `short_call`
5. For each symbol in `long_shares` state: `sell_calls()` finds and sells a covered call
6. Remaining symbols (not in any state) become `allowed_symbols`
7. `buying_power = MAX_RISK - current_risk` determines available capital
8. `sell_puts()` scans allowed symbols and sells puts within buying power
9. `strat_logger.save()` appends the run's decisions to `logs/strategy_log.json`

**Fresh Start Run:**

1. `client.liquidate_all_positions()` closes all positions (options first, then equities)
2. All symbols become allowed, buying power set to `MAX_RISK`
3. `sell_puts()` executes on all symbols
4. Strategy log saved

**sell_puts() Pipeline:**

1. `filter_underlying()` -- remove symbols whose stock price * 100 exceeds buying power
2. `client.get_options_contracts()` -- fetch all put contracts in DTE range (paginated, 1000/page)
3. `client.get_option_snapshot()` -- fetch market data for all contracts (batched, 100/batch)
4. Construct `Contract` objects via `Contract.from_contract_snapshot()`
5. `filter_options()` -- apply delta, yield, and open interest filters
6. `score_options()` -- compute risk-adjusted annualized return score
7. `select_options()` -- pick best per underlying, sort by score
8. Iterate selected options, sell via `client.market_sell()` until buying power exhausted

**sell_calls() Pipeline:**

1. `client.get_options_contracts()` -- fetch call contracts for the specific symbol
2. Construct `Contract` objects via `Contract.from_contract()` (lazy snapshot fetch per contract)
3. `filter_options(min_strike=purchase_price)` -- only sell calls above entry price
4. `score_options()` + `np.argmax()` -- pick the single highest-scoring call
5. `client.market_sell()` -- place the order

**State Management:**
- No local database; state is derived from Alpaca positions on each run
- `update_state()` returns a dict keyed by underlying symbol with values like `{"type": "short_put", "price": None}` or `{"type": "long_shares", "price": 150.0, "qty": 100}`
- Intermediate state `short_call_awaiting_stock` is used during processing when a short call is seen before its corresponding stock position; resolved to `short_call` once stock is found

## Key Abstractions

**BrokerClient:**
- Purpose: Single facade over three Alpaca SDK clients (trading, stock data, option data)
- Examples: `core/broker_client.py`
- Pattern: Facade with internal pagination (option contracts: 1000/page) and batching (snapshots: 100/batch)

**Contract:**
- Purpose: Normalized option contract with market data, independent of Alpaca SDK types
- Examples: `models/contract.py`
- Pattern: Dataclass with multiple constructors (`from_contract`, `from_contract_snapshot`, `from_dict`) and optional lazy update via client reference

**Wheel State Machine:**
- Purpose: Track each symbol's position in the options wheel cycle
- Examples: `core/state_manager.py`
- Pattern: Position list mapped to state dict; states are `short_put` -> `long_shares` -> `short_call` -> (cycle repeats)

**StrategyLogger:**
- Purpose: JSON audit trail of each strategy run's decisions
- Examples: `logging/strategy_logger.py`
- Pattern: Builder -- accumulates log entries via setter methods, writes on `save()`

## Entry Points

**`run-strategy` CLI command:**
- Location: `scripts/run_strategy.py:main()`
- Triggers: Console script registered in `pyproject.toml` (`[project.scripts]`), or direct `python -m scripts.run_strategy`
- Responsibilities: Parse CLI args, initialize clients and loggers, orchestrate the full wheel strategy run
- CLI flags: `--fresh-start`, `--strat-log`, `--log-level {DEBUG,INFO,...}`, `--log-to-file`

## Error Handling

**Strategy:** Fail-fast with `ValueError` exceptions

**Patterns:**
- `state_manager.py` raises `ValueError` on unexpected position states (e.g., long options, short stock, conflicting states)
- `execution.py` raises `ValueError` if fewer than 100 shares available for covered calls
- `utils.py` raises `ValueError` on malformed OCC option symbols
- `broker_client.py` raises `ValueError` on invalid input types to `get_option_snapshot()`
- No try/except blocks in the main flow -- unhandled exceptions propagate and crash the run
- No retry logic for API failures

## Cross-Cutting Concerns

**Logging:** Dual system -- Python stdlib `logging` (via `logging/logger_setup.py`) for runtime messages, and `StrategyLogger` (via `logging/strategy_logger.py`) for structured JSON decision audit. The custom `logging/` package shadows Python's stdlib `logging` module; internal imports resolve correctly via the package's `__init__.py`.

**Validation:** Inline in `state_manager.py` and `execution.py` via `ValueError` raises. No schema validation library. `filter_options()` implicitly validates that delta and open interest are non-None.

**Authentication:** Alpaca API keys loaded from `.env` via `python-dotenv` in `config/credentials.py`. Keys passed to `BrokerClient` constructor. Custom `User-Agent` header injected via `UserAgentMixin` (MRO-based mixin on Alpaca SDK clients).

---

*Architecture analysis: 2026-03-06*
