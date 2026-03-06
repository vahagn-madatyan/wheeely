# Technology Stack

**Analysis Date:** 2026-03-06

## Languages

**Primary:**
- Python >=3.8 - Entire codebase

**Secondary:**
- None

## Runtime

**Environment:**
- Python (CPython) >=3.8
- Uses `zoneinfo` (stdlib, Python 3.9+) in `core/broker_client.py` and `pytz` in `core/utils.py` for timezone handling

**Package Manager:**
- `uv` (recommended in `CLAUDE.md` for venv creation and package installation)
- `setuptools` >=61.0 as build backend
- Lockfile: Not present (no `requirements.txt` lock or `uv.lock` committed)

## Frameworks

**Core:**
- `alpaca-py` - Alpaca Trading API SDK. Primary external dependency; provides trading, stock data, and option data clients.

**Testing:**
- None configured. No test framework installed or test files present.

**Build/Dev:**
- `setuptools` >=61.0 - Build backend configured in `pyproject.toml`
- `uv` - Virtual environment and dependency management (not declared as a dependency, used as system tool)

## Key Dependencies

**Critical:**
- `alpaca-py` (unpinned) - Entire trading functionality depends on this SDK. Wraps three sub-clients: `TradingClient`, `StockHistoricalDataClient`, `OptionHistoricalDataClient`. Used in `core/broker_client.py`.
- `python-dotenv` (unpinned) - Loads `.env` credentials at startup. Used in `config/credentials.py`.

**Data/Computation:**
- `pandas` >=1.5 - Listed as dependency but not currently imported anywhere in the codebase.
- `numpy` >=1.23 - Used in `core/execution.py` for `np.argmax()` to select highest-scoring call option.

**Infrastructure:**
- `requests` >=2.28 - Listed as dependency; likely a transitive requirement of `alpaca-py`.
- `pytz` - Used in `core/utils.py` for New York timezone timestamps. Not declared in `pyproject.toml` (likely pulled in transitively).

## Configuration

**Environment:**
- `.env` file in project root (not committed to git)
- Required variables: `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `IS_PAPER` (defaults to `true`)
- Loaded via `python-dotenv` in `config/credentials.py`

**Strategy Parameters:**
- `config/params.py` - Hardcoded trading constants:
  - `MAX_RISK = 80_000`
  - `DELTA_MIN = 0.15`, `DELTA_MAX = 0.30`
  - `YIELD_MIN = 0.04`, `YIELD_MAX = 1.00`
  - `EXPIRATION_MIN = 0`, `EXPIRATION_MAX = 21`
  - `OPEN_INTEREST_MIN = 100`
  - `SCORE_MIN = 0.05`

**Symbol List:**
- `config/symbol_list.txt` - One ticker per line. Currently: AAPL, QQQ, INTC, CAT, DLR, MP, NVDA, PLTR, AAL, V

**Build:**
- `pyproject.toml` - Project metadata, dependencies, and console script entry point

## Entry Point

**Console Script:**
- `run-strategy` command registered in `pyproject.toml` via `[project.scripts]`
- Maps to `scripts/run_strategy.py:main()`
- Install with `uv pip install -e .`

**CLI Arguments (defined in `core/cli_args.py`):**
- `--fresh-start` - Liquidate all positions before running
- `--strat-log` - Enable JSON strategy logging to `logs/strategy_log.json`
- `--log-level` - DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)
- `--log-to-file` - Write logs to `logs/run.log`

## Platform Requirements

**Development:**
- Python >=3.9 (effectively, due to `zoneinfo` usage in `core/broker_client.py`)
- `uv` installed as system tool
- `.env` file with Alpaca API credentials
- Internet access for Alpaca API calls

**Production:**
- Same as development. No containerization, no deployment tooling.
- Designed as a CLI tool run manually or via scheduler (cron, etc.)

---

*Stack analysis: 2026-03-06*
