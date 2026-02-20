from datetime import date, timedelta
from unittest.mock import patch

import pandas as pd
import pytest

from optopsy.ui.providers.cache import ParquetCache
from optopsy.ui.providers.eodhd import EODHDProvider

# -- ParquetCache --


@pytest.fixture
def cache(tmp_path):
    return ParquetCache(cache_dir=str(tmp_path))


@pytest.fixture
def sample_df():
    return pd.DataFrame({"symbol": ["AAPL", "AAPL"], "price": [150.0, 151.0]})


class TestParquetCacheReadWrite:
    def test_read_missing_returns_none(self, cache):
        assert cache.read("options", "AAPL") is None

    def test_write_then_read(self, cache, sample_df):
        cache.write("options", "AAPL", sample_df)
        result = cache.read("options", "AAPL")
        assert result is not None
        pd.testing.assert_frame_equal(result, sample_df)

    def test_symbol_uppercased(self, cache, sample_df):
        cache.write("options", "aapl", sample_df)
        result = cache.read("options", "AAPL")
        assert result is not None
        assert len(result) == 2

    def test_separate_categories(self, cache, sample_df):
        cache.write("options", "AAPL", sample_df)
        assert cache.read("stocks", "AAPL") is None

    def test_corrupt_file_returns_none(self, cache, tmp_path):
        path = tmp_path / "options"
        path.mkdir()
        (path / "AAPL.parquet").write_text("not a parquet file")
        assert cache.read("options", "AAPL") is None

    def test_read_does_not_create_directories(self, cache, tmp_path):
        """read() should not create category directories as a side effect."""
        cache.read("newcategory", "AAPL")
        assert not (tmp_path / "newcategory").exists()


class TestParquetCacheMergeAndSave:
    def test_merge_no_existing(self, cache):
        df = pd.DataFrame({"a": [1, 2]})
        result = cache.merge_and_save("options", "AAPL", df)
        assert len(result) == 2
        assert cache.read("options", "AAPL") is not None

    def test_merge_with_existing_deduplicates(self, cache):
        df1 = pd.DataFrame({"a": [1, 2, 3]})
        df2 = pd.DataFrame({"a": [2, 3, 4]})
        cache.write("options", "AAPL", df1)
        result = cache.merge_and_save("options", "AAPL", df2)
        assert sorted(result["a"].tolist()) == [1, 2, 3, 4]

    def test_merge_preserves_on_disk(self, cache):
        df1 = pd.DataFrame({"a": [1, 2]})
        df2 = pd.DataFrame({"a": [3, 4]})
        cache.write("options", "AAPL", df1)
        cache.merge_and_save("options", "AAPL", df2)
        on_disk = cache.read("options", "AAPL")
        assert sorted(on_disk["a"].tolist()) == [1, 2, 3, 4]

    def test_merge_with_dedup_cols_keeps_last(self, cache):
        """When dedup_cols is provided, newer data wins for matching keys."""
        df1 = pd.DataFrame({"key": ["a", "b"], "val": [1, 2]})
        df2 = pd.DataFrame({"key": ["b", "c"], "val": [20, 3]})
        cache.write("options", "AAPL", df1)
        result = cache.merge_and_save("options", "AAPL", df2, dedup_cols=["key"])
        assert len(result) == 3
        b_row = result[result["key"] == "b"]
        assert b_row["val"].iloc[0] == 20  # newer value wins

    def test_merge_with_empty_existing(self, cache, tmp_path):
        """Existing cache file with zero rows should behave like no cache."""
        empty_df = pd.DataFrame({"a": pd.Series([], dtype="int64")})
        cache.write("options", "AAPL", empty_df)
        # Verify read returns the empty frame (not None)
        assert cache.read("options", "AAPL") is not None
        assert cache.read("options", "AAPL").empty
        # merge_and_save should treat it like no existing data
        new_df = pd.DataFrame({"a": [1, 2]})
        result = cache.merge_and_save("options", "AAPL", new_df)
        assert len(result) == 2


# -- _compute_date_gaps --


def _make_cached_df(dates, date_column="quote_date"):
    return pd.DataFrame({date_column: pd.to_datetime(dates)})


