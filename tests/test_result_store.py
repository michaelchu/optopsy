"""Tests for ResultStore and query_results tool."""

import pandas as pd
import pytest

pyarrow = pytest.importorskip("pyarrow")  # noqa: F841
pydantic = pytest.importorskip("pydantic")  # noqa: F841

from optopsy.ui.providers.result_store import ResultStore  # noqa: E402
from optopsy.ui.tools._executor import execute_tool  # noqa: E402
from optopsy.ui.tools._helpers import _cached_run, _with_cache_key  # noqa: E402

# ---------------------------------------------------------------------------
# ResultStore unit tests
# ---------------------------------------------------------------------------


@pytest.fixture
def store(tmp_path):
    """ResultStore scoped to a temporary directory."""
    return ResultStore(results_dir=str(tmp_path / "results"))


@pytest.fixture
def sample_df():
    return pd.DataFrame(
        {
            "strategy": ["long_calls", "short_puts"],
            "mean_return": [0.05, -0.02],
            "count": [100, 50],
        }
    )


class TestResultStore:
    def test_write_read_roundtrip(self, store, sample_df):
        store.write("abc123", sample_df, {"type": "strategy"})
        result = store.read("abc123")
        assert result is not None
        pd.testing.assert_frame_equal(result, sample_df)

    def test_has(self, store, sample_df):
        assert not store.has("abc123")
        store.write("abc123", sample_df, {"type": "strategy"})
        assert store.has("abc123")

    def test_read_missing(self, store):
        assert store.read("nonexistent") is None

    def test_get_metadata(self, store, sample_df):
        meta = {"type": "strategy", "strategy": "long_calls"}
        store.write("abc123", sample_df, meta)
        assert store.get_metadata("abc123") == meta

    def test_get_metadata_missing(self, store):
        assert store.get_metadata("nonexistent") == {}

    def test_list_all(self, store, sample_df):
        assert store.list_all() == {}
        store.write("abc123", sample_df, {"type": "strategy"})
        store.write("def456", sample_df, {"type": "simulation"})
        result = store.list_all()
        assert set(result.keys()) == {"abc123", "def456"}

    def test_clear_single(self, store, sample_df):
        store.write("abc123", sample_df, {"type": "strategy"})
        store.write("def456", sample_df, {"type": "strategy"})
        count = store.clear("abc123")
        assert count == 1
        assert not store.has("abc123")
        assert store.has("def456")
        # Metadata should also be cleaned
        assert "abc123" not in store.list_all()

    def test_clear_all(self, store, sample_df):
        store.write("abc123", sample_df, {"type": "strategy"})
        store.write("def456", sample_df, {"type": "strategy"})
        count = store.clear()
        assert count == 2  # parquet files only (index is cleared, not deleted)
        assert not store.has("abc123")
        assert not store.has("def456")

    def test_total_size_bytes(self, store, sample_df):
        assert store.total_size_bytes() == 0
        store.write("abc123", sample_df, {"type": "strategy"})
        assert store.total_size_bytes() > 0

    def test_make_key_deterministic(self):
        key1 = ResultStore.make_key("long_calls", {"dte": 45, "raw": False}, "fp123")
        key2 = ResultStore.make_key("long_calls", {"dte": 45, "raw": False}, "fp123")
        assert key1 == key2
        assert len(key1) == 64

    def test_make_key_different_params(self):
        key1 = ResultStore.make_key("long_calls", {"dte": 45}, "fp123")
        key2 = ResultStore.make_key("long_calls", {"dte": 90}, "fp123")
        assert key1 != key2

    def test_make_key_different_fingerprint(self):
        key1 = ResultStore.make_key("long_calls", {"dte": 45}, "fp123")
        key2 = ResultStore.make_key("long_calls", {"dte": 45}, "fp456")
        assert key1 != key2

    def test_make_key_different_name(self):
        key1 = ResultStore.make_key("long_calls", {"dte": 45}, "fp123")
        key2 = ResultStore.make_key("short_puts", {"dte": 45}, "fp123")
        assert key1 != key2

    def test_make_key_dataframe_values(self):
        """DataFrame values (e.g. signals) are fingerprinted, not stringified."""
        sig1 = pd.DataFrame({"signal": [1, 0, 1]})
        sig2 = pd.DataFrame({"signal": [0, 1, 0]})
        key1 = ResultStore.make_key("long_calls", {"dte": 45, "entry": sig1}, "fp123")
        key2 = ResultStore.make_key("long_calls", {"dte": 45, "entry": sig2}, "fp123")
        assert key1 != key2
        # Same signal should produce same key
        key3 = ResultStore.make_key("long_calls", {"dte": 45, "entry": sig1}, "fp123")
        assert key1 == key3

    def test_index_survives_corruption(self, store, sample_df):
        """If _index.json is corrupted, reads return empty."""
        store.write("abc123", sample_df, {"type": "strategy"})
        # Corrupt the index
        index_path = store._index_path()
        with open(index_path, "w") as f:
            f.write("not valid json{{{")
        assert store.list_all() == {}
        # Parquet file is still there and readable
        assert store.has("abc123")
        df = store.read("abc123")
        assert df is not None


