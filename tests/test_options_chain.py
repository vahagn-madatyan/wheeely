"""Tests for S09: Options Chain Validation.

Covers:
- filter_options_oi() pass/fail/None behavior
- filter_options_spread() pass/fail/None behavior
- compute_put_premium_yield() math and edge cases
- _find_nearest_atm_put() selection logic
- run_stage_3_options() orchestration with mocked API calls
- Preset YAML files contain options_oi_min and options_spread_max
- ScreenedStock has options chain fields
- OptionsConfig validates options_oi_min and options_spread_max
- Display table includes Yield column
- Filter breakdown includes options_oi and options_spread
- Pipeline integration: Stage 3 runs only after Stage 2 passes
- Pipeline backward compatibility: no option_client = no Stage 3
"""

from datetime import date, timedelta
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from models.screened_stock import FilterResult, ScreenedStock
from screener.config_loader import (
    OptionsConfig,
    ScreenerConfig,
    load_preset,
)
from screener.pipeline import (
    _find_nearest_atm_put,
    compute_put_premium_yield,
    filter_options_oi,
    filter_options_spread,
    run_stage_3_options,
)


PRESETS_DIR = Path(__file__).resolve().parent.parent / "config" / "presets"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_stock(**kwargs) -> ScreenedStock:
    """Create a ScreenedStock with custom fields set."""
    stock = ScreenedStock.from_symbol(kwargs.pop("symbol", "TEST"))
    for k, v in kwargs.items():
        setattr(stock, k, v)
    return stock


def _default_config(**overrides) -> ScreenerConfig:
    """Create a ScreenerConfig with defaults, applying overrides."""
    return ScreenerConfig.model_validate(overrides) if overrides else ScreenerConfig()


def _make_mock_contract(symbol, strike_price, expiration_date, open_interest=200):
    """Create a mock Alpaca OptionContract."""
    contract = MagicMock()
    contract.symbol = symbol
    contract.strike_price = strike_price
    contract.expiration_date = expiration_date
    contract.open_interest = open_interest
    contract.underlying_symbol = "TEST"
    return contract


def _make_mock_snapshot(bid_price, ask_price, open_interest=None):
    """Create a mock Alpaca OptionSnapshot with latest_quote."""
    snap = MagicMock()
    snap.latest_quote = MagicMock()
    snap.latest_quote.bid_price = bid_price
    snap.latest_quote.ask_price = ask_price
    if open_interest is not None:
        snap.open_interest = open_interest
    return snap


# ===========================================================================
# TestFilterOptionsOI
# ===========================================================================


class TestFilterOptionsOI:
    """filter_options_oi: pass/fail/None cases."""

    def test_oi_above_min_passes(self):
        stock = _make_stock(options_oi=500)
        config = _default_config()
        result = filter_options_oi(stock, config)
        assert result.passed is True
        assert result.filter_name == "options_oi"
        assert result.actual_value == 500.0
        assert result.reason == ""

    def test_oi_equal_to_min_passes(self):
        stock = _make_stock(options_oi=100)
        config = _default_config()  # default options_oi_min=100
        result = filter_options_oi(stock, config)
        assert result.passed is True

    def test_oi_below_min_fails(self):
        stock = _make_stock(options_oi=50)
        config = _default_config()  # default options_oi_min=100
        result = filter_options_oi(stock, config)
        assert result.passed is False
        assert result.actual_value == 50.0
        assert result.threshold == 100.0
        assert "below" in result.reason.lower()

    def test_oi_none_fails(self):
        stock = _make_stock(options_oi=None)
        config = _default_config()
        result = filter_options_oi(stock, config)
        assert result.passed is False
        assert result.actual_value is None
        assert "unavailable" in result.reason.lower()

    def test_oi_zero_below_default_fails(self):
        stock = _make_stock(options_oi=0)
        config = _default_config()
        result = filter_options_oi(stock, config)
        assert result.passed is False

    def test_oi_custom_threshold(self):
        stock = _make_stock(options_oi=300)
        config = _default_config(options={"options_oi_min": 500})
        result = filter_options_oi(stock, config)
        assert result.passed is False
        assert result.threshold == 500.0

    def test_oi_zero_threshold_passes_any(self):
        stock = _make_stock(options_oi=0)
        config = _default_config(options={"options_oi_min": 0})
        result = filter_options_oi(stock, config)
        assert result.passed is True


