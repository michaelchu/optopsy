"""Tests for yfinance caching in _fetch_stock_data_for_signals."""

from datetime import date, timedelta
from unittest.mock import patch

import pandas as pd
import pytest

pytest.importorskip("yfinance", reason="yfinance not installed (install ui extras)")
pytest.importorskip("chainlit", reason="chainlit not installed (install ui extras)")

from optopsy.ui.providers.cache import ParquetCache
from optopsy.ui.tools import _fetch_stock_data_for_signals, _YF_CACHE_CATEGORY

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_options_dataset(symbol: str, dates: list[str]) -> pd.DataFrame:
    """Minimal options DataFrame with just enough columns for the function."""
    return pd.DataFrame(
        {
            "underlying_symbol": symbol,
            "quote_date": pd.to_datetime(dates),
            "strike": 100.0,
            "bid": 1.0,
            "ask": 1.1,
        }
    )


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
    """Pre-built cache DataFrame matching the stored schema (uses 'date' column)."""
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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_cache_miss_fetches_yfinance_and_writes_cache(tmp_path):
    """On a cold cache, yfinance is called and results are stored."""
    dataset = _make_options_dataset("SPY", ["2025-12-16", "2025-12-17"])
    cache = ParquetCache(str(tmp_path))

    with (
        patch("optopsy.ui.tools._helpers._yf_cache", cache),
        patch("yfinance.download") as mock_dl,
    ):
        # Return a realistic yfinance result
        date_min = pd.to_datetime("2025-12-16").date()
        date_max = pd.to_datetime("2025-12-17").date()
        padded_start = date_min - timedelta(days=365)
        mock_dl.return_value = _make_yf_download_result(padded_start, date_max)

        result = _fetch_stock_data_for_signals(dataset)

    assert result is not None
    assert not result.empty
    assert "quote_date" in result.columns
    assert set(result["underlying_symbol"].unique()) == {"SPY"}

    # Cache file must have been written
    cached = cache.read(_YF_CACHE_CATEGORY, "SPY")
    assert cached is not None
    assert not cached.empty
    assert "date" in cached.columns  # stored as 'date', not 'quote_date'

    mock_dl.assert_called_once()


def test_full_cache_hit_skips_yfinance(tmp_path):
    """When cache covers the full requested range, yfinance is never called."""
    dataset = _make_options_dataset("SPY", ["2025-12-16", "2025-12-17"])
    cache = ParquetCache(str(tmp_path))

    # Pre-seed cache to cover padded_start → date_max
    date_min = pd.to_datetime("2025-12-16").date()
    date_max = pd.to_datetime("2025-12-17").date()
    padded_start = date_min - timedelta(days=365)
    cached_df = _make_cached_df("SPY", padded_start, date_max)
    cache.write(_YF_CACHE_CATEGORY, "SPY", cached_df)

    with (
        patch("optopsy.ui.tools._helpers._yf_cache", cache),
        patch("yfinance.download") as mock_dl,
    ):
        result = _fetch_stock_data_for_signals(dataset)

    assert result is not None
    assert not result.empty
    mock_dl.assert_not_called()


def test_partial_cache_hit_fetches_only_gap(tmp_path):
    """When cache covers only part of the range, only the missing gap is fetched."""
    dataset = _make_options_dataset("SPY", ["2025-12-16", "2025-12-17"])
    cache = ParquetCache(str(tmp_path))

    date_min = pd.to_datetime("2025-12-16").date()
    date_max = pd.to_datetime("2025-12-17").date()
    padded_start = date_min - timedelta(days=365)

    # Cache covers only the latter half of the needed range
    cache_start = date_min - timedelta(days=180)  # shorter than padded_start
    cached_df = _make_cached_df("SPY", cache_start, date_max)
    cache.write(_YF_CACHE_CATEGORY, "SPY", cached_df)

    fetched_ranges: list[tuple[str, str]] = []

    def fake_download(symbol, start, end, progress):
        fetched_ranges.append((start, end))
        fetch_start = pd.Timestamp(start).date()
        fetch_end = pd.Timestamp(end).date() - timedelta(days=1)
        return _make_yf_download_result(fetch_start, fetch_end)

    with (
        patch("optopsy.ui.tools._helpers._yf_cache", cache),
        patch("yfinance.download", side_effect=fake_download),
    ):
        result = _fetch_stock_data_for_signals(dataset)

    assert result is not None
    assert not result.empty
    # Exactly one gap fetch should have happened (the missing portion before cache_start)
    assert len(fetched_ranges) == 1
    # The fetched range should start at padded_start
    assert fetched_ranges[0][0] == str(padded_start)


