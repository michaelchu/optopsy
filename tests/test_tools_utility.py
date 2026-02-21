"""Tests for utility tools: clear_cache, describe_data, list_signals, enhanced preview_data."""

import datetime
import os
import tempfile
from unittest.mock import patch

import pandas as pd
import pytest

pytest.importorskip("pyarrow", reason="UI extras not installed")

from optopsy.ui.providers.cache import ParquetCache
from optopsy.ui.tools import execute_tool

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def option_data():
    """Small option dataset for testing preview/describe tools."""
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
# clear_cache tests
# ---------------------------------------------------------------------------


class TestClearCache:
    def test_clear_cache_all(self, tmp_path):
        """Clearing all cache files returns correct count and MB freed."""
        cache_dir = tmp_path / "cache"
        cat_dir = cache_dir / "options"
        cat_dir.mkdir(parents=True)
        df = pd.DataFrame({"a": [1, 2, 3]})
        df.to_parquet(cat_dir / "SPY.parquet")
        df.to_parquet(cat_dir / "QQQ.parquet")

        with patch(
            "optopsy.ui.tools._executor.ParquetCache",
            return_value=ParquetCache(str(cache_dir)),
        ):
            result = execute_tool("clear_cache", {}, None)

        assert "2" in result.llm_summary
        assert "cleared" in result.llm_summary.lower()

    def test_clear_cache_symbol(self, tmp_path):
        """Clearing a specific symbol only removes that symbol's files."""
        cache_dir = tmp_path / "cache"
        cat_dir = cache_dir / "options"
        cat_dir.mkdir(parents=True)
        df = pd.DataFrame({"a": [1, 2, 3]})
        df.to_parquet(cat_dir / "SPY.parquet")
        df.to_parquet(cat_dir / "QQQ.parquet")

        with patch(
            "optopsy.ui.tools._executor.ParquetCache",
            return_value=ParquetCache(str(cache_dir)),
        ):
            result = execute_tool("clear_cache", {"symbol": "SPY"}, None)

        assert "1" in result.llm_summary
        assert "SPY" in result.llm_summary

    def test_clear_cache_empty(self, tmp_path):
        """Clearing when no cache exists returns a 'nothing to clear' message."""
        cache_dir = tmp_path / "nonexistent_cache"

        with patch(
            "optopsy.ui.tools._executor.ParquetCache",
            return_value=ParquetCache(str(cache_dir)),
        ):
            result = execute_tool("clear_cache", {}, None)

        assert "no cached files" in result.llm_summary.lower()


# ---------------------------------------------------------------------------
# describe_data tests
# ---------------------------------------------------------------------------


class TestDescribeData:
    def test_describe_data(self, option_data):
        """Basic describe returns shape, dtypes, and numeric summary."""
        result = execute_tool("describe_data", {}, option_data)
        summary = result.llm_summary
        assert "8 rows" in summary
        assert "8 columns" in summary
        # Should mention numeric column stats
        assert "strike" in summary or "bid" in summary

    def test_describe_data_with_columns(self, option_data):
        """Filtering to specific columns only describes those columns."""
        result = execute_tool(
            "describe_data", {"columns": ["strike", "bid"]}, option_data
        )
        # User display should have the specific columns
        assert "strike" in result.user_display
        assert "bid" in result.user_display
        # Should not describe other columns
        assert "option_type" not in result.user_display.split("Data Types")[0]

    def test_describe_data_missing_columns(self, option_data):
        """Requesting nonexistent columns returns an error."""
        result = execute_tool(
            "describe_data", {"columns": ["nonexistent_col"]}, option_data
        )
        assert "not found" in result.llm_summary.lower()

    def test_describe_data_no_dataset(self):
        """Calling describe_data with no dataset loaded returns an error."""
        result = execute_tool("describe_data", {}, None)
        assert "no dataset" in result.llm_summary.lower()

    def test_describe_data_categorical_columns(self, option_data):
        """Key categorical columns get value_counts in the display."""
        result = execute_tool("describe_data", {}, option_data)
        display = result.user_display
        # underlying_symbol and option_type should have value_counts
        assert "underlying_symbol" in display
        assert "option_type" in display
        assert "SPX" in display
        assert "call" in display

    def test_describe_data_date_columns(self, option_data):
        """Date columns show min/max/nunique in the display."""
        result = execute_tool("describe_data", {}, option_data)
        display = result.user_display
        assert "quote_date" in display
        assert "expiration" in display