# ---------------------------------------------------------------------------
# _cached_run helper tests
# ---------------------------------------------------------------------------


class TestCachedRun:
    def test_cache_miss_then_hit(self, store, sample_df):
        calls = []

        def execute():
            calls.append(1)
            return sample_df, ""

        # First call: miss
        df, key, err = _cached_run(
            store, "test", {"a": 1}, "fp123", execute, {"type": "strategy"}
        )
        assert err == ""
        assert df is not None
        assert len(calls) == 1
        pd.testing.assert_frame_equal(df, sample_df)

        # Second call: hit
        df2, key2, err2 = _cached_run(
            store, "test", {"a": 1}, "fp123", execute, {"type": "strategy"}
        )
        assert err2 == ""
        assert len(calls) == 1  # execute NOT called again
        pd.testing.assert_frame_equal(df2, sample_df)
        assert key == key2

    def test_no_fingerprint_skips_cache(self, store, sample_df):
        calls = []

        def execute():
            calls.append(1)
            return sample_df, ""

        df, key, err = _cached_run(
            store, "test", {"a": 1}, None, execute, {"type": "strategy"}
        )
        assert key is None
        assert len(calls) == 1

        # Second call: still executes (no cache)
        df2, key2, err2 = _cached_run(
            store, "test", {"a": 1}, None, execute, {"type": "strategy"}
        )
        assert len(calls) == 2

    def test_error_passthrough(self, store):
        def execute():
            return None, "something went wrong"

        df, key, err = _cached_run(
            store, "test", {"a": 1}, "fp123", execute, {"type": "strategy"}
        )
        assert err == "something went wrong"
        assert df is None

    def test_empty_df_not_cached(self, store):
        def execute():
            return pd.DataFrame(), ""

        df, key, err = _cached_run(
            store, "test", {"a": 1}, "fp123", execute, {"type": "strategy"}
        )
        assert not store.has(key)


# ---------------------------------------------------------------------------
# _with_cache_key helper tests
# ---------------------------------------------------------------------------


class TestWithCacheKey:
    def test_adds_key(self):
        summary = {"strategy": "long_calls", "count": 10}
        result = _with_cache_key(summary, "abc123")
        assert result["_cache_key"] == "abc123"
        assert result["strategy"] == "long_calls"

    def test_no_key(self):
        summary = {"strategy": "long_calls", "count": 10}
        result = _with_cache_key(summary, None)
        assert "_cache_key" not in result


# ---------------------------------------------------------------------------
# query_results handler tests
# ---------------------------------------------------------------------------


