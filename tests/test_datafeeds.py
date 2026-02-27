import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

import optopsy as op
from optopsy.datafeeds import (
    _standardize_cols,
    _trim_cols,
    load_cached_options,
    load_cached_stocks,
    options_data,
)

_TEST_DATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "test_data")


def filepath():
    return os.path.join(_TEST_DATA_DIR, "data.csv")


def filepath_noncontiguous():
    return os.path.join(_TEST_DATA_DIR, "data_noncontiguous.csv")


def filepath_with_greeks():
    return os.path.join(_TEST_DATA_DIR, "data_with_greeks.csv")


def filepath_no_underlying_price():
    return os.path.join(_TEST_DATA_DIR, "data_no_underlying_price.csv")


def filepath_empty():
    return os.path.join(_TEST_DATA_DIR, "empty.csv")


def test_import_csv_file():
    data = op.datafeeds.csv_data(
        filepath(),
        underlying_symbol=0,
        underlying_price=1,
        option_type=2,
        expiration=3,
        quote_date=4,
        strike=5,
        bid=6,
        ask=7,
        delta=8,
    )

    expected_columns = [
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
    assert list(data.columns) == expected_columns
    assert not data.empty


def test_import_csv_with_date_range():
    data = op.datafeeds.csv_data(
        filepath(),
        start_date=datetime(1990, 1, 1),
        end_date=datetime(1990, 12, 31),
        underlying_symbol=0,
        underlying_price=1,
        option_type=2,
        expiration=3,
        quote_date=4,
        strike=5,
        bid=6,
        ask=7,
        delta=8,
    )
    assert len(data) == 1
    assert data.iloc[0]["expiration"] == datetime(1990, 1, 20)


def test_import_csv_with_start_date():
    data = op.datafeeds.csv_data(
        filepath(),
        start_date=datetime(2000, 1, 1),
        underlying_symbol=0,
        underlying_price=1,
        option_type=2,
        expiration=3,
        quote_date=4,
        strike=5,
        bid=6,
        ask=7,
        delta=8,
    )
    assert len(data) == 3
    assert data.iloc[0]["expiration"] == datetime(2000, 1, 20)
    assert data.iloc[1]["expiration"] == datetime(2010, 1, 20)
    assert data.iloc[2]["expiration"] == datetime(2020, 1, 20)


def test_import_csv_with_end_date():
    data = op.datafeeds.csv_data(
        filepath(),
        end_date=datetime(2010, 1, 1),
        underlying_symbol=0,
        underlying_price=1,
        option_type=2,
        expiration=3,
        quote_date=4,
        strike=5,
        bid=6,
        ask=7,
        delta=8,
    )
    assert len(data) == 2
    assert data.iloc[0]["expiration"] == datetime(1990, 1, 20)
    assert data.iloc[1]["expiration"] == datetime(2000, 1, 20)


def test_import_csv_with_no_date_range():
    data = op.datafeeds.csv_data(
        filepath(),
        underlying_symbol=0,
        underlying_price=1,
        option_type=2,
        expiration=3,
        quote_date=4,
        strike=5,
        bid=6,
        ask=7,
        delta=8,
    )
    assert len(data) == 4
    assert data.iloc[0]["expiration"] == datetime(1990, 1, 20)
    assert data.iloc[1]["expiration"] == datetime(2000, 1, 20)
    assert data.iloc[2]["expiration"] == datetime(2010, 1, 20)
    assert data.iloc[3]["expiration"] == datetime(2020, 1, 20)


def test_import_csv_noncontiguous_columns():
    """usecols optimization must handle non-contiguous column indices (gaps)."""
    data = op.datafeeds.csv_data(
        filepath_noncontiguous(),
        underlying_symbol=0,
        underlying_price=3,
        option_type=5,
        expiration=6,
        quote_date=7,
        strike=8,
        bid=9,
        ask=10,
        delta=11,
    )

    expected_columns = [
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
    assert list(data.columns) == expected_columns
    assert len(data) == 4
    assert data.iloc[0]["underlying_symbol"] == "SPX"
    assert data.iloc[0]["underlying_price"] == 359.69
    assert data.iloc[0]["strike"] == 225
    assert data.iloc[0]["expiration"] == datetime(1990, 1, 20)


def test_import_csv_noncontiguous_columns_with_date_range():
    """Non-contiguous column mapping should work with date filtering too."""
    data = op.datafeeds.csv_data(
        filepath_noncontiguous(),
        start_date=datetime(2000, 1, 1),
        end_date=datetime(2010, 12, 31),
        underlying_symbol=0,
        underlying_price=3,
        option_type=5,
        expiration=6,
        quote_date=7,
        strike=8,
        bid=9,
        ask=10,
        delta=11,
    )
    assert len(data) == 2
    assert data.iloc[0]["expiration"] == datetime(2000, 1, 20)
    assert data.iloc[1]["expiration"] == datetime(2010, 1, 20)


# =============================================================================
# Greek Column Import Tests
# =============================================================================


def test_import_csv_with_delta_column():
    """Importing CSV with delta Greek column should include it in output."""
    data = op.datafeeds.csv_data(
        filepath_with_greeks(),
        underlying_symbol=0,
        underlying_price=1,
        option_type=2,
        expiration=3,
        quote_date=4,
        strike=5,
        bid=6,
        ask=7,
        delta=8,
    )
    assert "delta" in data.columns
    assert len(data) == 4
    assert data.iloc[0]["delta"] == 0.65


def test_import_csv_without_underlying_price_uses_defaults():
    """CSV without underlying_price column should load correctly using default column positions."""
    data = op.datafeeds.csv_data(filepath_no_underlying_price())

    assert "underlying_price" not in data.columns
    expected_columns = [
        "underlying_symbol",
        "option_type",
        "expiration",
        "quote_date",
        "strike",
        "bid",
        "ask",
        "delta",
    ]
    assert list(data.columns) == expected_columns
    assert len(data) == 4
    assert data.iloc[0]["underlying_symbol"] == "SPX"
    assert data.iloc[0]["option_type"] == "call"
    assert data.iloc[0]["strike"] == 225
    assert data.iloc[0]["bid"] == 135.5
    assert data.iloc[0]["delta"] == 0.65
    assert data.iloc[0]["expiration"] == datetime(1990, 1, 20)


def test_import_csv_with_underlying_price_explicit():
    """CSV with underlying_price column should load it when index is specified explicitly."""
    data = op.datafeeds.csv_data(
        filepath(),
        underlying_symbol=0,
        underlying_price=1,
        option_type=2,
        expiration=3,
        quote_date=4,
        strike=5,
        bid=6,
        ask=7,
        delta=8,
    )

    assert "underlying_price" in data.columns
    assert data.iloc[0]["underlying_price"] == 359.69


# =============================================================================
# Error Path Tests
# =============================================================================


def test_file_not_found_raises():
    """Non-existent file should raise FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="CSV file not found"):
        op.datafeeds.csv_data(
            "/nonexistent/path/data.csv",
            underlying_symbol=0,
            underlying_price=1,
            option_type=2,
            expiration=3,
            quote_date=4,
            strike=5,
            bid=6,
            ask=7,
        )


def test_empty_csv_raises():
    """Empty CSV file should raise ValueError."""
    with pytest.raises(ValueError, match="CSV file is empty"):
        op.datafeeds.csv_data(
            filepath_empty(),
            underlying_symbol=0,
            underlying_price=1,
            option_type=2,
            expiration=3,
            quote_date=4,
            strike=5,
            bid=6,
            ask=7,
        )


# =============================================================================
# Internal Helper Tests
# =============================================================================


class TestTrimCols:
    def test_selects_specified_columns(self):
        """_trim_cols should select only columns at the specified indices."""
        df = pd.DataFrame(
            {
                "a": [1],
                "b": [2],
                "c": [3],
                "d": [4],
                "e": [5],
            }
        )
        mapping = [(0, "sym"), (2, "type"), (4, "bid")]
        result = _trim_cols(df, mapping)
        assert list(result.columns) == ["a", "c", "e"]
        assert len(result.columns) == 3

    def test_skips_none_indices(self):
        """_trim_cols should skip entries with None index."""
        df = pd.DataFrame(
            {
                "a": [1],
                "b": [2],
                "c": [3],
            }
        )
        mapping = [(0, "sym"), (None, "delta"), (2, "type")]
        result = _trim_cols(df, mapping)
        assert list(result.columns) == ["a", "c"]
        assert len(result.columns) == 2


class TestStandardizeCols:
    def test_renames_columns_to_labels(self):
        """_standardize_cols should rename columns to standardized labels."""
        df = pd.DataFrame(
            {
                "col_a": [1],
                "col_b": [2],
                "col_c": [3],
            }
        )
        mapping = [(0, "symbol"), (1, "price"), (2, "type")]
        result = _standardize_cols(df, mapping)
        assert list(result.columns) == ["symbol", "price", "type"]

    def test_skips_none_indices(self):
        """_standardize_cols should handle None entries without error."""
        df = pd.DataFrame(
            {
                "col_a": [1],
                "col_b": [2],
            }
        )
        mapping = [(0, "symbol"), (None, "delta"), (1, "price")]
        result = _standardize_cols(df, mapping)
        assert "symbol" in result.columns
        assert "price" in result.columns
        assert "delta" not in result.columns


# =============================================================================
# options_data() Tests
# =============================================================================


def _make_options_df(**overrides):
    """Build a minimal valid options DataFrame for testing."""
    data = {
        "underlying_symbol": ["SPX"],
        "option_type": ["c"],
        "expiration": ["2020-01-17"],
        "quote_date": ["2020-01-02"],
        "strike": [3200.0],
        "bid": [50.0],
        "ask": [51.0],
        "delta": [0.45],
    }
    data.update(overrides)
    return pd.DataFrame(data)


class TestOptionsData:
    def test_valid_dataframe(self):
        """Valid DataFrame with all required columns returns normalized output."""
        df = _make_options_df()
        result = options_data(df)
        assert not result.empty
        assert pd.api.types.is_datetime64_any_dtype(result["expiration"])
        assert pd.api.types.is_datetime64_any_dtype(result["quote_date"])

    def test_missing_required_column(self):
        """Missing required column raises ValueError."""
        df = _make_options_df()
        df = df.drop(columns=["delta"])
        with pytest.raises(ValueError, match="Missing required columns.*delta"):
            options_data(df)

    def test_multiple_missing_columns(self):
        """Multiple missing columns are all reported."""
        df = _make_options_df()
        df = df.drop(columns=["delta", "bid"])
        with pytest.raises(ValueError, match="bid.*delta|delta.*bid"):
            options_data(df)

    def test_extra_columns_preserved(self):
        """Extra columns (greeks, volume, etc.) pass through unchanged."""
        df = _make_options_df(gamma=[0.02], theta=[-0.05], volume=[1000])
        result = options_data(df)
        assert "gamma" in result.columns
        assert "theta" in result.columns
        assert "volume" in result.columns
        assert result.iloc[0]["gamma"] == 0.02

    def test_date_filtering(self):
        """Date range filtering works correctly."""
        df = pd.DataFrame(
            {
                "underlying_symbol": ["SPX", "SPX", "SPX"],
                "option_type": ["c", "c", "c"],
                "expiration": ["2020-01-17", "2020-06-19", "2021-01-15"],
                "quote_date": ["2020-01-02", "2020-01-02", "2020-01-02"],
                "strike": [3200.0, 3200.0, 3200.0],
                "bid": [50.0, 50.0, 50.0],
                "ask": [51.0, 51.0, 51.0],
                "delta": [0.45, 0.45, 0.45],
            }
        )
        result = options_data(
            df,
            start_date=datetime(2020, 3, 1),
            end_date=datetime(2020, 12, 31),
        )
        assert len(result) == 1
        assert result.iloc[0]["expiration"] == pd.Timestamp("2020-06-19")

    def test_string_dates_converted(self):
        """String date columns are converted to datetime64."""
        df = _make_options_df()
        assert not pd.api.types.is_datetime64_any_dtype(df["expiration"])
        result = options_data(df)
        assert pd.api.types.is_datetime64_any_dtype(result["expiration"])
        assert pd.api.types.is_datetime64_any_dtype(result["quote_date"])

    def test_accessible_from_public_api(self):
        """options_data is accessible via op.options_data."""
        assert hasattr(op, "options_data")
        assert op.options_data is options_data


# =============================================================================
# load_cached_options() Tests
# =============================================================================


class TestLoadCachedOptions:
    def _make_cached_df(self):
        """Sample DataFrame mimicking parquet cache content."""
        return pd.DataFrame(
            {
                "underlying_symbol": ["SPY", "SPY"],
                "option_type": ["Call", "Put"],
                "expiration": pd.to_datetime(["2020-01-17", "2020-01-17"]),
                "quote_date": pd.to_datetime(["2020-01-02", "2020-01-02"]),
                "strike": [320.0, 310.0],
                "bid": [5.0, 4.0],
                "ask": [5.5, 4.5],
                "delta": [0.55, -0.40],
                "gamma": [0.03, 0.03],
                "theta": [-0.05, -0.04],
                "vega": [0.15, 0.14],
                "implied_volatility": [0.20, 0.22],
                "volume": [1000, 800],
                # Extra columns that should be excluded
                "expiration_type": ["monthly", "monthly"],
                "moneyness": ["ITM", "OTM"],
                "theoretical": [5.2, 4.3],
                "dte": [15, 15],
            }
        )

    @patch("optopsy.data.providers.cache.ParquetCache", autospec=True)
    def test_loads_and_normalizes(self, MockCache):
        """Loading cached data returns normalized DataFrame."""
        mock_instance = MagicMock()
        mock_instance.read.return_value = self._make_cached_df()
        MockCache.return_value = mock_instance

        result = load_cached_options("SPY")

        mock_instance.read.assert_called_once_with("options", "SPY")
        assert not result.empty
        assert len(result) == 2
        # option_type normalized to single char
        assert list(result["option_type"]) == ["c", "p"]
        # Extra cache columns excluded
        assert "expiration_type" not in result.columns
        assert "moneyness" not in result.columns
        assert "theoretical" not in result.columns
        assert "dte" not in result.columns
        # Greeks preserved
        assert "delta" in result.columns
        assert "gamma" in result.columns

    @patch("optopsy.data.providers.cache.ParquetCache", autospec=True)
    def test_symbol_not_cached(self, MockCache):
        """Missing symbol raises FileNotFoundError."""
        mock_instance = MagicMock()
        mock_instance.read.return_value = None
        MockCache.return_value = mock_instance

        with pytest.raises(
            FileNotFoundError, match="No cached options data for 'AAPL'"
        ):
            load_cached_options("AAPL")

    @patch("optopsy.data.providers.cache.ParquetCache", autospec=True)
    def test_date_filtering(self, MockCache):
        """Date range filtering is applied correctly."""
        cached = pd.DataFrame(
            {
                "underlying_symbol": ["SPY", "SPY", "SPY"],
                "option_type": ["c", "c", "c"],
                "expiration": pd.to_datetime(
                    ["2020-01-17", "2020-06-19", "2021-01-15"]
                ),
                "quote_date": pd.to_datetime(
                    ["2020-01-02", "2020-01-02", "2020-01-02"]
                ),
                "strike": [320.0, 320.0, 320.0],
                "bid": [5.0, 5.0, 5.0],
                "ask": [5.5, 5.5, 5.5],
                "delta": [0.55, 0.55, 0.55],
            }
        )
        mock_instance = MagicMock()
        mock_instance.read.return_value = cached
        MockCache.return_value = mock_instance

        result = load_cached_options(
            "SPY",
            start_date=datetime(2020, 3, 1),
            end_date=datetime(2020, 12, 31),
        )
        assert len(result) == 1

    @patch("optopsy.data.providers.cache.ParquetCache", autospec=True)
    def test_empty_cache_raises(self, MockCache):
        """Empty cached DataFrame raises FileNotFoundError."""
        mock_instance = MagicMock()
        mock_instance.read.return_value = pd.DataFrame()
        MockCache.return_value = mock_instance

        with pytest.raises(FileNotFoundError, match="No cached options data"):
            load_cached_options("SPY")

    def test_accessible_from_public_api(self):
        """load_cached_options is accessible via op.load_cached_options."""
        assert hasattr(op, "load_cached_options")
        assert op.load_cached_options is load_cached_options


# =============================================================================
# load_cached_stocks() Tests
# =============================================================================


class TestLoadCachedStocks:
    def _make_cached_stock_df(self):
        """Sample DataFrame mimicking yfinance parquet cache content."""
        return pd.DataFrame(
            {
                "underlying_symbol": ["SPY", "SPY", "SPY"],
                "date": pd.to_datetime(["2020-01-02", "2020-01-03", "2020-01-06"]),
                "open": [320.0, 321.0, 319.0],
                "high": [322.0, 323.0, 321.0],
                "low": [319.0, 320.0, 318.0],
                "close": [321.0, 322.0, 320.0],
                "volume": [50000000, 48000000, 52000000],
            }
        )

    @patch("optopsy.data.providers.cache.ParquetCache", autospec=True)
    def test_loads_and_renames_date(self, MockCache):
        """Loading cached stock data renames 'date' to 'quote_date'."""
        mock_instance = MagicMock()
        mock_instance.read.return_value = self._make_cached_stock_df()
        MockCache.return_value = mock_instance

        result = load_cached_stocks("SPY")

        mock_instance.read.assert_called_once_with("yf_stocks", "SPY")
        assert not result.empty
        assert len(result) == 3
        assert "quote_date" in result.columns
        assert "date" not in result.columns
        assert "close" in result.columns
        assert "high" in result.columns
        assert "volume" in result.columns

    @patch("optopsy.data.providers.cache.ParquetCache", autospec=True)
    def test_symbol_not_cached(self, MockCache):
        """Missing symbol raises FileNotFoundError."""
        mock_instance = MagicMock()
        mock_instance.read.return_value = None
        MockCache.return_value = mock_instance

        with pytest.raises(FileNotFoundError, match="No cached stock data for 'AAPL'"):
            load_cached_stocks("AAPL")

    @patch("optopsy.data.providers.cache.ParquetCache", autospec=True)
    def test_date_filtering(self, MockCache):
        """Date range filtering works on quote_date."""
        mock_instance = MagicMock()
        mock_instance.read.return_value = self._make_cached_stock_df()
        MockCache.return_value = mock_instance

        result = load_cached_stocks(
            "SPY",
            start_date=datetime(2020, 1, 3),
            end_date=datetime(2020, 1, 3),
        )
        assert len(result) == 1
        assert result.iloc[0]["close"] == 322.0

    @patch("optopsy.data.providers.cache.ParquetCache", autospec=True)
    def test_empty_cache_raises(self, MockCache):
        """Empty cached DataFrame raises FileNotFoundError."""
        mock_instance = MagicMock()
        mock_instance.read.return_value = pd.DataFrame()
        MockCache.return_value = mock_instance

        with pytest.raises(FileNotFoundError, match="No cached stock data"):
            load_cached_stocks("SPY")

    @patch("optopsy.data.providers.cache.ParquetCache", autospec=True)
    def test_quote_date_is_datetime(self, MockCache):
        """quote_date column should be datetime64."""
        mock_instance = MagicMock()
        mock_instance.read.return_value = self._make_cached_stock_df()
        MockCache.return_value = mock_instance

        result = load_cached_stocks("SPY")
        assert pd.api.types.is_datetime64_any_dtype(result["quote_date"])

    def test_accessible_from_public_api(self):
        """load_cached_stocks is accessible via op.load_cached_stocks."""
        assert hasattr(op, "load_cached_stocks")
        assert op.load_cached_stocks is load_cached_stocks