def test_result_uses_quote_date_column(tmp_path):
    """Output DataFrame must expose 'quote_date', not 'date'."""
    dataset = _make_options_dataset("SPY", ["2025-12-16"])
    cache = ParquetCache(str(tmp_path))

    date_min = pd.to_datetime("2025-12-16").date()
    date_max = date_min
    padded_start = date_min - timedelta(days=365)
    cached_df = _make_cached_df("SPY", padded_start, date_max)
    cache.write(_YF_CACHE_CATEGORY, "SPY", cached_df)

    with patch("optopsy.ui.tools._helpers._yf_cache", cache):
        result = _fetch_stock_data_for_signals(dataset)

    assert result is not None
    assert "quote_date" in result.columns
    assert "date" not in result.columns


def test_empty_dataset_returns_none():
    """Empty dataset → None without touching yfinance or cache."""
    with patch("yfinance.download") as mock_dl:
        result = _fetch_stock_data_for_signals(pd.DataFrame())
    assert result is None
    mock_dl.assert_not_called()


def test_multi_symbol_independent_cache_entries(tmp_path):
    """Two symbols produce separate cache files and are both present in output."""
    dataset = pd.DataFrame(
        {
            "underlying_symbol": ["SPY", "SPY", "QQQ", "QQQ"],
            "quote_date": pd.to_datetime(
                ["2025-12-16", "2025-12-17", "2025-12-16", "2025-12-17"]
            ),
            "strike": 100.0,
            "bid": 1.0,
            "ask": 1.1,
        }
    )
    cache = ParquetCache(str(tmp_path))

    date_min = pd.to_datetime("2025-12-16").date()
    date_max = pd.to_datetime("2025-12-17").date()
    padded_start = date_min - timedelta(days=365)

    call_count = {"n": 0}

    def fake_download(symbol, start, end, progress):
        call_count["n"] += 1
        return _make_yf_download_result(
            pd.Timestamp(start).date(), pd.Timestamp(end).date() - timedelta(days=1)
        )

    with (
        patch("optopsy.ui.tools._helpers._yf_cache", cache),
        patch("yfinance.download", side_effect=fake_download),
    ):
        result = _fetch_stock_data_for_signals(dataset)

    assert result is not None
    assert set(result["underlying_symbol"].unique()) == {"SPY", "QQQ"}
    # Each symbol fetched once (cold cache)
    assert call_count["n"] == 2
    # Separate cache files written
    assert cache.read(_YF_CACHE_CATEGORY, "SPY") is not None
    assert cache.read(_YF_CACHE_CATEGORY, "QQQ") is not None


def test_failed_symbol_does_not_block_other(tmp_path):
    """When one symbol fetch fails (OSError/ValueError), the other symbol still succeeds."""
    dataset = pd.DataFrame(
        {
            "underlying_symbol": ["SPY", "SPY", "QQQ", "QQQ"],
            "quote_date": pd.to_datetime(
                ["2025-12-16", "2025-12-17", "2025-12-16", "2025-12-17"]
            ),
            "strike": 100.0,
            "bid": 1.0,
            "ask": 1.1,
        }
    )
    cache = ParquetCache(str(tmp_path))

    date_min = pd.to_datetime("2025-12-16").date()
    padded_start = date_min - timedelta(days=365)

    def fake_download(symbol, start, end, progress):
        if symbol == "SPY":
            raise OSError("network error")
        date_end = pd.Timestamp(end).date() - timedelta(days=1)
        return _make_yf_download_result(pd.Timestamp(start).date(), date_end)

    with (
        patch("optopsy.ui.tools._helpers._yf_cache", cache),
        patch("yfinance.download", side_effect=fake_download),
    ):
        result = _fetch_stock_data_for_signals(dataset)

    # QQQ should succeed even though SPY failed
    assert result is not None
    assert set(result["underlying_symbol"].unique()) == {"QQQ"}
    assert (
        cache.read(_YF_CACHE_CATEGORY, "SPY") is None
    )  # nothing cached for failed symbol