# ===========================================================================
# TestFilterOptionsSpread
# ===========================================================================


class TestFilterOptionsSpread:
    """filter_options_spread: pass/fail/None cases."""

    def test_spread_below_max_passes(self):
        stock = _make_stock(options_spread=0.05)  # 5%
        config = _default_config()  # default options_spread_max=0.10
        result = filter_options_spread(stock, config)
        assert result.passed is True
        assert result.filter_name == "options_spread"
        assert result.actual_value == 0.05
        assert result.reason == ""

    def test_spread_equal_to_max_passes(self):
        stock = _make_stock(options_spread=0.10)
        config = _default_config()  # default options_spread_max=0.10
        result = filter_options_spread(stock, config)
        assert result.passed is True

    def test_spread_above_max_fails(self):
        stock = _make_stock(options_spread=0.25)  # 25%
        config = _default_config()  # default options_spread_max=0.10
        result = filter_options_spread(stock, config)
        assert result.passed is False
        assert result.actual_value == 0.25
        assert result.threshold == 0.10
        assert "above" in result.reason.lower()

    def test_spread_none_fails(self):
        stock = _make_stock(options_spread=None)
        config = _default_config()
        result = filter_options_spread(stock, config)
        assert result.passed is False
        assert result.actual_value is None
        assert "unavailable" in result.reason.lower()

    def test_spread_custom_threshold(self):
        stock = _make_stock(options_spread=0.06)
        config = _default_config(options={"options_spread_max": 0.05})
        result = filter_options_spread(stock, config)
        assert result.passed is False

    def test_spread_wide_threshold(self):
        stock = _make_stock(options_spread=0.15)
        config = _default_config(options={"options_spread_max": 0.20})
        result = filter_options_spread(stock, config)
        assert result.passed is True


# ===========================================================================
# TestComputePutPremiumYield
# ===========================================================================


class TestComputePutPremiumYield:
    """compute_put_premium_yield: annualized yield math."""

    def test_basic_yield_computation(self):
        # bid=1.50, strike=50, DTE=30
        # yield = (1.50/50) * (365/30) * 100 = 3% * 12.17 = 36.5%
        result = compute_put_premium_yield(1.50, 50.0, 30)
        assert result is not None
        assert result == pytest.approx(36.5, abs=0.1)

    def test_low_yield(self):
        # bid=0.10, strike=100, DTE=45
        # yield = (0.10/100) * (365/45) * 100 = 0.1% * 8.11 = 0.81%
        result = compute_put_premium_yield(0.10, 100.0, 45)
        assert result is not None
        assert result == pytest.approx(0.81, abs=0.01)

    def test_high_yield(self):
        # bid=5.00, strike=25, DTE=14
        # yield = (5.00/25) * (365/14) * 100 = 20% * 26.07 = 521.4%
        result = compute_put_premium_yield(5.00, 25.0, 14)
        assert result is not None
        assert result == pytest.approx(521.43, abs=0.1)

    def test_zero_strike_returns_none(self):
        result = compute_put_premium_yield(1.50, 0.0, 30)
        assert result is None

    def test_zero_dte_returns_none(self):
        result = compute_put_premium_yield(1.50, 50.0, 0)
        assert result is None

    def test_negative_bid_returns_none(self):
        result = compute_put_premium_yield(-0.50, 50.0, 30)
        assert result is None

    def test_zero_bid_returns_zero(self):
        result = compute_put_premium_yield(0.0, 50.0, 30)
        assert result is not None
        assert result == 0.0

    def test_negative_strike_returns_none(self):
        result = compute_put_premium_yield(1.50, -50.0, 30)
        assert result is None


# ===========================================================================
# TestFindNearestAtmPut
# ===========================================================================


