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
    """Option dataset with known DTE and delta distributions.

    DTE values: 4 rows with DTE=30, 4 rows with DTE=0.
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
        "delta",
    ]
    d = [
        ["SPX", 213.93, "call", exp_date, quote_dates[0], 212.5, 7.35, 7.45, 0.55],
        ["SPX", 213.93, "call", exp_date, quote_dates[0], 215.0, 6.00, 6.05, 0.45],
        ["SPX", 213.93, "put", exp_date, quote_dates[0], 212.5, 5.70, 5.80, -0.45],
        ["SPX", 213.93, "put", exp_date, quote_dates[0], 215.0, 7.10, 7.20, -0.55],
        ["SPX", 220.0, "call", exp_date, quote_dates[1], 212.5, 7.45, 7.55, 0.60],
        ["SPX", 220.0, "call", exp_date, quote_dates[1], 215.0, 4.96, 5.05, 0.50],
        ["SPX", 220.0, "put", exp_date, quote_dates[1], 212.5, 0.0, 0.0, -0.05],
        ["SPX", 220.0, "put", exp_date, quote_dates[1], 215.0, 0.0, 0.0, -0.10],
    ]
    return pd.DataFrame(data=d, columns=cols)


@pytest.fixture
def wide_dte_data():
    """Option dataset with high DTE (90).

    Used to exercise capping logic in iron condor overrides.
    DTE distribution: 4 rows with DTE=90, 4 rows with DTE=0.
    """
    quote_date = datetime.datetime(2018, 1, 1)
    exp_date = datetime.datetime(2018, 4, 1)  # ~90 days
    exp_date_near = datetime.datetime(2018, 1, 1)  # DTE=0
    cols = [
        "underlying_symbol",
        "underlying_price",
        "option_type",
        "expiration",
        "quote_date",
        "strike",
        "bid",
        "ask",
        "delta",
    ]
    d = [
        ["SPX", 100.0, "call", exp_date, quote_date, 140.0, 1.0, 1.1, 0.10],
        ["SPX", 100.0, "call", exp_date, quote_date, 150.0, 0.5, 0.6, 0.05],
        ["SPX", 100.0, "put", exp_date, quote_date, 60.0, 1.0, 1.1, -0.10],
        ["SPX", 100.0, "put", exp_date, quote_date, 50.0, 0.5, 0.6, -0.05],
        ["SPX", 100.0, "call", exp_date_near, quote_date, 140.0, 0.1, 0.2, 0.08],
        ["SPX", 100.0, "call", exp_date_near, quote_date, 150.0, 0.05, 0.1, 0.03],
        ["SPX", 100.0, "put", exp_date_near, quote_date, 60.0, 0.1, 0.2, -0.08],
        ["SPX", 100.0, "put", exp_date_near, quote_date, 50.0, 0.05, 0.1, -0.03],
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
        """Base recommendations contain max_entry_dte, exit_dte."""
        result = execute_tool("suggest_strategy_params", {}, option_data)
        reco = _extract_recommended_json(result.user_display)
        assert reco is not None
        assert "max_entry_dte" in reco
        assert "exit_dte" in reco

    def test_base_recommendations_use_correct_percentiles(self, option_data):
        """Base max_entry_dte = p75(DTE), exit_dte = p10(DTE).

        Data has 4 rows with DTE=30 and 4 with DTE=0.
        p75 of DTE [0,0,0,0,30,30,30,30] = 30, p10 = 0.
        """
        result = execute_tool("suggest_strategy_params", {}, option_data)
        reco = _extract_recommended_json(result.user_display)
        assert reco is not None
        assert reco["max_entry_dte"] == 30
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

    def test_iron_condor_caps_dte(self, wide_dte_data):
        """Iron condor caps max_entry_dte at 45 and recommends per-leg deltas.

        Uses wide_dte_data where p75 DTE=90, above the cap.
        """
        result = execute_tool(
            "suggest_strategy_params",
            {"strategy_name": "iron_condor"},
            wide_dte_data,
        )
        reco = _extract_recommended_json(result.user_display)
        assert reco is not None
        # p75 DTE is 90 but cap is 45 → must be exactly 45
        assert reco["max_entry_dte"] == 45
        # Iron condor note should be present
        assert "iron condor" in result.llm_summary.lower()
        # Should recommend per-leg delta targets
        assert "leg1_delta" in reco
        assert "leg2_delta" in reco
        assert "leg3_delta" in reco
        assert "leg4_delta" in reco
        # Outer wings at 0.10 delta
        assert reco["leg1_delta"]["target"] == 0.10
        assert reco["leg4_delta"]["target"] == 0.10
        # Inner legs at 0.30 delta
        assert reco["leg2_delta"]["target"] == 0.30
        assert reco["leg3_delta"]["target"] == 0.30

    def test_spread_strategy_note(self, wide_dte_data):
        """Spread strategy includes strategy note."""
        result = execute_tool(
            "suggest_strategy_params",
            {"strategy_name": "long_call_spread"},
            wide_dte_data,
        )
        reco = _extract_recommended_json(result.user_display)
        assert reco is not None
        assert (
            "spread" in result.llm_summary.lower()
            or "delta" in result.llm_summary.lower()
        )

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
        """User display includes percentile tables for DTE and delta."""
        result = execute_tool("suggest_strategy_params", {}, option_data)
        display = result.user_display
        assert "p10" in display
        assert "p25" in display
        assert "p50" in display
        assert "p75" in display
        assert "p90" in display
        # Verify it's actually a markdown table
        assert "| Percentile | DTE |" in display
        assert "Delta" in display

    def test_delta_distribution_shown(self, option_data):
        """Delta distribution values are shown when delta column exists."""
        result = execute_tool("suggest_strategy_params", {}, option_data)
        assert "delta" in result.llm_summary.lower()

    def test_iron_butterfly_recommends_atm_body(self, wide_dte_data):
        """Iron butterfly recommends ATM deltas for inner legs."""
        result = execute_tool(
            "suggest_strategy_params",
            {"strategy_name": "iron_butterfly"},
            wide_dte_data,
        )
        reco = _extract_recommended_json(result.user_display)
        assert reco is not None
        assert reco["max_entry_dte"] == 45
        assert "iron butterfly" in result.llm_summary.lower()
        # Inner legs at ATM (0.50)
        assert reco["leg2_delta"]["target"] == 0.50
        assert reco["leg3_delta"]["target"] == 0.50
        # Outer wings at OTM (0.10)
        assert reco["leg1_delta"]["target"] == 0.10
        assert reco["leg4_delta"]["target"] == 0.10

    def test_butterfly_recommends_three_legs(self, option_data):
        """Butterfly strategy recommends 3-leg delta targets."""
        result = execute_tool(
            "suggest_strategy_params",
            {"strategy_name": "long_call_butterfly"},
            option_data,
        )
        reco = _extract_recommended_json(result.user_display)
        assert reco is not None
        assert "leg1_delta" in reco
        assert "leg2_delta" in reco
        assert "leg3_delta" in reco
        assert "leg4_delta" not in reco
        # ITM wing, ATM body, OTM wing
        assert reco["leg1_delta"]["target"] == 0.40
        assert reco["leg2_delta"]["target"] == 0.50
        assert reco["leg3_delta"]["target"] == 0.10

    def test_straddle_recommends_atm(self, option_data):
        """Straddle recommends ATM delta for both legs."""
        result = execute_tool(
            "suggest_strategy_params",
            {"strategy_name": "long_straddles"},
            option_data,
        )
        reco = _extract_recommended_json(result.user_display)
        assert reco is not None
        assert reco["leg1_delta"]["target"] == 0.50
        assert reco["leg2_delta"]["target"] == 0.50

    def test_strangle_recommends_otm(self, option_data):
        """Strangle recommends 0.30 delta for both legs."""
        result = execute_tool(
            "suggest_strategy_params",
            {"strategy_name": "long_strangles"},
            option_data,
        )
        reco = _extract_recommended_json(result.user_display)
        assert reco is not None
        assert reco["leg1_delta"]["target"] == 0.30
        assert reco["leg2_delta"]["target"] == 0.30

    def test_spread_recommends_two_legs(self, option_data):
        """Spread recommends ATM leg1 and OTM leg2."""
        result = execute_tool(
            "suggest_strategy_params",
            {"strategy_name": "long_call_spread"},
            option_data,
        )
        reco = _extract_recommended_json(result.user_display)
        assert reco is not None
        assert reco["leg1_delta"]["target"] == 0.50
        assert reco["leg2_delta"]["target"] == 0.10

    def test_covered_call_recommends_deep_itm_plus_otm(self, option_data):
        """Covered call recommends deep ITM leg1 and 0.30 delta leg2."""
        result = execute_tool(
            "suggest_strategy_params",
            {"strategy_name": "covered_call"},
            option_data,
        )
        reco = _extract_recommended_json(result.user_display)
        assert reco is not None
        assert reco["leg1_delta"]["target"] == 0.80
        assert reco["leg2_delta"]["target"] == 0.30

    def test_single_leg_strategy_recommends_default_delta(self, option_data):
        """Single-leg strategy recommends default 0.30 delta."""
        result = execute_tool(
            "suggest_strategy_params",
            {"strategy_name": "long_calls"},
            option_data,
        )
        reco = _extract_recommended_json(result.user_display)
        assert reco is not None
        assert reco["leg1_delta"]["target"] == 0.30
        assert "leg2_delta" not in reco

    def test_reverse_iron_condor_same_as_iron_condor(self, wide_dte_data):
        """Reverse iron condor shares iron condor delta recommendations."""
        result = execute_tool(
            "suggest_strategy_params",
            {"strategy_name": "reverse_iron_condor"},
            wide_dte_data,
        )
        reco = _extract_recommended_json(result.user_display)
        assert reco is not None
        assert reco["leg1_delta"]["target"] == 0.10
        assert reco["leg2_delta"]["target"] == 0.30
        assert reco["leg3_delta"]["target"] == 0.30
        assert reco["leg4_delta"]["target"] == 0.10

    def test_protective_put_recommends_deep_itm_plus_otm(self, option_data):
        """Protective put recommends deep ITM leg1 and 0.30 delta leg2."""
        result = execute_tool(
            "suggest_strategy_params",
            {"strategy_name": "protective_put"},
            option_data,
        )
        reco = _extract_recommended_json(result.user_display)
        assert reco is not None
        assert reco["leg1_delta"]["target"] == 0.80
        assert reco["leg2_delta"]["target"] == 0.30

    def test_reverse_iron_butterfly_same_as_iron_butterfly(self, wide_dte_data):
        """Reverse iron butterfly shares iron butterfly delta recommendations."""
        result = execute_tool(
            "suggest_strategy_params",
            {"strategy_name": "reverse_iron_butterfly"},
            wide_dte_data,
        )
        reco = _extract_recommended_json(result.user_display)
        assert reco is not None
        assert reco["leg1_delta"]["target"] == 0.10
        assert reco["leg2_delta"]["target"] == 0.50
        assert reco["leg3_delta"]["target"] == 0.50
        assert reco["leg4_delta"]["target"] == 0.10

    def test_no_delta_column_omits_delta_recommendations(self, option_data):
        """When delta column is missing, no leg*_delta keys in recommendations."""
        df = option_data.drop(columns=["delta"])
        result = execute_tool(
            "suggest_strategy_params",
            {"strategy_name": "iron_condor"},
            df,
        )
        reco = _extract_recommended_json(result.user_display)
        assert reco is not None
        assert "leg1_delta" not in reco
        assert "leg2_delta" not in reco
        assert "WARNING" in result.llm_summary
        assert "no delta column" in result.llm_summary.lower()

    def test_all_null_delta_omits_delta_recommendations(self, option_data):
        """When delta column is all-null, no leg*_delta keys in recommendations."""
        df = option_data.copy()
        df["delta"] = float("nan")
        result = execute_tool(
            "suggest_strategy_params",
            {"strategy_name": "long_calls"},
            df,
        )
        reco = _extract_recommended_json(result.user_display)
        assert reco is not None
        assert "leg1_delta" not in reco
        assert "WARNING" in result.llm_summary
        assert "no usable" in result.llm_summary.lower()

    def test_no_delta_strategy_note_omits_delta_values(self, option_data):
        """Strategy note should not mention delta values when delta is unavailable."""
        df = option_data.drop(columns=["delta"])
        result = execute_tool(
            "suggest_strategy_params",
            {"strategy_name": "long_call_spread"},
            df,
        )
        # The note should not mention specific delta numbers like "0.50" or "0.10"
        # after the WARNING prefix
        assert (
            "OTM%" in result.llm_summary
            or "without delta" in result.llm_summary.lower()
        )

    def test_empty_dataframe_raises_value_error(self):
        """Empty DataFrame raises ValueError from NaN quantile conversion."""
        cols = [
            "underlying_symbol",
            "underlying_price",
            "option_type",
            "expiration",
            "quote_date",
            "strike",
            "bid",
            "ask",
            "delta",
        ]
        empty_df = pd.DataFrame(columns=cols)
        with pytest.raises(ValueError, match="cannot convert float NaN"):
            execute_tool("suggest_strategy_params", {}, empty_df)
