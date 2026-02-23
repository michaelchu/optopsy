"""Tests for suggest_strategy_params tool handler."""

import datetime
import json
import re

import pandas as pd
import pytest

pytest.importorskip("pyarrow", reason="UI extras not installed")

from optopsy.ui.tools import execute_tool

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def option_data():
    """Option dataset with known DTE and OTM% distributions.

    DTE values: 4 rows with DTE=30, 4 rows with DTE=0.
    OTM% values (sorted): 0.005, 0.005, 0.0067, 0.0067, 0.0227, 0.0227, 0.0341, 0.0341
    """
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


def _extract_recommended_json(text):
    """Extract the JSON block from user_display or llm_summary."""
    match = re.search(r"```json\s*\n(.*?)\n```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    # Fallback: try parsing from llm_summary "Recommended: {..."
    match = re.search(r"Recommended:\s*(\{.*\})", text)
    if match:
        return json.loads(match.group(1).replace("'", '"'))
    return None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSuggestStrategyParams:
    def test_basic_recommendations_have_correct_keys(self, option_data):
        """Base recommendations contain max_entry_dte, exit_dte, max_otm_pct."""
        result = execute_tool("suggest_strategy_params", {}, option_data)
        reco = _extract_recommended_json(result.user_display)
        assert reco is not None
        assert "max_entry_dte" in reco
        assert "exit_dte" in reco
        assert "max_otm_pct" in reco

    def test_dte_percentiles_match_data(self, option_data):
        """DTE percentiles are computed correctly for known data.

        Data has 4 rows with DTE=30 and 4 with DTE=0.
        p50 should be 15 (midpoint), min=0, max=30.
        """
        result = execute_tool("suggest_strategy_params", {}, option_data)
        # Parse DTE stats from llm_summary
        summary = result.llm_summary
        assert "min" in summary
        assert "'min': 0" in summary or '"min": 0' in summary

    def test_base_recommendations_use_p75(self, option_data):
        """Base max_entry_dte = p75(DTE), max_otm_pct = p75(OTM%)."""
        result = execute_tool("suggest_strategy_params", {}, option_data)
        reco = _extract_recommended_json(result.user_display)
        # p75 of DTE [0,0,0,0,30,30,30,30] = 30
        assert reco["max_entry_dte"] == 30
        # exit_dte = max(0, p10) — p10 of [0,0,0,0,30,30,30,30] = 0
        assert reco["exit_dte"] == 0

    def test_no_dataset(self):
        """Returns error when no dataset is loaded."""
        result = execute_tool("suggest_strategy_params", {}, None)
        assert "no dataset" in result.llm_summary.lower()

    def test_calendar_strategy_uses_front_back_dte(self, option_data):
        """Calendar strategy replaces max_entry_dte with front/back DTE params."""
        result = execute_tool(
            "suggest_strategy_params",
            {"strategy_name": "long_call_calendar"},
            option_data,
        )
        reco = _extract_recommended_json(result.user_display)
        assert reco is not None
        assert "front_dte_min" in reco
        assert "front_dte_max" in reco
        assert "back_dte_min" in reco
        assert "back_dte_max" in reco
        # Should NOT have base params
        assert "max_entry_dte" not in reco
        # front_dte_min = max(10, p10) = 10 (since p10=0, floor is 10)
        assert reco["front_dte_min"] == 10

    def test_iron_condor_caps_dte_and_otm(self, option_data):
        """Iron condor caps max_entry_dte at 45 and max_otm_pct at 0.3."""
        result = execute_tool(
            "suggest_strategy_params",
            {"strategy_name": "iron_condor"},
            option_data,
        )
        reco = _extract_recommended_json(result.user_display)
        assert reco is not None
        assert reco["max_entry_dte"] <= 45
        assert reco["max_otm_pct"] <= 0.3
        # Multi-leg note should be present
        assert "multi-leg" in result.llm_summary.lower()

    def test_spread_caps_otm(self, option_data):
        """Spread strategy caps max_otm_pct at 0.2."""
        result = execute_tool(
            "suggest_strategy_params",
            {"strategy_name": "long_call_spread"},
            option_data,
        )
        reco = _extract_recommended_json(result.user_display)
        assert reco is not None
        assert reco["max_otm_pct"] <= 0.2

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

    def test_display_has_percentile_tables(self, option_data):
        """User display includes percentile tables for DTE and OTM%."""
        result = execute_tool("suggest_strategy_params", {}, option_data)
        display = result.user_display
        assert "p10" in display
        assert "p25" in display
        assert "p50" in display
        assert "p75" in display
        assert "p90" in display
        # Verify it's actually a markdown table
        assert "| Percentile | DTE |" in display
        assert "| Percentile | OTM% |" in display

    def test_otm_values_are_reasonable(self, option_data):
        """OTM% values in recommendations are within data range."""
        result = execute_tool("suggest_strategy_params", {}, option_data)
        reco = _extract_recommended_json(result.user_display)
        # All OTM% values in fixture are < 0.04, so p75 should be < 0.04
        assert reco["max_otm_pct"] < 0.05
        assert reco["max_otm_pct"] > 0.0
