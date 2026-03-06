# Testing Patterns

**Analysis Date:** 2026-03-06

## Test Framework

**Runner:**
- No test framework is configured
- No test runner, assertion library, or coverage tool is installed
- `CLAUDE.md` explicitly states: "There are no tests in this project currently."

**Dependencies:**
- `pyproject.toml` lists no test dependencies (no `pytest`, `unittest`, `tox`, `coverage`, etc.)
- No `[project.optional-dependencies]` section for test extras

**Run Commands:**
```bash
# No test commands exist. When tests are added, the recommended setup:
pip install pytest pytest-cov
pytest                        # Run all tests
pytest -v                     # Verbose output
pytest --cov=core --cov=models  # Coverage for core modules
```

## Test File Organization

**Location:**
- No test files exist anywhere in the repository
- No `tests/` directory, no `test_*.py` files, no `conftest.py`

**Recommended Structure (when adding tests):**
```
tests/
├── conftest.py              # Shared fixtures (mock BrokerClient, sample Contract data)
├── test_strategy.py         # Pure function tests (filter, score, select)
├── test_state_manager.py    # State mapping and risk calculation
├── test_contract.py         # Contract dataclass constructors, serialization
├── test_utils.py            # parse_option_symbol, get_ny_timestamp
├── test_execution.py        # Integration tests for sell_puts/sell_calls
└── test_broker_client.py    # BrokerClient method tests (mocked API)
```

**Naming:**
- Use `test_` prefix matching the module name: `test_strategy.py` for `core/strategy.py`
- Place tests in a top-level `tests/` directory (not co-located)

## Test Structure

**Recommended Suite Organization:**
```python
# tests/test_strategy.py
import pytest
from core.strategy import filter_options, score_options, select_options
from models.contract import Contract

class TestFilterOptions:
    def test_filters_by_delta_range(self):
        # Arrange: create contracts with known delta values
        # Act: call filter_options
        # Assert: only contracts within DELTA_MIN..DELTA_MAX remain

    def test_filters_by_open_interest(self):
        ...

    def test_filters_by_yield_range(self):
        ...

    def test_returns_empty_for_no_matches(self):
        ...

class TestScoreOptions:
    def test_score_formula(self):
        # Verify: (1 - |delta|) * (250 / (dte + 5)) * (bid_price / strike)
        ...

class TestSelectOptions:
    def test_keeps_best_per_underlying(self):
        ...

    def test_respects_score_minimum(self):
        ...

    def test_limits_to_top_n(self):
        ...
```

**Patterns:**
- Group tests by function or class using `class Test*`
- Use descriptive method names: `test_<what>_<condition>` or `test_<what>_<expected_result>`
- Arrange-Act-Assert structure

## Mocking

**Recommended Approach:**
```python
# tests/conftest.py
import pytest
from unittest.mock import MagicMock
from core.broker_client import BrokerClient

@pytest.fixture
def mock_client():
    """Mock BrokerClient with no real API calls."""
    client = MagicMock(spec=BrokerClient)
    return client
```

**What to Mock:**
- `BrokerClient` and all its methods (wraps Alpaca API -- never call real API in tests)
- `StrategyLogger` (pass `enabled=False` or mock to avoid file I/O)
- `datetime.date.today()` and `datetime.datetime.now()` for deterministic DTE calculations

**What NOT to Mock:**
- Pure functions in `core/strategy.py` (filter, score, select) -- test these directly
- `Contract` dataclass construction and serialization
- `core/utils.py` functions like `parse_option_symbol()`
- `core/state_manager.py` functions (operate on plain data, no I/O)

## Fixtures and Factories

**Recommended Test Data:**
```python
# tests/conftest.py
from models.contract import Contract

@pytest.fixture
def sample_put_contract():
    """A Contract with realistic put option values."""
    return Contract(
        underlying="AAPL",
        symbol="AAPL250516P00207500",
        contract_type="put",
        dte=14,
        strike=207.5,
        delta=-0.20,
        bid_price=3.50,
        ask_price=3.80,
        last_price=3.65,
        oi=500,
        underlying_price=210.0,
    )

@pytest.fixture
def sample_call_contract():
    return Contract(
        underlying="AAPL",
        symbol="AAPL250516C00215000",
        contract_type="call",
        dte=14,
        strike=215.0,
        delta=0.25,
        bid_price=2.10,
        ask_price=2.40,
        last_price=2.25,
        oi=300,
        underlying_price=210.0,
    )
```

**Location:**
- Shared fixtures in `tests/conftest.py`
- Test-specific data inline in each test file

## Coverage

**Requirements:** None enforced (no tests exist)

**Recommended Targets:**
- `core/strategy.py` -- highest priority, pure functions, easy to test
- `core/state_manager.py` -- complex state mapping logic with many edge cases
- `core/utils.py` -- `parse_option_symbol()` has clear input/output contract
- `models/contract.py` -- dataclass constructors and serialization

**Setup Coverage:**
```bash
pip install pytest-cov
pytest --cov=core --cov=models --cov-report=term-missing
```

## Test Types

**Unit Tests (recommended first priority):**
- `core/strategy.py`: All 4 functions are pure and testable in isolation
- `core/state_manager.py`: `update_state()` and `calculate_risk()` take plain position data
- `core/utils.py`: `parse_option_symbol()` is a pure parsing function
- `models/contract.py`: Dataclass construction, `to_dict()`, `from_dict()`, JSON round-trip

**Integration Tests (recommended second priority):**
- `core/execution.py`: `sell_puts()` and `sell_calls()` with mocked `BrokerClient`
- `scripts/run_strategy.py`: `main()` end-to-end with mocked client and file system

**E2E Tests:**
- Not applicable (live trading API; use paper trading manually)

## Common Patterns

**Testing parse_option_symbol:**
```python
# tests/test_utils.py
from core.utils import parse_option_symbol
import pytest

def test_parse_standard_symbol():
    underlying, opt_type, strike = parse_option_symbol("AAPL250516P00207500")
    assert underlying == "AAPL"
    assert opt_type == "P"
    assert strike == 207.5

def test_parse_invalid_symbol_raises():
    with pytest.raises(ValueError, match="Invalid option symbol format"):
        parse_option_symbol("INVALID")
```

**Testing state_manager with mock positions:**
```python
# tests/test_state_manager.py
from unittest.mock import MagicMock
from alpaca.trading.enums import AssetClass
from core.state_manager import update_state, calculate_risk

def make_position(symbol, asset_class, qty, avg_entry_price=100.0):
    pos = MagicMock()
    pos.symbol = symbol
    pos.asset_class = asset_class
    pos.qty = str(qty)
    pos.avg_entry_price = str(avg_entry_price)
    return pos

def test_short_put_state():
    pos = make_position("AAPL250516P00207500", AssetClass.US_OPTION, -1)
    state = update_state([pos])
    assert state["AAPL"]["type"] == "short_put"

def test_long_shares_state():
    pos = make_position("AAPL", AssetClass.US_EQUITY, 100, 150.0)
    state = update_state([pos])
    assert state["AAPL"]["type"] == "long_shares"
    assert state["AAPL"]["price"] == 150.0
```

**Testing Contract serialization:**
```python
# tests/test_contract.py
from models.contract import Contract

def test_to_dict_round_trip():
    c = Contract(underlying="AAPL", symbol="AAPL250516P00207500", contract_type="put",
                 dte=14, strike=207.5, delta=-0.20, bid_price=3.50)
    d = c.to_dict()
    c2 = Contract.from_dict(d)
    assert c2.underlying == c.underlying
    assert c2.strike == c.strike
```

---

*Testing analysis: 2026-03-06*