class TestComputeDateGaps:
    def test_no_cache_returns_full_range(self):
        gaps = EODHDProvider._compute_date_gaps(
            None, date(2024, 1, 1), date(2024, 3, 1)
        )
        assert gaps == [("2024-01-01", "2024-03-01")]

    def test_empty_cache_returns_full_range(self):
        gaps = EODHDProvider._compute_date_gaps(
            pd.DataFrame(), date(2024, 1, 1), date(2024, 3, 1)
        )
        assert gaps == [("2024-01-01", "2024-03-01")]

    def test_no_dates_no_cache_returns_fetch_all(self):
        """(None, None) means 'fetch everything' — no date filters applied."""
        gaps = EODHDProvider._compute_date_gaps(None, None, None)
        assert gaps == [(None, None)]

    def test_full_cache_hit_no_gaps(self):
        # Dense cache every 3 days — request falls entirely within
        cached = _make_cached_df(pd.date_range("2024-01-01", "2024-03-01", freq="3D"))
        gaps = EODHDProvider._compute_date_gaps(
            cached, date(2024, 1, 15), date(2024, 2, 15)
        )
        assert gaps == []

    def test_gap_before_cache(self):
        # Dense cache from Mar-Jun, request starts before cache
        cached = _make_cached_df(pd.date_range("2024-03-01", "2024-06-01", freq="3D"))
        gaps = EODHDProvider._compute_date_gaps(
            cached, date(2024, 1, 1), date(2024, 5, 1)
        )
        assert gaps == [("2024-01-01", "2024-02-29")]

    def test_gap_after_cache(self):
        # Dense cache from Jan-Mar, request extends past cache
        cached = _make_cached_df(pd.date_range("2024-01-01", "2024-03-01", freq="3D"))
        gaps = EODHDProvider._compute_date_gaps(
            cached, date(2024, 2, 1), date(2024, 6, 1)
        )
        assert gaps == [("2024-03-02", "2024-06-01")]

    def test_gaps_both_sides(self):
        # Dense cache every 3 days — well under interior gap threshold
        dates = pd.date_range("2024-03-01", "2024-06-01", freq="3D")
        cached = _make_cached_df(dates)
        gaps = EODHDProvider._compute_date_gaps(
            cached, date(2024, 1, 1), date(2024, 9, 1)
        )
        assert ("2024-01-01", "2024-02-29") in gaps
        # After-gap starts the day after the actual cached max
        cached_max = dates[-1].date()
        after_start = str(cached_max + timedelta(days=1))
        assert (after_start, "2024-09-01") in gaps

    def test_no_end_date_fetches_after_cache(self):
        # Dense cache from Jan-Mar
        cached = _make_cached_df(pd.date_range("2024-01-01", "2024-03-01", freq="3D"))
        cached_max = pd.date_range("2024-01-01", "2024-03-01", freq="3D")[-1].date()
        gaps = EODHDProvider._compute_date_gaps(cached, date(2024, 2, 1), None)
        assert gaps == [(str(cached_max + timedelta(days=1)), None)]

    def test_exact_match_dense_cache_no_gaps(self):
        """Dense cache covering the full range produces no gaps."""
        # Dates 3 days apart — well under the interior gap threshold
        cached = _make_cached_df(
            ["2024-01-01", "2024-01-04", "2024-01-07", "2024-01-10"]
        )
        gaps = EODHDProvider._compute_date_gaps(
            cached, date(2024, 1, 1), date(2024, 1, 10)
        )
        assert gaps == []

    def test_custom_date_column(self):
        # Dense cache from Jan-Mar with custom date column
        cached = _make_cached_df(
            pd.date_range("2024-01-01", "2024-03-01", freq="3D"),
            date_column="date",
        )
        gaps = EODHDProvider._compute_date_gaps(
            cached, date(2024, 2, 1), date(2024, 6, 1), date_column="date"
        )
        assert gaps == [("2024-03-02", "2024-06-01")]

    def test_missing_date_column_returns_full_range(self):
        cached = pd.DataFrame({"other_col": [1, 2, 3]})
        gaps = EODHDProvider._compute_date_gaps(
            cached, date(2024, 1, 1), date(2024, 3, 1)
        )
        assert gaps == [("2024-01-01", "2024-03-01")]

    def test_interior_gap_detected(self):
        """A >5-day hole inside the cached range triggers a re-fetch."""
        cached = _make_cached_df(
            ["2024-01-01", "2024-01-02", "2024-02-01", "2024-02-02"]
        )
        gaps = EODHDProvider._compute_date_gaps(
            cached, date(2024, 1, 1), date(2024, 2, 2)
        )
        # Jan 2 → Feb 1 is 30 days apart, well over the threshold
        assert ("2024-01-03", "2024-01-31") in gaps

    def test_small_interior_gap_ignored(self):
        """Gaps ≤5 calendar days (normal weekends/holidays) are not flagged."""
        # 4-day gap between Jan 3 and Jan 7 (typical weekend + 1)
        cached = _make_cached_df(
            ["2024-01-01", "2024-01-03", "2024-01-07", "2024-01-10"]
        )
        gaps = EODHDProvider._compute_date_gaps(
            cached, date(2024, 1, 1), date(2024, 1, 10)
        )
        assert gaps == []

    def test_interior_gap_outside_request_ignored(self):
        """Interior gaps outside the requested range are not flagged."""
        # Big gap between Jan 5 and Feb 20, but request only covers Jan 1-5
        cached = _make_cached_df(
            ["2024-01-01", "2024-01-05", "2024-02-20", "2024-02-25"]
        )
        gaps = EODHDProvider._compute_date_gaps(
            cached, date(2024, 1, 1), date(2024, 1, 5)
        )
        assert gaps == []

    def test_interior_gap_straddling_overlap_detected(self):
        """A gap that straddles the overlap boundary should still be detected."""
        # Cache: Jan 1-2 and Mar 1-2 (big gap in between)
        # Request: Jan 15 to Feb 15 (entirely inside the gap)
        cached = _make_cached_df(
            ["2024-01-01", "2024-01-02", "2024-03-01", "2024-03-02"]
        )
        gaps = EODHDProvider._compute_date_gaps(
            cached, date(2024, 1, 15), date(2024, 2, 15)
        )
        # Gap should be clamped to the requested range
        assert ("2024-01-15", "2024-02-15") in gaps

    def test_interior_gap_clamped_to_request(self):
        """Interior gap bounds should be clamped to the overlap region."""
        # Cache: Jan 1 and Jun 1 (huge gap). Request: Feb 1 to Apr 1
        cached = _make_cached_df(["2024-01-01", "2024-06-01"])
        gaps = EODHDProvider._compute_date_gaps(
            cached, date(2024, 2, 1), date(2024, 4, 1)
        )
        # Should fetch Feb 1 to Apr 1, not Jan 2 to May 31
        assert ("2024-02-01", "2024-04-01") in gaps


