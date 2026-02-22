"""Tests for the fetch_stock_data tool handler."""

from datetime import date, timedelta
from unittest.mock import patch

import pandas as pd
import pytest

pytest.importorskip("yfinance", reason="yfinance not installed (install ui extras)")
pytest.importorskip("chainlit", reason="chainlit not installed (install ui extras)")

from optopsy.ui.providers.cache import ParquetCache
from optopsy.ui.tools._executor import execute_tool
from optopsy.ui.tools._helpers import _YF_CACHE_CATEGORY

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_yf_download_result(start: date, end: date) -> pd.DataFrame:
    """Simulate a yfinance download result (DatetimeIndex, OHLCV columns)."""
    dates = pd.date_range(start, end, freq="B")
    df = pd.DataFrame(
        {
            "Open": 100.0,
            "High": 105.0,
            "Low": 98.0,
            "Close": 102.0,
            "Volume": 1_000_000,
        },
        index=dates,
    )
    df.index.name = "Date"
    return df


def _make_cached_df(symbol: str, start: date, end: date) -> pd.DataFrame:
    """Pre-built cache DataFrame matching the stored schema."""
    dates = pd.date_range(start, end, freq="B")
    return pd.DataFrame(
        {
            "underlying_symbol": symbol,
            "date": pd.to_datetime(dates),
            "open": 100.0,
            "high": 105.0,
            "low": 98.0,
            "close": 102.0,
            "volume": 1_000_000,
        }
    )


def _call_handler(arguments, cache):
    """Invoke the fetch_stock_data handler via execute_tool."""
    with patch("optopsy.ui.tools._executor._yf_cache", cache):
        return execute_tool("fetch_stock_data", arguments, dataset=None)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_cold_cache_fetches_full_history(tmp_path):
    """On a cold cache, yfinance is called with period='max'."""
    cache = ParquetCache(str(tmp_path))

    with patch("yfinance.download") as mock_dl:
        mock_dl.return_value = _make_yf_download_result(
            date(2020, 1, 1), date(2025, 12, 31)
        )
        result = _call_handler({"symbol": "SPY"}, cache)

    mock_dl.assert_called_once()
    _, kwargs = mock_dl.call_args
    assert kwargs.get("period") == "max"
    assert "Fetched" in result.llm_summary
    assert "SPY" in result.llm_summary

    # Data should be cached
    cached = cache.read(_YF_CACHE_CATEGORY, "SPY")
    assert cached is not None
    assert not cached.empty


def test_fresh_cache_skips_fetch(tmp_path):
    """When cache max date is today, yfinance is not called."""
    cache = ParquetCache(str(tmp_path))
    # Build cache with today as an explicit date (not via freq="B" which skips weekends)
    cached_df = _make_cached_df(
        "SPY", date(2020, 1, 1), date.today() - timedelta(days=1)
    )
    # Append a row for today so cache_max == date.today()
    today_row = pd.DataFrame(
        {
            "underlying_symbol": ["SPY"],
            "date": [pd.Timestamp(date.today())],
            "open": [100.0],
            "high": [105.0],
            "low": [98.0],
            "close": [102.0],
            "volume": [1_000_000],
        }
    )
    cached_df = pd.concat([cached_df, today_row], ignore_index=True)
    cache.write(_YF_CACHE_CATEGORY, "SPY", cached_df)

    with patch("yfinance.download") as mock_dl:
        result = _call_handler({"symbol": "SPY"}, cache)

    mock_dl.assert_not_called()
    assert "Fetched" in result.llm_summary


def test_stale_cache_fetches_incremental(tmp_path):
    """When cache is stale, only the gap between cache max and today is fetched."""
    cache = ParquetCache(str(tmp_path))
    cache_end = date.today() - timedelta(days=10)
    cached_df = _make_cached_df("SPY", date(2020, 1, 1), cache_end)
    cache.write(_YF_CACHE_CATEGORY, "SPY", cached_df)

    expected_start = str(cache_end + timedelta(days=1))
    expected_end = str(date.today() + timedelta(days=1))

    with patch("yfinance.download") as mock_dl:
        mock_dl.return_value = _make_yf_download_result(
            cache_end + timedelta(days=1), date.today()
        )
        result = _call_handler({"symbol": "SPY"}, cache)

    mock_dl.assert_called_once()
    _, kwargs = mock_dl.call_args
    assert kwargs["start"] == expected_start
    assert kwargs["end"] == expected_end
    assert "period" not in kwargs
    assert "Fetched" in result.llm_summary


def test_empty_yfinance_result(tmp_path):
    """When yfinance returns empty on a cold cache, handler reports no data."""
    cache = ParquetCache(str(tmp_path))

    with patch("yfinance.download") as mock_dl:
        mock_dl.return_value = pd.DataFrame()
        result = _call_handler({"symbol": "INVALID"}, cache)

    assert "No stock data found" in result.llm_summary


def test_yfinance_error_with_existing_cache(tmp_path):
    """When yfinance raises but cache exists, handler returns cached data."""
    cache = ParquetCache(str(tmp_path))
    cache_end = date.today() - timedelta(days=5)
    cached_df = _make_cached_df("SPY", date(2020, 1, 1), cache_end)
    cache.write(_YF_CACHE_CATEGORY, "SPY", cached_df)

    with patch("yfinance.download", side_effect=OSError("network error")):
        result = _call_handler({"symbol": "SPY"}, cache)

    # Should still return cached data despite the error
    assert "Fetched" in result.llm_summary
    assert "SPY" in result.llm_summary


def test_yfinance_error_no_cache(tmp_path):
    """When yfinance raises and no cache exists, handler reports no data."""
    cache = ParquetCache(str(tmp_path))

    with patch("yfinance.download", side_effect=OSError("network error")):
        result = _call_handler({"symbol": "SPY"}, cache)

    assert "No stock data found" in result.llm_summary


def test_symbol_uppercased(tmp_path):
    """Symbol argument is uppercased before use."""
    cache = ParquetCache(str(tmp_path))

    with patch("yfinance.download") as mock_dl:
        mock_dl.return_value = _make_yf_download_result(
            date(2020, 1, 1), date(2025, 12, 31)
        )
        _call_handler({"symbol": "spy"}, cache)

    # Cache should be keyed by uppercase
    cached = cache.read(_YF_CACHE_CATEGORY, "SPY")
    assert cached is not None