# ---------------------------------------------------------------------------
# list_signals tests
# ---------------------------------------------------------------------------


class TestListSignals:
    def test_list_signals_empty(self, option_data):
        """No signals built yet returns appropriate message."""
        result = execute_tool("list_signals", {}, option_data, signals={})
        assert "no signals" in result.llm_summary.lower()

    def test_list_signals_with_slots(self, option_data):
        """Shows built signals with date counts and ranges."""
        valid_dates = pd.DataFrame(
            {
                "underlying_symbol": ["SPX", "SPX", "SPX"],
                "quote_date": pd.to_datetime(
                    ["2018-01-03", "2018-01-04", "2018-01-05"]
                ),
            }
        )
        signals = {"entry": valid_dates}
        result = execute_tool("list_signals", {}, option_data, signals=signals)
        summary = result.llm_summary
        assert "entry" in summary
        assert "3 dates" in summary
        assert "SPX" in summary

    def test_list_signals_empty_slot(self, option_data):
        """A signal slot with 0 dates is reported correctly."""
        empty_dates = pd.DataFrame(columns=["underlying_symbol", "quote_date"])
        signals = {"empty_slot": empty_dates}
        result = execute_tool("list_signals", {}, option_data, signals=signals)
        assert "0 dates" in result.llm_summary

    def test_list_signals_multiple_slots(self, option_data):
        """Multiple signal slots are all listed."""
        dates_1 = pd.DataFrame(
            {
                "underlying_symbol": ["SPX"],
                "quote_date": pd.to_datetime(["2018-01-03"]),
            }
        )
        dates_2 = pd.DataFrame(
            {
                "underlying_symbol": ["SPX", "SPX"],
                "quote_date": pd.to_datetime(["2018-01-04", "2018-01-05"]),
            }
        )
        signals = {"entry": dates_1, "exit": dates_2}
        result = execute_tool("list_signals", {}, option_data, signals=signals)
        assert "2 signal slot" in result.llm_summary
        assert "entry" in result.llm_summary
        assert "exit" in result.llm_summary


# ---------------------------------------------------------------------------
# Enhanced preview_data tests
# ---------------------------------------------------------------------------


class TestPreviewDataEnhanced:
    def test_preview_data_default(self, option_data):
        """Default preview shows first 5 rows."""
        result = execute_tool("preview_data", {}, option_data)
        assert "First 5 rows" in result.user_display

    def test_preview_data_tail(self, option_data):
        """Tail mode shows last rows."""
        result = execute_tool(
            "preview_data", {"position": "tail", "rows": 3}, option_data
        )
        assert "Last 3 rows" in result.user_display

    def test_preview_data_sample(self, option_data):
        """Sample mode shows random rows."""
        result = execute_tool("preview_data", {"sample": True, "rows": 3}, option_data)
        assert "Random sample" in result.user_display

    def test_preview_data_custom_rows(self, option_data):
        """Custom row count is respected."""
        result = execute_tool("preview_data", {"rows": 2}, option_data)
        assert "First 2 rows" in result.user_display

    def test_preview_data_sample_larger_than_df(self, option_data):
        """Requesting more sample rows than exist returns all rows."""
        result = execute_tool(
            "preview_data", {"sample": True, "rows": 100}, option_data
        )
        # Should show all 8 rows (capped to len(df))
        assert "Random sample of 8 rows" in result.user_display

    def test_preview_data_head_default_position(self, option_data):
        """Explicit head position works the same as default."""
        result_default = execute_tool("preview_data", {"rows": 3}, option_data)
        result_head = execute_tool(
            "preview_data", {"rows": 3, "position": "head"}, option_data
        )
        assert "First 3 rows" in result_default.user_display
        assert "First 3 rows" in result_head.user_display
