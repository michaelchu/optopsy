"""CSV data import and column standardisation for option chain data.

This module provides :func:`csv_data`, the primary way to load historical
option chain data into a pandas DataFrame with the standardised column names
that the rest of the library expects.

Expected input CSV columns (position-mapped by index):
    underlying_symbol, underlying_price, option_type, expiration,
    quote_date, strike, bid, ask.

Optional columns (Greeks and liquidity) can also be mapped by providing
their column indices.
"""

from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
from .core import _trim, _ltrim, _rtrim
from .checks import _check_data_types

default_kwargs: Dict[str, Any] = {
    "start_date": None,
    "end_date": None,
    "underlying_symbol": 0,
    "underlying_price": 1,
    "option_type": 2,
    "expiration": 3,
    "quote_date": 4,
    "strike": 5,
    "bid": 6,
    "ask": 7,
    # Optional Greek columns (set to column index to include)
    "delta": None,
    "gamma": None,
    "theta": None,
    "vega": None,
    # Optional liquidity columns for slippage modeling (set to column index to include)
    "volume": None,  # Used by liquidity-based slippage
    "open_interest": None,  # Reserved for future use
}


def _trim_dates(
    data: pd.DataFrame, start_date: Optional[str], end_date: Optional[str]
) -> pd.DataFrame:
    """Filter DataFrame rows to an optional start/end date window on the expiration column.

    Args:
        data: DataFrame with an ``expiration`` datetime column.
        start_date: Inclusive lower bound, or ``None`` for no lower bound.
        end_date: Inclusive upper bound, or ``None`` for no upper bound.

    Returns:
        Filtered DataFrame.
    """
    if start_date is not None and end_date is not None:
        return _trim(data, "expiration", start_date, end_date)
    elif start_date is None and end_date is not None:
        return _rtrim(data, "expiration", end_date)
    elif start_date is not None and end_date is None:
        return _ltrim(data, "expiration", start_date)
    else:
        return data


def _trim_cols(
    data: pd.DataFrame, column_mapping: List[Tuple[Optional[int], str]]
) -> pd.DataFrame:
    """Select only the columns whose indices appear in *column_mapping*.

    Args:
        data: Raw DataFrame from ``pd.read_csv``.
        column_mapping: List of ``(column_index, label)`` pairs.  Entries
            where the index is ``None`` (optional columns not provided by
            the user) are skipped.

    Returns:
        DataFrame with only the selected columns (by positional index).
    """
    cols = [c for c, _ in column_mapping if c is not None]
    return data.iloc[:, cols]


def _standardize_cols(
    data: pd.DataFrame, column_mapping: List[Tuple[Optional[int], str]]
) -> pd.DataFrame:
    """Rename CSV columns from their original names to the standardised names
    expected by the rest of the library (e.g. ``"bid"``, ``"ask"``).

    Args:
        data: Raw DataFrame from ``pd.read_csv``.
        column_mapping: List of ``(column_index, standard_label)`` pairs.

    Returns:
        DataFrame with renamed columns.
    """
    col_names = list(data.columns)
    cols = {col_names[idx]: label for idx, label in column_mapping if idx is not None}
    return data.rename(columns=cols)


def _infer_date_cols(data: pd.DataFrame) -> pd.DataFrame:
    """Convert ``expiration`` and ``quote_date`` columns to ``datetime64``.

    Handles both pandas < 2.0 (where ``infer_datetime_format`` improves
    performance) and pandas >= 2.0 (where strict inference is the default).
    """
    # infer_datetime_format was deprecated in pandas 2.0 and removed in 3.0
    # For pandas < 2.0, use infer_datetime_format=True for better performance
    # For pandas >= 2.0, the strict inference is now default behavior
    pandas_version = tuple(int(x) for x in pd.__version__.split(".")[:2])

    if pandas_version < (2, 0):
        data["expiration"] = pd.to_datetime(data.expiration, infer_datetime_format=True)
        data["quote_date"] = pd.to_datetime(data.quote_date, infer_datetime_format=True)
    else:
        data["expiration"] = pd.to_datetime(data.expiration)
        data["quote_date"] = pd.to_datetime(data.quote_date)
    return data


def csv_data(file_path: str, **kwargs: Any) -> pd.DataFrame:
    """
    Import option chain data from CSV files with standardized column names.

    Uses pandas DataFrame.read_csv function to import data from CSV files.
    Automatically generates standardized headers for library use.

    Args:
        file_path: Path to CSV file
        start_date: Optional start date of dataset to consider (inclusive)
        end_date: Optional end date of dataset to consider (inclusive)
        underlying_symbol: Column index containing underlying symbol
        underlying_price: Column index containing underlying stock price
        quote_date: Column index containing quote date
        expiration: Column index containing expiration date
        strike: Column index containing strike price
        option_type: Column index containing option type (call/put)
        bid: Column index containing bid price
        ask: Column index containing ask price
        delta: Optional column index containing delta Greek
        gamma: Optional column index containing gamma Greek
        theta: Optional column index containing theta Greek
        vega: Optional column index containing vega Greek
        volume: Optional column index containing trading volume (used by liquidity slippage)
        open_interest: Optional column index containing open interest (reserved for future use)

    Returns:
        DataFrame with option chains and standardized column names

    Raises:
        FileNotFoundError: If CSV file doesn't exist at specified path
        ValueError: If CSV file is empty, has parsing errors, column mapping errors,
                   or other data processing issues

    """
    params = {**default_kwargs, **kwargs}

    # Required columns
    column_mapping: List[Tuple[Optional[int], str]] = [
        (params["underlying_symbol"], "underlying_symbol"),
        (params["underlying_price"], "underlying_price"),
        (params["option_type"], "option_type"),
        (params["expiration"], "expiration"),
        (params["quote_date"], "quote_date"),
        (params["strike"], "strike"),
        (params["bid"], "bid"),
        (params["ask"], "ask"),
    ]

    # Add optional Greek columns if specified
    for greek in ["delta", "gamma", "theta", "vega"]:
        if params.get(greek) is not None:
            column_mapping.append((params[greek], greek))

    # Add optional liquidity columns if specified
    for col in ["volume", "open_interest"]:
        if params.get(col) is not None:
            column_mapping.append((params[col], col))

    try:
        return (
            pd.read_csv(file_path)
            .pipe(_standardize_cols, column_mapping)
            .pipe(_trim_cols, column_mapping)
            .pipe(_infer_date_cols)
            .pipe(_trim_dates, params["start_date"], params["end_date"])
        )
    except FileNotFoundError:
        raise FileNotFoundError(f"CSV file not found at path: {file_path}")
    except pd.errors.EmptyDataError:
        raise ValueError(f"CSV file is empty: {file_path}")
    except pd.errors.ParserError as e:
        raise ValueError(f"Error parsing CSV file {file_path}: {str(e)}")
    except (IndexError, KeyError) as e:
        raise ValueError(f"Column mapping error in {file_path}: {str(e)}")
    except Exception as e:
        raise ValueError(f"Unexpected error reading CSV file {file_path}: {str(e)}")
