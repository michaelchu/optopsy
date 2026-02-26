import os
from datetime import datetime

import pandas as pd
import pytest

import optopsy as op
from optopsy.datafeeds import _standardize_cols, _trim_cols

_TEST_DATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "test_data")


def filepath():
    return os.path.join(_TEST_DATA_DIR, "data.csv")


def filepath_noncontiguous():
    return os.path.join(_TEST_DATA_DIR, "data_noncontiguous.csv")


def filepath_with_greeks():
    return os.path.join(_TEST_DATA_DIR, "data_with_greeks.csv")


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
