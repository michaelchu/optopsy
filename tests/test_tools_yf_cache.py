"""Tests for yfinance caching in _yf_fetch_and_cache and _fetch_stock_data_for_signals."""

from datetime import date, timedelta
from unittest.mock import patch

import pandas as pd
import pytest

pytest.importorskip("yfinance", reason="yfinance not installed (install ui extras)")
pytest.importorskip("chainlit", reason="chainlit not installed (install ui extras)")

from optopsy.ui.providers.cache import ParquetCache
from optopsy.ui.tools import _YF_CACHE_CATEGORY, _fetch_stock_data_for_signals
from optopsy.ui.tools._helpers import _yf_fetch_and_cache

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
    """On a cold cache, yfinance is called with period='max' and results are stored."""
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
    # Should use period="max" for all-or-nothing fetch
    mock_dl.assert_called_with("SPY", period="max", progress=False)


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


def test_warm_cache_fetches_only_tail(tmp_path):
    """When cache exists but is behind date_max, only the tail is fetched."""
    dataset = _make_options_dataset("SPY", ["2025-12-16", "2025-12-17"])
    cache = ParquetCache(str(tmp_path))

    date_max = pd.to_datetime("2025-12-17").date()

    # Cache ends a few days before date_max
    cache_start = date_max - timedelta(days=400)  # plenty of history
    cache_end = date_max - timedelta(days=5)
    cached_df = _make_cached_df("SPY", cache_start, cache_end)
    cache.write(_YF_CACHE_CATEGORY, "SPY", cached_df)

    # _make_cached_df uses freq="B" so actual max may differ from cache_end;
    # compute expected fetch start from the real cached max date.
    actual_cache_max = pd.to_datetime(cached_df["date"]).dt.date.max()
    expected_fetch_start = str(actual_cache_max + timedelta(days=1))
    expected_fetch_end = str(date_max + timedelta(days=1))

    with (
        patch("optopsy.ui.tools._helpers._yf_cache", cache),
        patch("yfinance.download") as mock_dl,
    ):
        mock_dl.return_value = _make_yf_download_result(
            actual_cache_max + timedelta(days=1), date_max
        )
        result = _fetch_stock_data_for_signals(dataset)

    assert result is not None
    assert not result.empty
    # Should fetch only the missing tail, not period="max"
    mock_dl.assert_called_once_with(
        "SPY",
        start=expected_fetch_start,
        end=expected_fetch_end,
        progress=False,
    )


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

    with (
        patch("optopsy.ui.tools._helpers._yf_cache", cache),
        patch("yfinance.download") as mock_dl,
    ):
        mock_dl.return_value = _make_yf_download_result(padded_start, date_max)
        result = _fetch_stock_data_for_signals(dataset)

    assert result is not None
    assert set(result["underlying_symbol"].unique()) == {"SPY", "QQQ"}
    # Each symbol fetched once (cold cache)
    assert mock_dl.call_count == 2
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
    date_max = pd.to_datetime("2025-12-17").date()
    padded_start = date_min - timedelta(days=365)

    def fake_download(symbol, **kwargs):
        if symbol == "SPY":
            raise OSError("network error")
        return _make_yf_download_result(padded_start, date_max)

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


# ---------------------------------------------------------------------------
# Direct _yf_fetch_and_cache unit tests
# ---------------------------------------------------------------------------


class TestYfFetchAndCache:
    """Unit tests for _yf_fetch_and_cache edge cases.

    Core cold/warm/hit paths are already covered by the integration tests
    above (test_cache_miss_*, test_full_cache_hit_*, test_warm_cache_*).
    These tests target behaviours only exercisable at the unit level.
    """

    def test_tail_fetch_returns_empty(self, tmp_path):
        """yfinance returns empty for the tail → returns original cached data."""
        cache = ParquetCache(str(tmp_path))
        cached_df = _make_cached_df("SPY", date(2020, 1, 1), date(2025, 12, 10))

        with (
            patch("optopsy.ui.tools._helpers._yf_cache", cache),
            patch("yfinance.download") as mock_dl,
        ):
            mock_dl.return_value = pd.DataFrame()
            result = _yf_fetch_and_cache("SPY", cached_df, date(2025, 12, 17))

        assert result is not None
        assert len(result) == len(cached_df)

    def test_cold_fetch_returns_empty(self, tmp_path):
        """Cold cache + yfinance returns empty → returns None."""
        cache = ParquetCache(str(tmp_path))

        with (
            patch("optopsy.ui.tools._helpers._yf_cache", cache),
            patch("yfinance.download") as mock_dl,
        ):
            mock_dl.return_value = pd.DataFrame()
            result = _yf_fetch_and_cache("SPY", None, date(2025, 12, 17))

        assert result is None

    def test_interior_gaps_ignored(self, tmp_path):
        """Cache with a 15-day interior gap does NOT trigger re-fetch.

        This is the core regression test for the fix — the old gap-detection
        logic would have flagged this as missing data and re-fetched.
        """
        cache = ParquetCache(str(tmp_path))
        end = date(2025, 12, 17)

        # 15-day gap between Nov 20 and Dec 5
        part1 = _make_cached_df("SPY", date(2020, 1, 1), date(2025, 11, 20))
        part2 = _make_cached_df("SPY", date(2025, 12, 5), end)
        cached_df = pd.concat([part1, part2], ignore_index=True)

        with (
            patch("optopsy.ui.tools._helpers._yf_cache", cache),
            patch("yfinance.download") as mock_dl,
        ):
            result = _yf_fetch_and_cache("SPY", cached_df, end)

        mock_dl.assert_not_called()
        assert result is not None

    def test_tail_merges_and_persists(self, tmp_path):
        """Tail fetch data is merged with existing cache and persisted to disk."""
        cache = ParquetCache(str(tmp_path))
        end = date(2025, 12, 17)
        cached_df = _make_cached_df("SPY", date(2025, 1, 1), date(2025, 12, 10))
        cache.write(_YF_CACHE_CATEGORY, "SPY", cached_df)
        actual_cache_max = pd.to_datetime(cached_df["date"]).dt.date.max()

        with (
            patch("optopsy.ui.tools._helpers._yf_cache", cache),
            patch("yfinance.download") as mock_dl,
        ):
            mock_dl.return_value = _make_yf_download_result(
                actual_cache_max + timedelta(days=1), end
            )
            _yf_fetch_and_cache("SPY", cached_df, end)

        on_disk = cache.read(_YF_CACHE_CATEGORY, "SPY")
        assert on_disk is not None
        assert len(on_disk) > len(cached_df)
        disk_max = pd.to_datetime(on_disk["date"]).dt.date.max()
        assert disk_max >= actual_cache_max