class TestFindNearestAtmPut:
    """_find_nearest_atm_put: ATM selection logic."""

    def test_finds_closest_strike(self):
        contracts = [
            _make_mock_contract("C1", 45.0, date.today() + timedelta(days=30)),
            _make_mock_contract("C2", 50.0, date.today() + timedelta(days=30)),
            _make_mock_contract("C3", 55.0, date.today() + timedelta(days=30)),
        ]
        result = _find_nearest_atm_put(contracts, 48.0)
        assert result.symbol == "C2"  # 50 is closest to 48

    def test_exact_match(self):
        contracts = [
            _make_mock_contract("C1", 45.0, date.today() + timedelta(days=30)),
            _make_mock_contract("C2", 50.0, date.today() + timedelta(days=30)),
        ]
        result = _find_nearest_atm_put(contracts, 50.0)
        assert result.symbol == "C2"

    def test_empty_list_returns_none(self):
        result = _find_nearest_atm_put([], 50.0)
        assert result is None

    def test_single_contract(self):
        contracts = [
            _make_mock_contract("ONLY", 55.0, date.today() + timedelta(days=30)),
        ]
        result = _find_nearest_atm_put(contracts, 100.0)
        assert result.symbol == "ONLY"

    def test_equidistant_picks_first(self):
        """When two strikes are equidistant, min() picks whichever comes first."""
        contracts = [
            _make_mock_contract("LOW", 45.0, date.today() + timedelta(days=30)),
            _make_mock_contract("HIGH", 55.0, date.today() + timedelta(days=30)),
        ]
        result = _find_nearest_atm_put(contracts, 50.0)
        # Both are distance 5 from 50; min returns first
        assert result is not None


# ===========================================================================
# TestRunStage3Options
# ===========================================================================


