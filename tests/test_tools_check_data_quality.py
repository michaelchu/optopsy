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
    """Minimal clean option dataset — all 8 required columns, no issues."""
    exp = datetime.datetime(2024, 3, 15)
    dates = pd.to_datetime(
        ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08"]
    )
    rows = []
    for qd in dates:
        rows.extend(
            [
                ["SPY", 480.0, "call", exp, qd, 480.0, 5.0, 5.10, 0.50],
                ["SPY", 480.0, "put", exp, qd, 480.0, 4.8, 4.90, -0.50],
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
        "delta",
    ]
    return pd.DataFrame(rows, columns=cols)


@pytest.fixture
def data_with_optionals(clean_data):
    """Clean data plus optional columns (volume, implied_volatility, etc.)."""
    df = clean_data.copy()
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
        assert "all 8 required columns" in result.llm_summary
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


# ---------------------------------------------------------------------------
# Tests — optional columns
# ---------------------------------------------------------------------------


class TestOptionalColumns:
    def test_optional_columns_detected(self, data_with_optionals):
        result = execute_tool("check_data_quality", {}, data_with_optionals)
        assert "implied_volatility" in result.llm_summary
        assert "volume" in result.llm_summary

    def test_delta_is_required(self, data_with_optionals):
        result = execute_tool("check_data_quality", {}, data_with_optionals)
        assert "all 8 required columns" in result.llm_summary

    def test_no_optional_columns(self):
        """Dataset with only required columns (no optionals)."""
        df = pd.DataFrame(
            {
                "underlying_symbol": ["SPY"],
                "underlying_price": [480.0],
                "option_type": ["call"],
                "expiration": pd.to_datetime(["2024-03-15"]),
                "quote_date": pd.to_datetime(["2024-01-02"]),
                "strike": [480.0],
                "bid": [5.0],
                "ask": [5.10],
                "delta": [0.50],
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


# ---------------------------------------------------------------------------
# Tests — duplicate rows
# ---------------------------------------------------------------------------


class TestDuplicateRows:
    def test_duplicates_detected(self, clean_data):
        """Duplicate (quote_date, expiration, strike, option_type) rows flagged."""
        df = pd.concat([clean_data, clean_data.iloc[:2]], ignore_index=True)
        result = execute_tool("check_data_quality", {}, df)
        assert "duplicate" in result.llm_summary.lower()
        assert "WARN" in result.llm_summary

    def test_no_duplicates(self, clean_data):
        result = execute_tool("check_data_quality", {}, clean_data)
        assert "no duplicate rows" in result.llm_summary.lower()


# ---------------------------------------------------------------------------
# Tests — negative values
# ---------------------------------------------------------------------------


class TestNegativeValues:
    def test_negative_bid(self, clean_data):
        df = clean_data.copy()
        df.loc[0, "bid"] = -1.0
        result = execute_tool("check_data_quality", {}, df)
        assert "negative" in result.llm_summary.lower()
        assert "bid" in result.llm_summary

    def test_negative_strike(self, clean_data):
        df = clean_data.copy()
        df.loc[0, "strike"] = -100.0
        result = execute_tool("check_data_quality", {}, df)
        assert "negative" in result.llm_summary.lower()
        assert "strike" in result.llm_summary

    def test_no_negatives(self, clean_data):
        result = execute_tool("check_data_quality", {}, clean_data)
        assert "no negative" in result.llm_summary.lower()


# ---------------------------------------------------------------------------
# Tests — option type balance
# ---------------------------------------------------------------------------


class TestOptionTypeBalance:
    def test_iron_condor_calls_only(self, clean_data):
        """iron_condor needs both calls and puts; calls-only should fail."""
        df = clean_data[clean_data["option_type"] == "call"].copy()
        result = execute_tool(
            "check_data_quality",
            {"strategy_name": "iron_condor"},
            df,
        )
        assert "FAIL" in result.llm_summary
        assert "put" in result.llm_summary.lower()

    def test_iron_condor_both_types(self, clean_data):
        """iron_condor with both types should pass."""
        result = execute_tool(
            "check_data_quality",
            {"strategy_name": "iron_condor"},
            clean_data,
        )
        assert (
            "both calls" in result.llm_summary.lower() or "PASS" in result.llm_summary
        )

    def test_call_strategy_missing_calls(self, clean_data):
        """long_calls requires calls; puts-only should fail."""
        df = clean_data[clean_data["option_type"] == "put"].copy()
        result = execute_tool(
            "check_data_quality",
            {"strategy_name": "long_calls"},
            df,
        )
        assert "FAIL" in result.llm_summary
        assert "call" in result.llm_summary.lower()

    def test_no_strategy_skips_check(self, clean_data):
        """Without strategy_name, option type balance check is skipped."""
        df = clean_data[clean_data["option_type"] == "call"].copy()
        result = execute_tool("check_data_quality", {}, df)
        assert "Option Type Balance" not in (result.user_display or "")


# ---------------------------------------------------------------------------
# Tests — strike density
# ---------------------------------------------------------------------------


class TestStrikeDensity:
    def test_butterfly_sparse_strikes(self):
        """Butterfly needs ≥3 strikes per date; 1 strike should warn."""
        exp = datetime.datetime(2024, 3, 15)
        qd = pd.Timestamp("2024-01-02")
        df = pd.DataFrame(
            {
                "underlying_symbol": ["SPY"] * 2,
                "option_type": ["call"] * 2,
                "expiration": [exp] * 2,
                "quote_date": [qd] * 2,
                "strike": [480.0, 480.0],
                "bid": [5.0, 5.0],
                "ask": [5.10, 5.10],
            }
        )
        result = execute_tool(
            "check_data_quality",
            {"strategy_name": "long_call_butterfly"},
            df,
        )
        assert "strike" in result.llm_summary.lower()
        assert "WARN" in result.llm_summary

    def test_butterfly_sufficient_strikes(self):
        """Butterfly with ≥3 distinct strikes should pass."""
        exp = datetime.datetime(2024, 3, 15)
        qd = pd.Timestamp("2024-01-02")
        df = pd.DataFrame(
            {
                "underlying_symbol": ["SPY"] * 3,
                "option_type": ["call"] * 3,
                "expiration": [exp] * 3,
                "quote_date": [qd] * 3,
                "strike": [475.0, 480.0, 485.0],
                "bid": [8.0, 5.0, 3.0],
                "ask": [8.10, 5.10, 3.10],
            }
        )
        result = execute_tool(
            "check_data_quality",
            {"strategy_name": "long_call_butterfly"},
            df,
        )
        assert "PASS" in result.llm_summary
        assert (
            "≥ 3" in result.llm_summary
            or ">= 3" in result.llm_summary
            or "3 distinct" in result.llm_summary
        )


# ---------------------------------------------------------------------------
# Tests — expiration coverage
# ---------------------------------------------------------------------------


class TestExpirationCoverage:
    def test_calendar_single_expiration(self):
        """Calendar strategy with 1 expiration per date should warn."""
        exp = datetime.datetime(2024, 3, 15)
        qd = pd.Timestamp("2024-01-02")
        df = pd.DataFrame(
            {
                "underlying_symbol": ["SPY"],
                "option_type": ["call"],
                "expiration": [exp],
                "quote_date": [qd],
                "strike": [480.0],
                "bid": [5.0],
                "ask": [5.10],
            }
        )
        result = execute_tool(
            "check_data_quality",
            {"strategy_name": "long_call_calendar"},
            df,
        )
        assert "expiration" in result.llm_summary.lower()
        assert "WARN" in result.llm_summary

    def test_calendar_multiple_expirations(self):
        """Calendar strategy with ≥2 expirations per date should pass."""
        exp1 = datetime.datetime(2024, 3, 15)
        exp2 = datetime.datetime(2024, 4, 19)
        qd = pd.Timestamp("2024-01-02")
        df = pd.DataFrame(
            {
                "underlying_symbol": ["SPY", "SPY"],
                "option_type": ["call", "call"],
                "expiration": [exp1, exp2],
                "quote_date": [qd, qd],
                "strike": [480.0, 480.0],
                "bid": [5.0, 7.0],
                "ask": [5.10, 7.10],
            }
        )
        result = execute_tool(
            "check_data_quality",
            {"strategy_name": "long_call_calendar"},
            df,
        )
        assert "PASS" in result.llm_summary
        assert "expiration" in result.llm_summary.lower()

    def test_non_calendar_skips_check(self, clean_data):
        """Non-calendar strategy should not run expiration coverage check."""
        result = execute_tool(
            "check_data_quality",
            {"strategy_name": "long_calls"},
            clean_data,
        )
        assert "Expiration Coverage" not in (result.user_display or "")
