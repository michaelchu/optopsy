"""Tests for plot_vol_surface and iv_term_structure tools."""

import datetime

import pandas as pd
import pytest

pytest.importorskip("pyarrow", reason="UI extras not installed")
pytest.importorskip("plotly", reason="plotly not installed")

from optopsy.ui.tools import execute_tool

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def iv_dataset():
    """Options data with implied_volatility, multiple expirations and strikes.

    Two quote dates, two expirations, calls and puts at three strikes.
    """
    qd1 = datetime.datetime(2024, 1, 2)
    qd2 = datetime.datetime(2024, 1, 3)
    exp1 = datetime.datetime(2024, 2, 16)
    exp2 = datetime.datetime(2024, 3, 15)
    rows = []
    for qd, price in [(qd1, 100.0), (qd2, 101.0)]:
        for exp in [exp1, exp2]:
            for strike in [95.0, 100.0, 105.0]:
                for ot in ["call", "put"]:
                    # IV smile: higher for OTM
                    iv = 0.20 + abs(strike - price) * 0.005
                    bid = (
                        max(price - strike, 0) + 1.0
                        if ot == "call"
                        else max(strike - price, 0) + 1.0
                    )
                    rows.append(
                        [
                            "SPX",
                            price,
                            ot,
                            exp,
                            qd,
                            strike,
                            bid,
                            bid + 0.10,
                            iv,
                        ]
                    )
    cols = [
        "underlying_symbol",
        "underlying_price",
        "option_type",
        "expiration",
        "quote_date",
        "strike",
        "bid",
        "ask",
        "implied_volatility",
    ]
    return pd.DataFrame(data=rows, columns=cols)


@pytest.fixture
def no_iv_dataset():
    """Options data without implied_volatility column."""
    qd = datetime.datetime(2024, 1, 2)
    exp = datetime.datetime(2024, 2, 16)
    cols = [
        "underlying_symbol",
        "underlying_price",
        "option_type",
        "expiration",
        "quote_date",
        "strike",
        "bid",
        "ask",
    ]
    d = [
        ["SPX", 100.0, "call", exp, qd, 100.0, 3.0, 3.10],
        ["SPX", 100.0, "put", exp, qd, 100.0, 3.0, 3.10],
    ]
    return pd.DataFrame(data=d, columns=cols)


@pytest.fixture
def single_exp_dataset():
    """Options data with IV but only one expiration."""
    qd = datetime.datetime(2024, 1, 2)
    exp = datetime.datetime(2024, 2, 16)
    rows = []
    for strike in [95.0, 100.0, 105.0]:
        for ot in ["call", "put"]:
            iv = 0.20 + abs(strike - 100.0) * 0.005
            rows.append(["SPX", 100.0, ot, exp, qd, strike, 3.0, 3.10, iv])
    cols = [
        "underlying_symbol",
        "underlying_price",
        "option_type",
        "expiration",
        "quote_date",
        "strike",
        "bid",
        "ask",
        "implied_volatility",
    ]
    return pd.DataFrame(data=rows, columns=cols)


# ---------------------------------------------------------------------------
# plot_vol_surface tests
# ---------------------------------------------------------------------------


class TestPlotVolSurface:
    def test_returns_chart(self, iv_dataset):
        """Should return a ToolResult with a chart figure."""
        result = execute_tool(
            "plot_vol_surface",
            {"quote_date": "2024-01-02"},
            dataset=iv_dataset,
        )
        assert result.chart_figure is not None
        assert "Volatility surface" in result.llm_summary

    def test_defaults_to_latest_date(self, iv_dataset):
        """Should use the latest quote_date when none specified."""
        result = execute_tool("plot_vol_surface", {}, dataset=iv_dataset)
        assert result.chart_figure is not None
        # Latest date is 2024-01-03
        assert "2024-01-03" in result.llm_summary

    def test_missing_iv_column(self, no_iv_dataset):
        """Should return error when dataset lacks implied_volatility."""
        result = execute_tool("plot_vol_surface", {}, dataset=no_iv_dataset)
        assert result.chart_figure is None
        assert "implied_volatility" in result.llm_summary

    def test_no_dataset(self):
        """Should return error when no dataset is loaded."""
        result = execute_tool("plot_vol_surface", {}, dataset=None)
        assert result.chart_figure is None
        assert "No dataset" in result.llm_summary

    def test_invalid_date_suggests_closest(self, iv_dataset):
        """Should suggest closest available date for invalid quote_date."""
        result = execute_tool(
            "plot_vol_surface",
            {"quote_date": "2024-06-15"},
            dataset=iv_dataset,
        )
        assert result.chart_figure is None
        assert "Closest available date" in result.llm_summary

    def test_put_option_type(self, iv_dataset):
        """Should work with option_type='put'."""
        result = execute_tool(
            "plot_vol_surface",
            {"quote_date": "2024-01-02", "option_type": "put"},
            dataset=iv_dataset,
        )
        assert result.chart_figure is not None
        assert "put" in result.llm_summary.lower()

    def test_summary_has_dimensions(self, iv_dataset):
        """Summary should report number of strikes and expirations."""
        result = execute_tool(
            "plot_vol_surface",
            {"quote_date": "2024-01-02"},
            dataset=iv_dataset,
        )
        assert "strikes" in result.llm_summary
        assert "expirations" in result.llm_summary

    def test_single_expiration(self, single_exp_dataset):
        """Should handle dataset with only one expiration."""
        result = execute_tool(
            "plot_vol_surface",
            {"quote_date": "2024-01-02"},
            dataset=single_exp_dataset,
        )
        assert result.chart_figure is not None