class TestRunStage3Options:
    """run_stage_3_options: orchestrates data fetch + filters + yield computation."""

    def _make_passing_stock(self, price=50.0):
        """Create a stock that has passed all prior stages."""
        return _make_stock(
            symbol="AAPL",
            price=price,
            options_oi=None,
            options_spread=None,
        )

    def _mock_clients(self, contracts=None, snapshot=None):
        """Create mock trade_client and option_client."""
        trade_client = MagicMock()
        option_client = MagicMock()

        # Mock get_option_contracts
        response = MagicMock()
        response.option_contracts = contracts or []
        trade_client.get_option_contracts.return_value = response

        # Mock get_option_snapshot
        option_client.get_option_snapshot.return_value = snapshot or {}

        return trade_client, option_client

    def test_liquid_option_passes_both_filters(self):
        stock = self._make_passing_stock(price=50.0)
        config = _default_config()

        exp_date = date.today() + timedelta(days=30)
        contracts = [
            _make_mock_contract("AAPL240401P00050000", 50.0, exp_date, open_interest=500),
        ]
        snap = _make_mock_snapshot(bid_price=1.50, ask_price=1.60)
        trade_client, option_client = self._mock_clients(
            contracts=contracts,
            snapshot={"AAPL240401P00050000": snap},
        )

        result = run_stage_3_options(stock, config, trade_client, option_client)

        assert result is True
        assert stock.options_oi == 500
        assert stock.best_put_strike == 50.0
        assert stock.best_put_bid == 1.50
        assert stock.best_put_ask == 1.60
        assert stock.options_spread is not None
        assert stock.put_premium_yield is not None
        assert stock.put_premium_yield > 0

    def test_low_oi_fails(self):
        stock = self._make_passing_stock(price=50.0)
        config = _default_config()  # options_oi_min=100

        exp_date = date.today() + timedelta(days=30)
        contracts = [
            _make_mock_contract("AAPL240401P00050000", 50.0, exp_date, open_interest=10),
        ]
        snap = _make_mock_snapshot(bid_price=1.50, ask_price=1.55)
        trade_client, option_client = self._mock_clients(
            contracts=contracts,
            snapshot={"AAPL240401P00050000": snap},
        )

        result = run_stage_3_options(stock, config, trade_client, option_client)

        assert result is False
        assert stock.options_oi == 10
        oi_result = next(r for r in stock.filter_results if r.filter_name == "options_oi")
        assert oi_result.passed is False

    def test_wide_spread_fails(self):
        stock = self._make_passing_stock(price=50.0)
        config = _default_config()  # options_spread_max=0.10

        exp_date = date.today() + timedelta(days=30)
        contracts = [
            _make_mock_contract("AAPL240401P00050000", 50.0, exp_date, open_interest=500),
        ]
        # Wide spread: bid=1.00, ask=2.00 → midpoint=1.50 → spread=1.00/1.50=66.7%
        snap = _make_mock_snapshot(bid_price=1.00, ask_price=2.00)
        trade_client, option_client = self._mock_clients(
            contracts=contracts,
            snapshot={"AAPL240401P00050000": snap},
        )

        result = run_stage_3_options(stock, config, trade_client, option_client)

        assert result is False
        spread_result = next(r for r in stock.filter_results if r.filter_name == "options_spread")
        assert spread_result.passed is False

    def test_no_contracts_fails_both_filters(self):
        stock = self._make_passing_stock(price=50.0)
        config = _default_config()

        trade_client, option_client = self._mock_clients(contracts=[], snapshot={})

        result = run_stage_3_options(stock, config, trade_client, option_client)

        assert result is False
        filter_names = {r.filter_name for r in stock.filter_results}
        assert "options_oi" in filter_names
        assert "options_spread" in filter_names

    def test_no_snapshot_fails(self):
        stock = self._make_passing_stock(price=50.0)
        config = _default_config()

        exp_date = date.today() + timedelta(days=30)
        contracts = [
            _make_mock_contract("AAPL240401P00050000", 50.0, exp_date, open_interest=500),
        ]
        # Snapshot returns empty dict (symbol not found)
        trade_client, option_client = self._mock_clients(
            contracts=contracts,
            snapshot={},
        )

        result = run_stage_3_options(stock, config, trade_client, option_client)

        assert result is False
        # OI should pass (from contract), but spread should fail (no snapshot)
        oi_result = next(r for r in stock.filter_results if r.filter_name == "options_oi")
        assert oi_result.passed is True
        spread_result = next(r for r in stock.filter_results if r.filter_name == "options_spread")
        assert spread_result.passed is False

    def test_yield_only_computed_when_both_pass(self):
        stock = self._make_passing_stock(price=50.0)
        config = _default_config()

        exp_date = date.today() + timedelta(days=30)
        contracts = [
            _make_mock_contract("AAPL240401P00050000", 50.0, exp_date, open_interest=10),
        ]
        snap = _make_mock_snapshot(bid_price=1.50, ask_price=1.55)
        trade_client, option_client = self._mock_clients(
            contracts=contracts,
            snapshot={"AAPL240401P00050000": snap},
        )

        result = run_stage_3_options(stock, config, trade_client, option_client)

        # OI fails → yield should not be computed
        assert result is False
        assert stock.put_premium_yield is None

    def test_api_exception_handled_gracefully(self):
        stock = self._make_passing_stock(price=50.0)
        config = _default_config()

        trade_client = MagicMock()
        option_client = MagicMock()
        trade_client.get_option_contracts.side_effect = Exception("API error")

        result = run_stage_3_options(stock, config, trade_client, option_client)

        assert result is False
        # Should have filter results even when API fails
        assert len(stock.filter_results) == 2

    def test_selects_nearest_atm_put(self):
        stock = self._make_passing_stock(price=52.0)
        config = _default_config(options={"options_oi_min": 0})

        exp_date = date.today() + timedelta(days=30)
        contracts = [
            _make_mock_contract("P45", 45.0, exp_date, open_interest=500),
            _make_mock_contract("P50", 50.0, exp_date, open_interest=500),
            _make_mock_contract("P55", 55.0, exp_date, open_interest=500),
        ]
        snap = _make_mock_snapshot(bid_price=1.50, ask_price=1.55)
        trade_client, option_client = self._mock_clients(
            contracts=contracts,
            snapshot={"P50": snap},
        )

        run_stage_3_options(stock, config, trade_client, option_client)

        # Price is 52, nearest strike is 50
        assert stock.best_put_strike == 50.0
        assert stock.best_put_symbol == "P50"

    def test_stock_no_price_fails(self):
        stock = _make_stock(symbol="NOPR", price=None)
        config = _default_config()

        trade_client, option_client = self._mock_clients()

        result = run_stage_3_options(stock, config, trade_client, option_client)

        assert result is False


# ===========================================================================
# TestOptionsConfigValidation
# ===========================================================================