class TestQueryResults:
    @pytest.fixture(autouse=True)
    def _patch_store_dir(self, store, monkeypatch):
        """Make the handler's ResultStore() use the tmp_path-backed store."""
        monkeypatch.setattr(
            "optopsy.ui.providers.result_store._RESULTS_DIR", store._dir
        )

    @pytest.fixture
    def stored_result(self, store, sample_df):
        """Write a result to store and return results dict with _cache_key."""
        key = ResultStore.make_key("long_calls", {"dte": 45}, "fp123")
        store.write(
            key,
            sample_df,
            {
                "type": "strategy",
                "strategy": "long_calls",
                "display_key": "long_calls:dte=45",
            },
        )
        results = {
            "long_calls:dte=45,exit=0,otm=0.50,slip=mid": {
                "strategy": "long_calls",
                "count": 100,
                "mean_return": 0.05,
                "_cache_key": key,
            }
        }
        return results, store

    def test_list_mode(self, stored_result):
        results, store = stored_result
        result = execute_tool("query_results", {}, None, results=results)
        assert "1 result(s)" in result.llm_summary

    def test_list_mode_empty(self):
        result = execute_tool("query_results", {}, None, results={})
        assert (
            "No results" in result.llm_summary or "cached results" in result.llm_summary
        )

    def test_query_with_result_key(self, stored_result, sample_df):
        results, store = stored_result
        key = "long_calls:dte=45,exit=0,otm=0.50,slip=mid"
        result = execute_tool(
            "query_results",
            {"result_key": key},
            None,
            results=results,
        )
        assert "2 rows" in result.llm_summary

    def test_query_sort(self, stored_result):
        results, store = stored_result
        key = "long_calls:dte=45,exit=0,otm=0.50,slip=mid"
        result = execute_tool(
            "query_results",
            {"result_key": key, "sort_by": "mean_return", "ascending": True},
            None,
            results=results,
        )
        assert "2 rows" in result.llm_summary

    def test_query_head(self, stored_result):
        results, store = stored_result
        key = "long_calls:dte=45,exit=0,otm=0.50,slip=mid"
        result = execute_tool(
            "query_results",
            {"result_key": key, "head": 1},
            None,
            results=results,
        )
        assert "1 rows" in result.llm_summary

    def test_query_missing_key(self, stored_result):
        results, store = stored_result
        result = execute_tool(
            "query_results",
            {"result_key": "nonexistent"},
            None,
            results=results,
        )
        assert "not found" in result.llm_summary

    def test_query_filter(self, stored_result):
        results, store = stored_result
        key = "long_calls:dte=45,exit=0,otm=0.50,slip=mid"
        result = execute_tool(
            "query_results",
            {
                "result_key": key,
                "filter_column": "mean_return",
                "filter_op": "gt",
                "filter_value": "0",
            },
            None,
            results=results,
        )
        assert "1 rows" in result.llm_summary

    def test_query_columns(self, stored_result):
        results, store = stored_result
        key = "long_calls:dte=45,exit=0,otm=0.50,slip=mid"
        result = execute_tool(
            "query_results",
            {"result_key": key, "columns": ["strategy", "count"]},
            None,
            results=results,
        )
        assert "strategy" in result.llm_summary
        assert "count" in result.llm_summary


# ---------------------------------------------------------------------------
# Content fingerprint tests
# ---------------------------------------------------------------------------


class TestContentFingerprint:
    def test_same_data_same_fingerprint(self):
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        fp1 = str(pd.util.hash_pandas_object(df, index=False).sum())
        fp2 = str(pd.util.hash_pandas_object(df, index=False).sum())
        assert fp1 == fp2

    def test_different_data_different_fingerprint(self):
        df1 = pd.DataFrame({"a": [1, 2, 3]})
        df2 = pd.DataFrame({"a": [4, 5, 6]})
        fp1 = str(pd.util.hash_pandas_object(df1, index=False).sum())
        fp2 = str(pd.util.hash_pandas_object(df2, index=False).sum())
        assert fp1 != fp2
