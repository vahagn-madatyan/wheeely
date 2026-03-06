# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Automated options wheel strategy bot using the Alpaca Trading API. Sells cash-secured puts on selected stocks, handles assignments, then sells covered calls — repeating the cycle to collect premiums.

## Setup & Commands

```bash
uv venv && source .venv/bin/activate
uv pip install -e .
```

Requires a `.env` file with `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, and `IS_PAPER=true|false`.

**Run the strategy:**
```bash
run-strategy                    # normal run
run-strategy --fresh-start      # liquidate all positions first
run-strategy --strat-log        # enable JSON strategy logging
run-strategy --log-level DEBUG --log-to-file
```

There are no tests in this project currently.

## Architecture

**Entry point:** `scripts/run_strategy.py:main()` — registered as `run-strategy` console script in `pyproject.toml`.

**Flow:** `main()` → check positions via `state_manager.update_state()` → sell covered calls on assigned stock → sell new puts on remaining symbols within buying power.

### Key Modules

- **`core/broker_client.py`** — `BrokerClient` wraps three Alpaca SDK clients (trading, stock data, option data) with `UserAgentMixin`. All API interaction goes through this class.
- **`core/strategy.py`** — Pure functions for filtering/scoring/selecting options. No API calls. Scoring formula: `(1 - |delta|) * (250 / (DTE + 5)) * (bid / strike)`.
- **`core/execution.py`** — `sell_puts()` and `sell_calls()` orchestrate the full pipeline: filter underlyings → fetch contracts → filter → score → select → place orders.
- **`core/state_manager.py`** — `update_state()` maps current positions to wheel states: `short_put`, `long_shares`, or `short_call`. `calculate_risk()` computes capital at risk.
- **`models/contract.py`** — `Contract` dataclass normalizing Alpaca's `OptionContract` and `OptionSnapshot` into a single object. Two constructors: `from_contract()` (fetches snapshot lazily via client) and `from_contract_snapshot()` (pre-joined data).
- **`config/params.py`** — Strategy tuning constants (delta range, yield range, DTE range, open interest minimum, score minimum, max risk).
- **`config/symbol_list.txt`** — One ticker per line. Only these symbols are traded.
- **`logging/strategy_logger.py`** — JSON logger for strategy decisions (separate from Python's `logging`). Note: the `logging/` package shadows Python's stdlib `logging` — imports use `from logging.logger_setup import ...` for the custom module.

### Important Patterns

- The project shadows Python's `logging` module with its own `logging/` package. The custom `logger_setup.py` internally imports `logging` (stdlib) via the package's `__init__.py`.
- `BrokerClient` paginates option contract fetches (1000 per page) and batches snapshot requests (100 per batch).
- Options are filtered to one contract per underlying symbol to promote diversification.
- Risk is tracked as `strike * 100` per short put and `entry_price * qty` per stock position.