class TestOptionsConfigValidation:
    """OptionsConfig Pydantic validation for OI and spread fields."""

    def test_default_values(self):
        cfg = OptionsConfig()
        assert cfg.options_oi_min == 100
        assert cfg.options_spread_max == 0.10

    def test_negative_oi_raises(self):
        with pytest.raises(Exception):
            OptionsConfig(options_oi_min=-1)

    def test_zero_spread_raises(self):
        with pytest.raises(Exception):
            OptionsConfig(options_spread_max=0)

    def test_spread_above_one_raises(self):
        with pytest.raises(Exception):
            OptionsConfig(options_spread_max=1.5)

    def test_valid_custom_values(self):
        cfg = OptionsConfig(options_oi_min=50, options_spread_max=0.20)
        assert cfg.options_oi_min == 50
        assert cfg.options_spread_max == 0.20

    def test_screener_config_options_section(self):
        cfg = ScreenerConfig.model_validate({
            "options": {
                "optionable": True,
                "options_oi_min": 250,
                "options_spread_max": 0.08,
            }
        })
        assert cfg.options.options_oi_min == 250
        assert cfg.options.options_spread_max == 0.08


# ===========================================================================
# TestPresetOptionsThresholds
# ===========================================================================


class TestPresetOptionsThresholds:
    """Preset YAML files contain differentiated options_oi_min and options_spread_max."""

    def test_conservative_preset_has_strict_options(self):
        data = load_preset("conservative")
        assert data["options"]["options_oi_min"] == 500
        assert data["options"]["options_spread_max"] == 0.05

    def test_moderate_preset_has_moderate_options(self):
        data = load_preset("moderate")
        assert data["options"]["options_oi_min"] == 100
        assert data["options"]["options_spread_max"] == 0.10

    def test_aggressive_preset_has_loose_options(self):
        data = load_preset("aggressive")
        assert data["options"]["options_oi_min"] == 50
        assert data["options"]["options_spread_max"] == 0.20

    def test_presets_differentiated(self):
        """All three presets must have different OI and spread thresholds."""
        c = load_preset("conservative")
        m = load_preset("moderate")
        a = load_preset("aggressive")

        oi_values = {
            c["options"]["options_oi_min"],
            m["options"]["options_oi_min"],
            a["options"]["options_oi_min"],
        }
        spread_values = {
            c["options"]["options_spread_max"],
            m["options"]["options_spread_max"],
            a["options"]["options_spread_max"],
        }
        assert len(oi_values) == 3, "All presets should have distinct OI thresholds"
        assert len(spread_values) == 3, "All presets should have distinct spread thresholds"

    def test_conservative_strictest(self):
        """Conservative should require the most OI and tightest spread."""
        c = load_preset("conservative")
        m = load_preset("moderate")
        a = load_preset("aggressive")

        assert c["options"]["options_oi_min"] > m["options"]["options_oi_min"]
        assert m["options"]["options_oi_min"] > a["options"]["options_oi_min"]
        assert c["options"]["options_spread_max"] < m["options"]["options_spread_max"]
        assert m["options"]["options_spread_max"] < a["options"]["options_spread_max"]


# ===========================================================================
# TestScreenedStockOptionsFields
# ===========================================================================


class TestScreenedStockOptionsFields:
    """ScreenedStock has options chain data fields."""

    def test_default_fields_are_none(self):
        stock = ScreenedStock.from_symbol("TEST")
        assert stock.options_oi is None
        assert stock.options_spread is None
        assert stock.put_premium_yield is None
        assert stock.best_put_symbol is None
        assert stock.best_put_strike is None
        assert stock.best_put_dte is None
        assert stock.best_put_bid is None
        assert stock.best_put_ask is None

    def test_fields_settable(self):
        stock = ScreenedStock.from_symbol("TEST")
        stock.options_oi = 500
        stock.options_spread = 0.05
        stock.put_premium_yield = 36.5
        stock.best_put_symbol = "TEST240401P00050000"
        stock.best_put_strike = 50.0
        stock.best_put_dte = 30
        stock.best_put_bid = 1.50
        stock.best_put_ask = 1.60

        assert stock.options_oi == 500
        assert stock.options_spread == 0.05
        assert stock.put_premium_yield == 36.5


# ===========================================================================
# TestDisplayYieldColumn
# ===========================================================================


