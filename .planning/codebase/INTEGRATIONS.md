# External Integrations

**Analysis Date:** 2026-03-06

## APIs & External Services

**Alpaca Trading API:**
- Purpose: All brokerage operations -- account positions, option contract discovery, market data, order execution
- SDK: `alpaca-py` package
- Auth: API key + secret key via env vars `ALPACA_API_KEY` and `ALPACA_SECRET_KEY`
- Paper/Live toggle: `IS_PAPER` env var (defaults to `true`)
- Client wrapper: `core/broker_client.py` `BrokerClient` class

**Alpaca Sub-Clients (all instantiated in `core/broker_client.py`):**

1. `TradingClient` (via `TradingClientSigned`)
   - Get all positions: `get_all_positions()`
   - Get option contracts: `get_option_contracts()` with pagination (1000 per page)
   - Submit market orders: `submit_order()`
   - Close positions: `close_position()`

2. `StockHistoricalDataClient` (via `StockHistoricalDataClientSigned`)
   - Get latest stock trade prices: `get_stock_latest_trade()`
   - Used to filter symbols by buying power in `core/strategy.py:filter_underlying()`

3. `OptionHistoricalDataClient` (via `OptionHistoricalDataClientSigned`)
   - Get option snapshots (greeks, quotes, trades): `get_option_snapshot()`
   - Batched in groups of 100 symbols per request in `core/broker_client.py`

**Custom User-Agent:**
- All three clients use `UserAgentMixin` (`core/user_agent_mixin.py`) to set `User-Agent: OPTIONS-WHEEL` header

## Data Storage

**Databases:**
- None. No database is used.

**File Storage:**
- `config/symbol_list.txt` - Static list of tradeable tickers (read at startup)
- `logs/strategy_log.json` - Append-only JSON array of strategy run entries (created by `logging/strategy_logger.py`)
- `logs/run.log` - Standard log file (optional, enabled with `--log-to-file` flag)
- `Contract.save_to_json()` / `Contract.load_from_json()` in `models/contract.py` - JSON serialization for contract data (utility methods, not used in main flow currently)

**Caching:**
- None

## Authentication & Identity

**Auth Provider:**
- Alpaca API key authentication (not OAuth)
- Implementation: Key pair loaded from `.env` via `python-dotenv` in `config/credentials.py`
- Passed directly to `BrokerClient` constructor in `scripts/run_strategy.py`

## Monitoring & Observability

**Error Tracking:**
- None. Errors propagate as unhandled exceptions.

**Logging:**
- Two separate logging systems:
  1. **Python stdlib `logging`** via `logging/logger_setup.py` - Runtime messages to stdout and optionally `logs/run.log`
     - Logger name: `"strategy"`
     - Console format: `[%(message)s]`
     - File format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
  2. **Custom JSON strategy logger** via `logging/strategy_logger.py` - Structured strategy decision data to `logs/strategy_log.json`
     - Records: positions, state, buying power, symbols, filtered options, sold contracts
     - Append-only JSON array format

## CI/CD & Deployment

**Hosting:**
- None. Local CLI tool.

**CI Pipeline:**
- None configured.

## Environment Configuration

**Required env vars:**
- `ALPACA_API_KEY` - Alpaca API key
- `ALPACA_SECRET_KEY` - Alpaca secret key

**Optional env vars:**
- `IS_PAPER` - Set to `"false"` for live trading (defaults to `"true"` for paper trading)

**Secrets location:**
- `.env` file in project root (not committed)

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## API Rate Limiting & Pagination

**Pagination:**
- Option contract fetches paginate with `next_page_token`, 1000 contracts per page (`core/broker_client.py:get_options_contracts()`)

**Batching:**
- Option snapshot requests batched in groups of 100 symbols (`core/broker_client.py:get_option_snapshot()`)

**Rate Limiting:**
- No explicit rate limiting implemented. Relies on Alpaca SDK defaults.

---

*Integration audit: 2026-03-06*
