"""Tests for suggest_strategy_params tool handler."""

import datetime

import pandas as pd
import pytest

pytest.importorskip("pyarrow", reason="UI extras not installed")

from optopsy.ui.tools import execute_tool

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def option_data():
    """Option dataset with known DTE and OTM% distributions."""
    exp_date = datetime.datetime(2018, 1, 31)
    quote_dates = [datetime.datetime(2018, 1, 1), datetime.datetime(2018, 1, 31)]
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
        ["SPX", 213.93, "call", exp_date, quote_dates[0], 212.5, 7.35, 7.45],
        ["SPX", 213.93, "call", exp_date, quote_dates[0], 215.0, 6.00, 6.05],
        ["SPX", 213.93, "put", exp_date, quote_dates[0], 212.5, 5.70, 5.80],
        ["SPX", 213.93, "put", exp_date, quote_dates[0], 215.0, 7.10, 7.20],
        ["SPX", 220.0, "call", exp_date, quote_dates[1], 212.5, 7.45, 7.55],
        ["SPX", 220.0, "call", exp_date, quote_dates[1], 215.0, 4.96, 5.05],
        ["SPX", 220.0, "put", exp_date, quote_dates[1], 212.5, 0.0, 0.0],
        ["SPX", 220.0, "put", exp_date, quote_dates[1], 215.0, 0.0, 0.0],
    ]
    return pd.DataFrame(data=d, columns=cols)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSuggestStrategyParams:
    def test_basic_suggestions(self, option_data):
        """Returns DTE and OTM% distribution tables."""
        result = execute_tool("suggest_strategy_params", {}, option_data)
        assert "DTE" in result.llm_summary
        assert "OTM" in result.llm_summary
        assert "Recommended" in result.llm_summary
        assert "DTE Distribution" in result.user_display
        assert "OTM% Distribution" in result.user_display
        assert "json" in result.user_display

    def test_no_dataset(self):
        """Returns error when no dataset is loaded."""
        result = execute_tool("suggest_strategy_params", {}, None)
        assert "no dataset" in result.llm_summary.lower()

    def test_calendar_strategy(self, option_data):
        """Calendar strategy gets front/back DTE instead of max_entry_dte."""
        result = execute_tool(
            "suggest_strategy_params",
            {"strategy_name": "long_call_calendar"},
            option_data,
        )
        assert (
            "front_dte_min" in result.llm_summary
            or "front" in result.llm_summary.lower()
        )
        assert (
            "Calendar" in result.user_display
            or "calendar" in result.llm_summary.lower()
        )

    def test_iron_condor_capping(self, option_data):
        """Iron condor caps DTE at 45 and OTM at 0.3."""
        result = execute_tool(
            "suggest_strategy_params",
            {"strategy_name": "iron_condor"},
            option_data,
        )
        assert "Recommended" in result.llm_summary
        # The note about multi-leg strategies should be present
        assert (
            "Multi-leg" in result.user_display
            or "multi-leg" in result.llm_summary.lower()
        )

    def test_spread_capping(self, option_data):
        """Spread strategy caps OTM at 0.2."""
        result = execute_tool(
            "suggest_strategy_params",
            {"strategy_name": "long_call_spread"},
            option_data,
        )
        assert "Recommended" in result.llm_summary
        assert "Spread" in result.user_display or "spread" in result.llm_summary.lower()

    def test_unknown_strategy_rejected(self, option_data):
        """Unknown strategy name is rejected by Pydantic validation."""
        result = execute_tool(
            "suggest_strategy_params",
            {"strategy_name": "nonexistent_strategy"},
            option_data,
        )
        assert (
            "invalid" in result.llm_summary.lower()
            or "unknown" in result.llm_summary.lower()
        )

    def test_no_strategy_name(self, option_data):
        """Omitting strategy_name returns base recommendations."""
        result = execute_tool(
            "suggest_strategy_params",
            {},
            option_data,
        )
        assert "DTE" in result.llm_summary
        assert "Recommended" in result.llm_summary

    def test_display_has_percentile_tables(self, option_data):
        """User display includes percentile tables for DTE and OTM%."""
        result = execute_tool("suggest_strategy_params", {}, option_data)
        display = result.user_display
        assert "p10" in display
        assert "p25" in display
        assert "p50" in display
        assert "p75" in display
        assert "p90" in display
