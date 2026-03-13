"""Tests for screener.market_data -- Alpaca bar fetching and indicator computation."""

import logging as stdlib_logging
from unittest.mock import MagicMock, patch, call

import pandas as pd
import pytest

from screener.market_data import fetch_daily_bars, compute_indicators, compute_monthly_performance


# ---------------------------------------------------------------------------
# TestComputeIndicators -- pure function tests with synthetic DataFrames
# ---------------------------------------------------------------------------


class TestComputeIndicators:
    """Tests for compute_indicators() using synthetic bar DataFrames."""

    def _make_bars(self, n: int, close_val: float = 100.0, volume_val: float = 1_000_000.0) -> pd.DataFrame:
        """Create a synthetic bar DataFrame with n rows."""
        dates = pd.bdate_range(end="2026-03-06", periods=n)
        return pd.DataFrame(
            {"close": [close_val] * n, "volume": [volume_val] * n},
            index=dates,
        )

    def test_price_is_last_close(self):
        """price should be the last close value."""
        df = self._make_bars(50, close_val=123.45)
        result = compute_indicators(df)
        assert result["price"] == 123.45

    def test_avg_volume(self):
        """avg_volume should be the mean of all volume values."""
        dates = pd.bdate_range(end="2026-03-06", periods=3)
        df = pd.DataFrame(
            {"close": [100.0, 101.0, 102.0], "volume": [1000.0, 2000.0, 3000.0]},
            index=dates,
        )
        result = compute_indicators(df)
        assert result["avg_volume"] == 2000.0

    def test_rsi_with_sufficient_bars(self):
        """RSI(14) should be computed and be a float between 0-100 with 50+ bars."""
        # Use alternating prices to produce a non-trivial RSI
        dates = pd.bdate_range(end="2026-03-06", periods=50)
        closes = [100 + (i % 5) * 2.0 for i in range(50)]
        df = pd.DataFrame(
            {"close": closes, "volume": [1_000_000.0] * 50},
            index=dates,
        )
        result = compute_indicators(df)
        assert result["rsi_14"] is not None
        assert isinstance(result["rsi_14"], float)
        assert 0 <= result["rsi_14"] <= 100

    def test_rsi_with_insufficient_bars(self):
        """RSI(14) should be None when fewer than 30 bars are provided."""
        df = self._make_bars(20)
        result = compute_indicators(df)
        assert result["rsi_14"] is None

    def test_sma_with_sufficient_bars(self):
        """SMA(200) should equal close value when all closes are constant."""
        df = self._make_bars(210, close_val=100.0)
        result = compute_indicators(df)
        assert result["sma_200"] == pytest.approx(100.0, abs=0.01)

    def test_sma_with_insufficient_bars(self):
        """SMA(200) and above_sma200 should be None with fewer than 200 bars."""
        df = self._make_bars(150)
        result = compute_indicators(df)
        assert result["sma_200"] is None
        assert result["above_sma200"] is None

    def test_above_sma200_true(self):
        """above_sma200 should be True when last close > SMA(200)."""
        # 200 bars at 100.0, then 10 bars at 200.0 -- SMA(200) will be < 200.0
        dates = pd.bdate_range(end="2026-03-06", periods=210)
        closes = [100.0] * 200 + [200.0] * 10
        df = pd.DataFrame(
            {"close": closes, "volume": [1_000_000.0] * 210},
            index=dates,
        )
        result = compute_indicators(df)
        assert result["above_sma200"] is True

    def test_above_sma200_false(self):
        """above_sma200 should be False when last close < SMA(200)."""
        # 200 bars at 200.0, then 10 bars at 50.0 -- SMA(200) will be > 50.0
        dates = pd.bdate_range(end="2026-03-06", periods=210)
        closes = [200.0] * 200 + [50.0] * 10
        df = pd.DataFrame(
            {"close": closes, "volume": [1_000_000.0] * 210},
            index=dates,
        )
        result = compute_indicators(df)
        assert result["above_sma200"] is False

    def test_nan_converted_to_none(self):
        """NaN outputs from ta library should be converted to None, not float NaN."""
        # With exactly 30 bars and constant values, RSI might produce NaN
        # But with sufficient bars and constant prices, RSI is well-defined (0 or 100 or NaN)
        # Test with constant prices where RSI produces NaN (no up/down movement = 0 std dev)
        df = self._make_bars(50, close_val=100.0)
        result = compute_indicators(df)
        # With constant close prices, RSI change is 0, producing NaN in ta library
        # Verify it is None, not float NaN
        for key in ["rsi_14", "sma_200", "above_sma200"]:
            val = result.get(key)
            if val is None:
                continue
            # If not None, it should not be NaN
            if isinstance(val, float):
                assert not pd.isna(val), f"{key} should not be NaN, should be None or a valid float"


# ---------------------------------------------------------------------------
# TestFetchDailyBars -- mock Alpaca client
# ---------------------------------------------------------------------------