class TestDisplayYieldColumn:
    """Display table includes Yield column for put premium yield."""

    def test_yield_column_in_results_table(self):
        from rich.console import Console
        from screener.display import render_results_table

        stock = _make_stock(
            symbol="AAPL",
            price=50.0,
            avg_volume=3_000_000,
            market_cap=2_000_000_000_000,
            debt_equity=0.5,
            net_margin=25.0,
            sales_growth=10.0,
            rsi_14=45.0,
            hv_percentile=60.0,
            put_premium_yield=36.5,
            sector="Technology",
            score=75.0,
        )
        # Make it pass all filters
        stock.filter_results.append(FilterResult(filter_name="test", passed=True))

        buf = StringIO()
        console = Console(file=buf, width=200)
        render_results_table([stock], console=console)
        output = buf.getvalue()

        assert "Yield" in output
        assert "36.5%" in output

    def test_yield_na_when_none(self):
        from rich.console import Console
        from screener.display import render_results_table

        stock = _make_stock(
            symbol="AAPL",
            price=50.0,
            avg_volume=3_000_000,
            put_premium_yield=None,
            score=75.0,
        )
        stock.filter_results.append(FilterResult(filter_name="test", passed=True))

        buf = StringIO()
        console = Console(file=buf, width=200)
        render_results_table([stock], console=console)
        output = buf.getvalue()

        assert "Yield" in output


# ===========================================================================
# TestDisplayFilterBreakdown
# ===========================================================================


class TestDisplayFilterBreakdown:
    """Filter breakdown includes options_oi and options_spread."""

    def test_options_filters_in_breakdown(self):
        from rich.console import Console
        from screener.display import render_filter_breakdown

        # Stock that fails options_oi
        stock = _make_stock(symbol="FAIL")
        stock.filter_results.append(
            FilterResult(filter_name="options_oi", passed=False, reason="OI too low")
        )

        buf = StringIO()
        console = Console(file=buf, width=120)
        render_filter_breakdown([stock], console=console)
        output = buf.getvalue()

        assert "options_oi" in output


# ===========================================================================
# TestDisplayStageSummary
# ===========================================================================


class TestDisplayStageSummary:
    """Stage summary includes Options stage when options filters present."""

    def test_options_stage_shown_when_present(self):
        from rich.console import Console
        from screener.display import render_stage_summary

        # Two stocks: one passes options, one fails
        stock_pass = _make_stock(symbol="PASS", price=50.0)
        stock_pass.filter_results = [
            FilterResult(filter_name="price_range", passed=True),
            FilterResult(filter_name="avg_volume", passed=True),
            FilterResult(filter_name="rsi", passed=True),
            FilterResult(filter_name="sma200", passed=True),
            FilterResult(filter_name="hv_percentile", passed=True),
            FilterResult(filter_name="earnings_proximity", passed=True),
            FilterResult(filter_name="market_cap", passed=True),
            FilterResult(filter_name="debt_equity", passed=True),
            FilterResult(filter_name="net_margin", passed=True),
            FilterResult(filter_name="sales_growth", passed=True),
            FilterResult(filter_name="sector", passed=True),
            FilterResult(filter_name="optionable", passed=True),
            FilterResult(filter_name="options_oi", passed=True),
            FilterResult(filter_name="options_spread", passed=True),
        ]
        stock_pass.score = 75.0

        stock_fail = _make_stock(symbol="FAIL", price=50.0)
        stock_fail.filter_results = [
            FilterResult(filter_name="price_range", passed=True),
            FilterResult(filter_name="avg_volume", passed=True),
            FilterResult(filter_name="rsi", passed=True),
            FilterResult(filter_name="sma200", passed=True),
            FilterResult(filter_name="hv_percentile", passed=True),
            FilterResult(filter_name="earnings_proximity", passed=True),
            FilterResult(filter_name="market_cap", passed=True),
            FilterResult(filter_name="debt_equity", passed=True),
            FilterResult(filter_name="net_margin", passed=True),
            FilterResult(filter_name="sales_growth", passed=True),
            FilterResult(filter_name="sector", passed=True),
            FilterResult(filter_name="optionable", passed=True),
            FilterResult(filter_name="options_oi", passed=False, reason="Low OI"),
            FilterResult(filter_name="options_spread", passed=False, reason="Wide spread"),
        ]

        buf = StringIO()
        console = Console(file=buf, width=120)
        render_stage_summary([stock_pass, stock_fail], console=console)
        output = buf.getvalue()

        assert "Options" in output

    def test_no_options_stage_when_absent(self):
        from rich.console import Console
        from screener.display import render_stage_summary

        stock = _make_stock(symbol="PASS", price=50.0)
        stock.filter_results = [
            FilterResult(filter_name="price_range", passed=True),
            FilterResult(filter_name="avg_volume", passed=True),
            FilterResult(filter_name="rsi", passed=True),
            FilterResult(filter_name="sma200", passed=True),
            FilterResult(filter_name="hv_percentile", passed=True),
            FilterResult(filter_name="earnings_proximity", passed=True),
            FilterResult(filter_name="market_cap", passed=True),
            FilterResult(filter_name="debt_equity", passed=True),
            FilterResult(filter_name="net_margin", passed=True),
            FilterResult(filter_name="sales_growth", passed=True),
            FilterResult(filter_name="sector", passed=True),
            FilterResult(filter_name="optionable", passed=True),
        ]
        stock.score = 75.0

        buf = StringIO()
        console = Console(file=buf, width=120)
        render_stage_summary([stock], console=console)
        output = buf.getvalue()

        # No "Options" line when no options filters present
        assert "Options" not in output


