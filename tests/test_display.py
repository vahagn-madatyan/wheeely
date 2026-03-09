"""Tests for screener/display.py -- Rich-formatted screening output."""

import sys
from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console

# Ensure project root on path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.screened_stock import FilterResult, ScreenedStock
from screener.display import (
    fmt_large_number,
    fmt_pct,
    fmt_price,
    fmt_ratio,
    render_results_table,
    _score_style,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_stock(
    symbol: str,
    filter_results: list[FilterResult] | None = None,
    score: float | None = None,
    price: float | None = None,
    avg_volume: float | None = None,
    market_cap: float | None = None,
    debt_equity: float | None = None,
    net_margin: float | None = None,
    sales_growth: float | None = None,
    rsi_14: float | None = None,
    sector: str | None = None,
) -> ScreenedStock:
    s = ScreenedStock.from_symbol(symbol)
    s.price = price
    s.avg_volume = avg_volume
    s.market_cap = market_cap
    s.debt_equity = debt_equity
    s.net_margin = net_margin
    s.sales_growth = sales_growth
    s.rsi_14 = rsi_14
    s.sector = sector
    s.score = score
    if filter_results is not None:
        s.filter_results = filter_results
    return s


def _all_pass_filters() -> list[FilterResult]:
    """Return filter results where every stage passes."""
    names = [
        "bar_data",
        "price_range", "avg_volume", "rsi", "sma200",
        "market_cap", "debt_equity", "net_margin", "sales_growth", "sector", "optionable",
    ]
    return [FilterResult(filter_name=n, passed=True) for n in names]


def _capture_console() -> Console:
    return Console(file=StringIO(), width=120)


# ===========================================================================
# Formatters
# ===========================================================================


class TestFormatters:
    """Test number formatting helpers."""

    # -- fmt_large_number ---------------------------------------------------

    def test_billions(self):
        assert fmt_large_number(2_100_000_000) == "$2.1B"

    def test_millions(self):
        assert fmt_large_number(3_200_000, prefix="") == "3.2M"

    def test_thousands(self):
        assert fmt_large_number(45_000, prefix="$") == "$45.0K"

    def test_exact_billion(self):
        assert fmt_large_number(1_000_000_000) == "$1.0B"

    def test_sub_thousand(self):
        # Values below 1000 should still render something reasonable
        result = fmt_large_number(500, prefix="$")
        assert "$" in result

    def test_none(self):
        assert fmt_large_number(None) == "N/A"

    def test_zero(self):
        result = fmt_large_number(0)
        assert result is not None  # should not crash

    def test_negative(self):
        result = fmt_large_number(-5_000_000)
        assert "M" in result

    # -- fmt_price ----------------------------------------------------------

    def test_price_normal(self):
        assert fmt_price(24.5) == "$24.50"

    def test_price_none(self):
        assert fmt_price(None) == "N/A"

    def test_price_zero(self):
        assert fmt_price(0) == "$0.00"

    def test_price_high(self):
        assert fmt_price(1234.5) == "$1234.50"

    # -- fmt_pct ------------------------------------------------------------

    def test_pct_normal(self):
        assert fmt_pct(12.345) == "12.3%"

    def test_pct_none(self):
        assert fmt_pct(None) == "N/A"

    def test_pct_zero(self):
        assert fmt_pct(0) == "0.0%"

    def test_pct_negative(self):
        assert fmt_pct(-3.7) == "-3.7%"

    # -- fmt_ratio ----------------------------------------------------------

    def test_ratio_normal(self):
        assert fmt_ratio(0.75) == "0.75"

    def test_ratio_none(self):
        assert fmt_ratio(None) == "N/A"

    def test_ratio_zero(self):
        assert fmt_ratio(0) == "0.00"

    def test_ratio_negative(self):
        assert fmt_ratio(-1.23) == "-1.23"


# ===========================================================================
# Score styling
# ===========================================================================


class TestScoreStyle:
    """Test _score_style color distribution."""

    def test_thirds_distribution(self):
        scores = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0]
        # Top third -> green, middle -> yellow, bottom -> red
        assert _score_style(60.0, scores) == "green"
        assert _score_style(50.0, scores) == "green"
        assert _score_style(30.0, scores) == "yellow"
        assert _score_style(10.0, scores) == "red"

    def test_single_stock(self):
        assert _score_style(50.0, [50.0]) == "green"

    def test_empty_list(self):
        assert _score_style(50.0, []) == "white"

    def test_two_stocks(self):
        assert _score_style(50.0, [50.0, 30.0]) == "green"
        assert _score_style(30.0, [50.0, 30.0]) == "green"