# -- _fetch_with_cache --


class TestFetchWithCacheFallback:
    """Test the cache-aware fetch orchestrator's error-fallback behaviour."""

    @pytest.fixture
    def provider(self, tmp_path):
        p = EODHDProvider()
        p._cache = ParquetCache(cache_dir=str(tmp_path))
        return p

    @patch.dict("os.environ", {"EODHD_API_KEY": "test-key"})
    def test_api_error_with_cache_returns_cached_data(self, provider):
        """When API fails but cache exists, return stale cached data."""
        cached = pd.DataFrame(
            {"date": pd.to_datetime(["2024-01-01", "2024-01-02"]), "val": [1, 2]}
        )
        provider._cache.write("test", "AAPL", cached)

        def failing_fetch(api_key, symbol, gaps):
            return "EODHD rate limit exceeded."

        result, _, _ = provider._fetch_with_cache(
            symbol="AAPL",
            start_date="2024-01-01",
            end_date="2024-06-01",
            category="test",
            date_column="date",
            dedup_cols=["date"],
            fetch_fn=failing_fetch,
            label="test data",
        )
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

    @patch.dict("os.environ", {"EODHD_API_KEY": "test-key"})
    def test_api_error_without_cache_returns_error(self, provider):
        """When API fails and no cache exists, return error string."""

        def failing_fetch(api_key, symbol, gaps):
            return "EODHD rate limit exceeded."

        result, _, _ = provider._fetch_with_cache(
            symbol="AAPL",
            start_date="2024-01-01",
            end_date="2024-06-01",
            category="test",
            date_column="date",
            dedup_cols=["date"],
            fetch_fn=failing_fetch,
            label="test data",
        )
        assert isinstance(result, str)
        assert "rate limit" in result.lower()