# ===========================================================================
# TestPipelineOptionsIntegration
# ===========================================================================


class TestPipelineOptionsIntegration:
    """Pipeline integration: Stage 3 only after Stage 2, backward compat."""

    def _setup_mocks(self):
        """Create common mocks for pipeline tests."""
        asset = MagicMock()
        asset.symbol = "PASS"
        asset.tradable = True

        opt = MagicMock()
        opt.symbol = "PASS"

        trade_client = MagicMock()
        trade_client.get_all_assets.side_effect = [
            [asset],
            [opt],
        ]

        # Mock option contracts response
        exp_date = date.today() + timedelta(days=30)
        contract = _make_mock_contract("PASS240401P00050000", 50.0, exp_date, 500)
        opt_response = MagicMock()
        opt_response.option_contracts = [contract]
        trade_client.get_option_contracts.return_value = opt_response

        stock_client = MagicMock()

        finnhub_client = MagicMock()
        finnhub_client.company_profile.return_value = {
            "marketCapitalization": 5000,
            "finnhubIndustry": "Technology",
        }
        finnhub_client.company_metrics.return_value = {
            "metric": {
                "totalDebtToEquity": 0.5,
                "netProfitMarginTTM": 15.0,
                "revenueGrowthQuarterlyYoy": 10.0,
            }
        }
        finnhub_client.earnings_for_symbol.return_value = None

        option_client = MagicMock()
        snap = _make_mock_snapshot(bid_price=1.50, ask_price=1.55)
        option_client.get_option_snapshot.return_value = {
            "PASS240401P00050000": snap,
        }

        config = ScreenerConfig.model_validate({
            "sectors": {"include": [], "exclude": []},
        })

        return trade_client, stock_client, finnhub_client, option_client, config

    def _make_bars_dict(self):
        np.random.seed(42)
        pass_prices = 25 + np.cumsum(np.random.normal(0, 0.1, 250))
        pass_df = pd.DataFrame({
            "close": pass_prices,
            "volume": [3_000_000] * 250,
        })
        return {"PASS": pass_df}

    def _make_indicators(self, df):
        close = df["close"]
        price = float(close.iloc[-1])
        volume = float(df["volume"].mean())
        return {
            "price": price,
            "avg_volume": volume,
            "rsi_14": 45.0,
            "sma_200": price - 1.0,
            "above_sma200": True,
        }

    @patch("screener.pipeline.fetch_daily_bars")
    @patch("screener.pipeline.compute_indicators")
    @patch("screener.pipeline.compute_hv_percentile")
    @patch("screener.pipeline.compute_historical_volatility")
    def test_stage3_runs_when_option_client_provided(
        self, mock_hv, mock_hv_pct, mock_indicators, mock_bars
    ):
        from screener.pipeline import run_pipeline

        trade_client, stock_client, finnhub_client, option_client, config = self._setup_mocks()
        mock_bars.return_value = self._make_bars_dict()
        mock_indicators.side_effect = lambda df: self._make_indicators(df)
        mock_hv.return_value = 0.35
        mock_hv_pct.return_value = 55.0

        result = run_pipeline(
            trade_client, stock_client, finnhub_client, config,
            symbol_list_path="/nonexistent/path.txt",
            option_client=option_client,
        )

        pass_stock = next(s for s in result if s.symbol == "PASS")
        filter_names = {r.filter_name for r in pass_stock.filter_results}
        assert "options_oi" in filter_names
        assert "options_spread" in filter_names

    @patch("screener.pipeline.fetch_daily_bars")
    @patch("screener.pipeline.compute_indicators")
    @patch("screener.pipeline.compute_hv_percentile")
    @patch("screener.pipeline.compute_historical_volatility")
    def test_stage3_skipped_without_option_client(
        self, mock_hv, mock_hv_pct, mock_indicators, mock_bars
    ):
        from screener.pipeline import run_pipeline

        trade_client, stock_client, finnhub_client, option_client, config = self._setup_mocks()
        mock_bars.return_value = self._make_bars_dict()
        mock_indicators.side_effect = lambda df: self._make_indicators(df)
        mock_hv.return_value = 0.35
        mock_hv_pct.return_value = 55.0

        # Run without option_client (backward compatible)
        result = run_pipeline(
            trade_client, stock_client, finnhub_client, config,
            symbol_list_path="/nonexistent/path.txt",
        )

        pass_stock = next(s for s in result if s.symbol == "PASS")
        filter_names = {r.filter_name for r in pass_stock.filter_results}
        assert "options_oi" not in filter_names
        assert "options_spread" not in filter_names
        # Stock should still pass and be scored
        assert pass_stock.passed_all_filters
        assert pass_stock.score is not None

    @patch("screener.pipeline.fetch_daily_bars")
    @patch("screener.pipeline.compute_indicators")
    @patch("screener.pipeline.compute_hv_percentile")
    @patch("screener.pipeline.compute_historical_volatility")
    def test_stage3_only_for_stage2_passers(
        self, mock_hv, mock_hv_pct, mock_indicators, mock_bars
    ):
        from screener.pipeline import run_pipeline

        trade_client, stock_client, finnhub_client, option_client, config = self._setup_mocks()

        # Add a second stock that will fail Stage 1 (price too low)
        asset_fail = MagicMock()
        asset_fail.symbol = "FAIL"
        asset_fail.tradable = True
        opt_fail = MagicMock()
        opt_fail.symbol = "FAIL"

        trade_client.get_all_assets.side_effect = [
            [
                MagicMock(symbol="PASS", tradable=True),
                asset_fail,
            ],
            [
                MagicMock(symbol="PASS"),
                opt_fail,
            ],
        ]

        bars = self._make_bars_dict()
        # FAIL stock: price=3 (below min)
        fail_prices = 3 + np.cumsum(np.random.normal(0, 0.01, 250))
        bars["FAIL"] = pd.DataFrame({
            "close": fail_prices,
            "volume": [3_000_000] * 250,
        })
        mock_bars.return_value = bars
        mock_indicators.side_effect = lambda df: self._make_indicators(df)
        mock_hv.return_value = 0.35
        mock_hv_pct.return_value = 55.0

        result = run_pipeline(
            trade_client, stock_client, finnhub_client, config,
            symbol_list_path="/nonexistent/path.txt",
            option_client=option_client,
        )

        fail_stock = next(s for s in result if s.symbol == "FAIL")
        filter_names = {r.filter_name for r in fail_stock.filter_results}
        # FAIL should NOT have options chain filters (failed earlier)
        assert "options_oi" not in filter_names
        assert "options_spread" not in filter_names


# ===========================================================================
# TestSpreadComputation
# ===========================================================================


class TestSpreadComputation:
    """Verify spread computation in _fetch_options_chain_data."""

    def test_spread_computation_tight(self):
        """Tight spread: bid=1.50, ask=1.55 → midpoint=1.525 → spread≈3.3%."""
        stock = _make_stock(symbol="TIGHT", price=50.0)
        stock.best_put_bid = 1.50
        stock.best_put_ask = 1.55
        midpoint = (1.50 + 1.55) / 2
        expected_spread = (1.55 - 1.50) / midpoint
        assert expected_spread == pytest.approx(0.0328, abs=0.001)

    def test_spread_computation_wide(self):
        """Wide spread: bid=0.50, ask=1.00 → midpoint=0.75 → spread≈66.7%."""
        midpoint = (0.50 + 1.00) / 2
        expected_spread = (1.00 - 0.50) / midpoint
        assert expected_spread == pytest.approx(0.6667, abs=0.001)