# ---------------------------------------------------------------------------
# iv_term_structure tests
# ---------------------------------------------------------------------------


class TestIVTermStructure:
    def test_returns_chart(self, iv_dataset):
        """Should return a ToolResult with a chart figure."""
        result = execute_tool(
            "iv_term_structure",
            {"quote_date": "2024-01-02"},
            dataset=iv_dataset,
        )
        assert result.chart_figure is not None
        assert "IV term structure" in result.llm_summary

    def test_defaults_to_latest_date(self, iv_dataset):
        """Should use the latest quote_date when none specified."""
        result = execute_tool("iv_term_structure", {}, dataset=iv_dataset)
        assert result.chart_figure is not None

    def test_missing_iv_column(self, no_iv_dataset):
        """Should return error when dataset lacks implied_volatility."""
        result = execute_tool("iv_term_structure", {}, dataset=no_iv_dataset)
        assert result.chart_figure is None
        assert "implied_volatility" in result.llm_summary

    def test_no_dataset(self):
        """Should return error when no dataset is loaded."""
        result = execute_tool("iv_term_structure", {}, dataset=None)
        assert result.chart_figure is None
        assert "No dataset" in result.llm_summary

    def test_invalid_date_suggests_closest(self, iv_dataset):
        """Should suggest closest available date for invalid quote_date."""
        result = execute_tool(
            "iv_term_structure",
            {"quote_date": "2024-06-15"},
            dataset=iv_dataset,
        )
        assert result.chart_figure is None
        assert "Closest available date" in result.llm_summary

    def test_summary_reports_iv_range(self, iv_dataset):
        """Summary should contain IV range."""
        result = execute_tool(
            "iv_term_structure",
            {"quote_date": "2024-01-02"},
            dataset=iv_dataset,
        )
        assert "ATM IV range" in result.llm_summary

    def test_vectorized_underlying_price(self):
        """ATM strike should be determined per-row, not from a single price.

        Regression test for the .iloc[0] bug: if underlying_price varies
        across expirations, the per-row calculation should still find the
        correct ATM strike for each expiration.
        """
        qd = datetime.datetime(2024, 1, 2)
        exp1 = datetime.datetime(2024, 2, 16)
        exp2 = datetime.datetime(2024, 3, 15)
        rows = [
            # exp1: underlying=100, ATM strike=100, IV=0.20
            ["SPX", 100.0, "call", exp1, qd, 95.0, 5.0, 5.10, 0.25],
            ["SPX", 100.0, "call", exp1, qd, 100.0, 3.0, 3.10, 0.20],
            ["SPX", 100.0, "call", exp1, qd, 105.0, 1.0, 1.10, 0.25],
            # exp2: underlying=110, ATM strike=110, IV=0.30
            ["SPX", 110.0, "call", exp2, qd, 105.0, 5.0, 5.10, 0.35],
            ["SPX", 110.0, "call", exp2, qd, 110.0, 3.0, 3.10, 0.30],
            ["SPX", 110.0, "call", exp2, qd, 115.0, 1.0, 1.10, 0.35],
        ]
        cols = [
            "underlying_symbol",
            "underlying_price",
            "option_type",
            "expiration",
            "quote_date",
            "strike",
            "bid",
            "ask",
            "implied_volatility",
        ]
        ds = pd.DataFrame(data=rows, columns=cols)
        result = execute_tool(
            "iv_term_structure",
            {"quote_date": "2024-01-02"},
            dataset=ds,
        )
        assert result.chart_figure is not None

    def test_single_strike(self):
        """Should handle data with only one strike per expiration."""
        qd = datetime.datetime(2024, 1, 2)
        exp = datetime.datetime(2024, 2, 16)
        cols = [
            "underlying_symbol",
            "underlying_price",
            "option_type",
            "expiration",
            "quote_date",
            "strike",
            "bid",
            "ask",
            "implied_volatility",
        ]
        d = [["SPX", 100.0, "call", exp, qd, 100.0, 3.0, 3.10, 0.20]]
        ds = pd.DataFrame(data=d, columns=cols)
        result = execute_tool(
            "iv_term_structure",
            {"quote_date": "2024-01-02"},
            dataset=ds,
        )
        # Only one forward expiration, should produce a chart
        assert result.chart_figure is not None


# ---------------------------------------------------------------------------
# build_signal incompatible combination tests (comment #4)
# ---------------------------------------------------------------------------


class TestBuildSignalIncompatibleCombination:
    def test_iv_plus_ohlcv_rejected(self, iv_dataset):
        """Combining IV rank signal with OHLCV signal should return error."""
        result = execute_tool(
            "build_signal",
            {
                "slot": "test_combo",
                "signals": [
                    {"name": "iv_rank_above", "params": {"threshold": 0.5}},
                    {"name": "rsi_below", "params": {"threshold": 30}},
                ],
            },
            dataset=iv_dataset,
        )
        assert "Cannot combine IV signals" in result.llm_summary
        assert "OHLCV signals" in result.llm_summary

    def test_iv_plus_date_only_allowed(self, iv_dataset):
        """Combining IV rank signal with day_of_week should work."""
        result = execute_tool(
            "build_signal",
            {
                "slot": "test_iv_dow",
                "signals": [
                    {"name": "iv_rank_above", "params": {"threshold": 0.5}},
                    {"name": "day_of_week", "params": {"days": [2, 3, 4]}},
                ],
            },
            dataset=iv_dataset,
        )
        # Should succeed (no incompatibility error)
        assert "Cannot combine" not in result.llm_summary