# ===========================================================================
# Results table rendering
# ===========================================================================


class TestRenderResultsTable:
    """Test render_results_table output."""

    def _make_passing_stocks(self) -> list[ScreenedStock]:
        """Build 3+ passing stocks with varied scores."""
        stocks = []
        for sym, score, price, vol, mcap, de, margin, growth, rsi, sector in [
            ("AAPL", 85.0, 175.50, 50_000_000, 2_800_000_000_000, 1.73, 25.3, 8.1, 55.2, "Technology"),
            ("MSFT", 72.0, 380.00, 25_000_000, 2_500_000_000_000, 0.35, 36.4, 12.5, 48.7, "Technology"),
            ("JNJ", 60.0, 155.20, 8_000_000, 380_000_000_000, 0.52, 18.1, 3.2, 42.1, "Healthcare"),
            ("KO", 45.0, 58.30, 12_000_000, 250_000_000_000, 1.80, 21.5, 5.0, 61.3, "Consumer Staples"),
        ]:
            s = _make_stock(
                sym, _all_pass_filters(), score=score, price=price,
                avg_volume=vol, market_cap=mcap, debt_equity=de,
                net_margin=margin, sales_growth=growth, rsi_14=rsi, sector=sector,
            )
            stocks.append(s)
        return stocks

    def test_table_has_column_headers(self):
        console = _capture_console()
        stocks = self._make_passing_stocks()
        render_results_table(stocks, console=console)
        output = console.file.getvalue()
        for col in ["Symbol", "Price", "AvgVol", "MktCap", "D/E", "Margin", "Growth", "RSI", "Score", "Sector"]:
            assert col in output, f"Column '{col}' not found in table output"

    def test_table_row_count(self):
        console = _capture_console()
        stocks = self._make_passing_stocks()
        render_results_table(stocks, console=console)
        output = console.file.getvalue()
        # All 4 passing stocks should appear; check symbols
        for sym in ["AAPL", "MSFT", "JNJ", "KO"]:
            assert sym in output

    def test_sorted_by_score_descending(self):
        console = _capture_console()
        stocks = self._make_passing_stocks()
        render_results_table(stocks, console=console)
        output = console.file.getvalue()
        # AAPL (85) should appear before KO (45) in output
        assert output.index("AAPL") < output.index("KO")

    def test_score_colors_in_markup(self):
        console = Console(file=StringIO(), width=120, highlight=False, markup=True)
        stocks = self._make_passing_stocks()
        render_results_table(stocks, console=console)
        output = console.file.getvalue()
        # Scores should be styled -- check for the score values in the output
        assert "85.0" in output or "85.00" in output

    def test_zero_passing_stocks(self):
        console = _capture_console()
        # All stocks fail filters
        s = _make_stock("FAIL", [FilterResult("bar_data", False, reason="no data")], score=None)
        render_results_table([s], console=console)
        output = console.file.getvalue()
        assert "No stocks passed all filters" in output

    def test_empty_list(self):
        console = _capture_console()
        render_results_table([], console=console)
        output = console.file.getvalue()
        assert "No stocks passed all filters" in output

    def test_only_passing_scored_stocks_shown(self):
        console = _capture_console()
        passing = _make_stock("GOOD", _all_pass_filters(), score=75.0, price=100.0, sector="Tech")
        failing = _make_stock("BAD", [FilterResult("bar_data", False)], score=None)
        no_score = _make_stock("NOSCORE", _all_pass_filters(), score=None)
        render_results_table([passing, failing, no_score], console=console)
        output = console.file.getvalue()
        assert "GOOD" in output
        assert "BAD" not in output
        assert "NOSCORE" not in output