class TestFetchDailyBars:
    """Tests for fetch_daily_bars() with mocked Alpaca client."""

    def _make_mock_barset(self, symbols: list[str], n_bars: int = 10) -> MagicMock:
        """Create a mock barset response with multi-index DataFrame."""
        dfs = []
        for sym in symbols:
            dates = pd.bdate_range(end="2026-03-06", periods=n_bars)
            sym_df = pd.DataFrame(
                {
                    "open": [100.0] * n_bars,
                    "high": [105.0] * n_bars,
                    "low": [95.0] * n_bars,
                    "close": [102.0] * n_bars,
                    "volume": [1_000_000] * n_bars,
                },
                index=dates,
            )
            sym_df.index.name = "timestamp"
            # Add symbol level to index
            sym_df = pd.concat({sym: sym_df}, names=["symbol"])
            dfs.append(sym_df)
        barset = MagicMock()
        barset.df = pd.concat(dfs)
        return barset

    def test_batches_symbols(self):
        """fetch_daily_bars should batch symbols and call get_stock_bars once per batch."""
        client = MagicMock()
        symbols = [f"SYM{i}" for i in range(25)]

        # Each call returns a barset with some symbols
        def side_effect(request):
            batch_syms = request.symbol_or_symbols
            return self._make_mock_barset(batch_syms)

        client.get_stock_bars.side_effect = side_effect

        result = fetch_daily_bars(client, symbols, batch_size=10)

        # 25 symbols / 10 per batch = 3 calls
        assert client.get_stock_bars.call_count == 3

    def test_split_adjustment_used(self):
        """StockBarsRequest should use Adjustment.SPLIT."""
        from alpaca.data.enums import Adjustment

        client = MagicMock()
        client.get_stock_bars.return_value = self._make_mock_barset(["AAPL"])

        fetch_daily_bars(client, ["AAPL"])

        # Get the request object passed to get_stock_bars
        call_args = client.get_stock_bars.call_args
        request = call_args[0][0]
        assert request.adjustment == Adjustment.SPLIT

    def test_no_limit_parameter(self):
        """StockBarsRequest should NOT have a limit parameter set."""
        client = MagicMock()
        client.get_stock_bars.return_value = self._make_mock_barset(["AAPL"])

        fetch_daily_bars(client, ["AAPL"])

        call_args = client.get_stock_bars.call_args
        request = call_args[0][0]
        # limit should be None (not set)
        assert request.limit is None

    def test_missing_symbol_skipped(self):
        """Symbols not in the response should be silently excluded from results."""
        client = MagicMock()
        # Response only contains AAPL, not MSFT
        client.get_stock_bars.return_value = self._make_mock_barset(["AAPL"])

        result = fetch_daily_bars(client, ["AAPL", "MSFT"])

        assert "AAPL" in result
        assert "MSFT" not in result

    def test_returns_per_symbol_dataframes(self):
        """Each symbol should get its own DataFrame in the returned dict."""
        client = MagicMock()
        client.get_stock_bars.return_value = self._make_mock_barset(["AAPL", "MSFT", "GOOG"])

        result = fetch_daily_bars(client, ["AAPL", "MSFT", "GOOG"])

        assert len(result) == 3
        for sym in ["AAPL", "MSFT", "GOOG"]:
            assert sym in result
            assert isinstance(result[sym], pd.DataFrame)
            assert "close" in result[sym].columns
            assert "volume" in result[sym].columns


# ---------------------------------------------------------------------------
# TestComputeMonthlyPerformance -- pure math tests
# ---------------------------------------------------------------------------


class TestComputeMonthlyPerformance:
    """Tests for compute_monthly_performance() using synthetic bar DataFrames."""

    def _make_bars(self, closes: list[float]) -> pd.DataFrame:
        """Create a synthetic bar DataFrame from a list of close prices."""
        n = len(closes)
        dates = pd.bdate_range(end="2026-03-06", periods=n)
        return pd.DataFrame(
            {"close": closes, "volume": [1_000_000.0] * n},
            index=dates,
        )

    def test_exact_22_bars_computes_correctly(self):
        """With exactly 22 bars, should compute (close[-1]/close[-22] - 1)*100."""
        # close[0]=200, close[21]=210 => (210/200 - 1)*100 = 5.0
        closes = [200.0] + [205.0] * 20 + [210.0]
        df = self._make_bars(closes)
        result = compute_monthly_performance(df)
        assert result == pytest.approx(5.0)

    def test_250_bars_uses_last_22(self):
        """With 250 bars, should use iloc[-1] and iloc[-22], ignoring earlier data."""
        # 228 bars of noise, then close[-22]=80.0, 20 filler, close[-1]=100.0
        closes = [999.0] * 228 + [80.0] + [90.0] * 20 + [100.0]
        assert len(closes) == 250
        df = self._make_bars(closes)
        result = compute_monthly_performance(df)
        # (100/80 - 1)*100 = 25.0
        assert result == pytest.approx(25.0)

    def test_insufficient_data_returns_none(self):
        """With fewer than 22 bars, should return None."""
        closes = [100.0] * 21
        df = self._make_bars(closes)
        assert compute_monthly_performance(df) is None

    def test_negative_return(self):
        """Declining price should give a negative percentage."""
        # close[-22]=100, close[-1]=90 => (90/100 - 1)*100 = -10.0
        closes = [100.0] + [95.0] * 20 + [90.0]
        df = self._make_bars(closes)
        result = compute_monthly_performance(df)
        assert result == pytest.approx(-10.0)

    def test_positive_return(self):
        """Rising price should give a positive percentage."""
        # close[-22]=50, close[-1]=60 => (60/50 - 1)*100 = 20.0
        closes = [50.0] + [55.0] * 20 + [60.0]
        df = self._make_bars(closes)
        result = compute_monthly_performance(df)
        assert result == pytest.approx(20.0)

    def test_flat_return_is_zero(self):
        """Same close price over the period should give 0.0."""
        closes = [100.0] * 22
        df = self._make_bars(closes)
        result = compute_monthly_performance(df)
        assert result == pytest.approx(0.0)
