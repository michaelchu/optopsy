"""Tests for the check_data_quality tool."""

import datetime

import pandas as pd
import pytest

pytest.importorskip("pyarrow", reason="UI extras not installed")

from optopsy.ui.tools import execute_tool

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def clean_data():
    """Minimal clean option dataset — all 7 required columns, no issues."""
    exp = datetime.datetime(2024, 3, 15)
    dates = pd.to_datetime(
        ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08"]
    )
    rows = []
    for qd in dates:
        rows.extend(
            [
                ["SPY", 480.0, "call", exp, qd, 480.0, 5.0, 5.10],
                ["SPY", 480.0, "put", exp, qd, 480.0, 4.8, 4.90],
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
    ]
    return pd.DataFrame(rows, columns=cols)


@pytest.fixture
def data_with_optionals(clean_data):
    """Clean data plus optional columns (delta, volume, implied_volatility)."""
    df = clean_data.copy()
    df["delta"] = 0.5
    df["gamma"] = 0.02
    df["volume"] = 100
    df["open_interest"] = 5000
    df["implied_volatility"] = 0.20
    return df


# ---------------------------------------------------------------------------
# Tests — basic operation
# ---------------------------------------------------------------------------


class TestCheckDataQualityBasic:
    def test_no_dataset_loaded(self):
        result = execute_tool("check_data_quality", {}, None)
        assert (
            "no dataset" in result.llm_summary.lower()
            or "load" in result.llm_summary.lower()
        )

    def test_clean_data_pass(self, clean_data):
        result = execute_tool("check_data_quality", {}, clean_data)
        assert "PASS" in result.llm_summary
        assert "all 7 required columns" in result.llm_summary
        assert result.user_display is not None

    def test_named_dataset(self, clean_data):
        datasets = {"SPY": clean_data}
        result = execute_tool(
            "check_data_quality",
            {"dataset_name": "SPY"},
            None,
            datasets=datasets,
        )
        assert "SPY" in result.llm_summary
        assert "PASS" in result.llm_summary


# ---------------------------------------------------------------------------
# Tests — required columns
# ---------------------------------------------------------------------------


class TestRequiredColumns:
    def test_missing_required_column(self, clean_data):
        df = clean_data.drop(columns=["bid"])
        result = execute_tool("check_data_quality", {}, df)
        assert "FAIL" in result.llm_summary
        assert "bid" in result.llm_summary

    def test_missing_multiple_columns(self, clean_data):
        df = clean_data.drop(columns=["bid", "ask", "strike"])
        result = execute_tool("check_data_quality", {}, df)
        assert "FAIL" in result.llm_summary
        assert "bid" in result.llm_summary
        assert "ask" in result.llm_summary
        assert "strike" in result.llm_summary

    def test_underlying_price_not_required(self, clean_data):
        """underlying_price is NOT a required column for check_data_quality."""
        df = clean_data.drop(columns=["underlying_price"])
        result = execute_tool("check_data_quality", {}, df)
        assert "FAIL" not in result.llm_summary
        assert "PASS" in result.llm_summary


# ---------------------------------------------------------------------------
# Tests — optional columns
# ---------------------------------------------------------------------------


class TestOptionalColumns:
    def test_optional_columns_detected(self, data_with_optionals):
        result = execute_tool("check_data_quality", {}, data_with_optionals)
        assert "delta" in result.llm_summary
        assert "implied_volatility" in result.llm_summary
        assert "volume" in result.llm_summary

    def test_delta_filtering_noted(self, data_with_optionals):
        result = execute_tool("check_data_quality", {}, data_with_optionals)
        assert "delta filtering" in result.llm_summary.lower()

    def test_no_optional_columns(self):
        """Dataset with only required columns (no optionals)."""
        df = pd.DataFrame(
            {
                "underlying_symbol": ["SPY"],
                "option_type": ["call"],
                "expiration": pd.to_datetime(["2024-03-15"]),
                "quote_date": pd.to_datetime(["2024-01-02"]),
                "strike": [480.0],
                "bid": [5.0],
                "ask": [5.10],
            }
        )
        result = execute_tool("check_data_quality", {}, df)
        assert "no optional columns" in result.llm_summary.lower()


# ---------------------------------------------------------------------------
# Tests — null analysis
# ---------------------------------------------------------------------------


class TestNullAnalysis:
    def test_null_volume(self, clean_data):
        df = clean_data.copy()
        df["volume"] = float("nan")
        result = execute_tool("check_data_quality", {}, df)
        assert "volume" in result.llm_summary
        assert "100.0% null" in result.llm_summary

    def test_partial_null_bid(self, clean_data):
        df = clean_data.copy()
        df.loc[0, "bid"] = float("nan")
        result = execute_tool("check_data_quality", {}, df)
        assert "bid" in result.llm_summary
        assert "null" in result.llm_summary.lower()

    def test_no_nulls(self, clean_data):
        result = execute_tool("check_data_quality", {}, clean_data)
        # Should not have WARN about nulls for bid/ask (no volume column)
        lines = result.llm_summary.split("\n")
        null_warns = [ln for ln in lines if "null" in ln.lower() and "WARN" in ln]
        assert len(null_warns) == 0


# ---------------------------------------------------------------------------
# Tests — bid/ask quality
# ---------------------------------------------------------------------------


class TestBidAskQuality:
    def test_zero_bid_detected(self, clean_data):
        df = clean_data.copy()
        df.loc[0, "bid"] = 0.0
        result = execute_tool("check_data_quality", {}, df)
        assert "zero-bid" in result.llm_summary.lower()

    def test_crossed_market_detected(self, clean_data):
        df = clean_data.copy()
        df.loc[0, "bid"] = 10.0
        df.loc[0, "ask"] = 5.0
        result = execute_tool("check_data_quality", {}, df)
        assert "crossed" in result.llm_summary.lower()

    def test_clean_bid_ask(self, clean_data):
        result = execute_tool("check_data_quality", {}, clean_data)
        assert "no zero-bid or crossed-market" in result.llm_summary.lower()


# ---------------------------------------------------------------------------
# Tests — date coverage
# ---------------------------------------------------------------------------


class TestDateCoverage:
    def test_date_range_reported(self, clean_data):
        result = execute_tool("check_data_quality", {}, clean_data)
        assert "2024-01-02" in result.llm_summary
        assert "2024-01-08" in result.llm_summary

    def test_gap_detected(self):
        """A gap > 4 calendar days should be reported."""
        dates = pd.to_datetime(["2024-01-02", "2024-01-10"])
        exp = datetime.datetime(2024, 3, 15)
        df = pd.DataFrame(
            {
                "underlying_symbol": ["SPY", "SPY"],
                "option_type": ["call", "call"],
                "expiration": [exp, exp],
                "quote_date": dates,
                "strike": [480.0, 480.0],
                "bid": [5.0, 5.0],
                "ask": [5.10, 5.10],
            }
        )
        result = execute_tool("check_data_quality", {}, df)
        assert "gap" in result.llm_summary.lower()


# ---------------------------------------------------------------------------
# Tests — recommendations
# ---------------------------------------------------------------------------


class TestRecommendations:
    def test_volume_null_recommends_mid(self, clean_data):
        df = clean_data.copy()
        df["volume"] = float("nan")
        # More than 10% null => recommend mid
        result = execute_tool("check_data_quality", {}, df)
        assert "slippage='mid'" in result.llm_summary

    def test_volume_present_recommends_liquidity(self, data_with_optionals):
        result = execute_tool("check_data_quality", {}, data_with_optionals)
        assert "liquidity" in result.llm_summary.lower()

    def test_no_volume_column(self, clean_data):
        result = execute_tool("check_data_quality", {}, clean_data)
        assert "no volume column" in result.llm_summary.lower()


# ---------------------------------------------------------------------------
# Tests — user display
# ---------------------------------------------------------------------------


class TestUserDisplay:
    def test_user_display_has_markdown_headers(self, data_with_optionals):
        result = execute_tool("check_data_quality", {}, data_with_optionals)
        assert "### Data Quality" in result.user_display
        assert "**Required Columns**" in result.user_display
        assert "**Optional Columns**" in result.user_display

    def test_user_display_has_tables(self, data_with_optionals):
        result = execute_tool("check_data_quality", {}, data_with_optionals)
        # Bid/ask quality section should have a table
        assert "Spread mean" in result.user_display
