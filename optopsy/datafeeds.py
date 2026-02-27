"""CSV data import and column normalization for option chain data.

The primary entry point is ``csv_data()``, which reads a CSV file and maps
its columns to the standardized names used throughout optopsy (e.g.
``underlying_symbol``, ``quote_date``, ``strike``).  Column positions are
specified by integer index, allowing the library to work with any CSV layout.

The module also handles:
- Date column inference (``_infer_date_cols``)
- Optional date-range filtering (``_trim_dates``)
- Optional Greek and liquidity columns (gamma, theta, vega, volume, etc.); delta is required
"""

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from .filters import _ltrim, _rtrim, _trim

default_kwargs: Dict[str, Any] = {
    "start_date": None,
    "end_date": None,
    "underlying_symbol": 0,
    "underlying_price": None,
    "option_type": 1,
    "expiration": 2,
    "quote_date": 3,
    "strike": 4,
    "bid": 5,
    "ask": 6,
    "delta": 7,
    # Optional Greek columns (set to column index to include)
    "gamma": None,
    "theta": None,
    "vega": None,
    "implied_volatility": None,
    # Optional liquidity columns for slippage modeling (set to column index to include)
    "volume": None,
    "open_interest": None,
}


def _trim_dates(
    data: pd.DataFrame, start_date: Optional[str], end_date: Optional[str]
) -> pd.DataFrame:
    """Filter dataframe by date range."""
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
    """Select only the columns specified in the mapping."""
    cols = [c for c, _ in column_mapping if c is not None]
    return data.iloc[:, cols]


def _standardize_cols(
    data: pd.DataFrame, column_mapping: List[Tuple[Optional[int], str]]
) -> pd.DataFrame:
    """Rename columns to standardized names."""
    idx_to_label = {idx: label for idx, label in column_mapping if idx is not None}
    sorted_indices = sorted(idx_to_label)
    idx_to_colname = dict(zip(sorted_indices, data.columns))
    cols = {
        idx_to_colname[idx]: label for idx, label in column_mapping if idx is not None
    }
    return data.rename(columns=cols)


def _infer_date_cols(data: pd.DataFrame) -> pd.DataFrame:
    """Convert date columns to datetime format."""
    data["expiration"] = pd.to_datetime(data.expiration)
    data["quote_date"] = pd.to_datetime(data.quote_date)
    return data


def csv_data(
    file_path: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    underlying_symbol: int = 0,
    underlying_price: Optional[int] = None,
    option_type: int = 1,
    expiration: int = 2,
    quote_date: int = 3,
    strike: int = 4,
    bid: int = 5,
    ask: int = 6,
    delta: int = 7,
    gamma: Optional[int] = None,
    theta: Optional[int] = None,
    vega: Optional[int] = None,
    implied_volatility: Optional[int] = None,
    volume: Optional[int] = None,
    open_interest: Optional[int] = None,
) -> pd.DataFrame:
    """
    Import option chain data from CSV files with standardized column names.

    Uses pandas DataFrame.read_csv function to import data from CSV files.
    Automatically generates standardized headers for library use.

    Args:
        file_path: Path to CSV file
        start_date: Optional start date of dataset to consider (inclusive)
        end_date: Optional end date of dataset to consider (inclusive)
        underlying_symbol: Column index containing underlying symbol
        underlying_price: Optional column index containing underlying stock price; omit (or pass ``None``) if the CSV does not include this column
        quote_date: Column index containing quote date
        expiration: Column index containing expiration date
        strike: Column index containing strike price
        option_type: Column index containing option type (call/put)
        bid: Column index containing bid price
        ask: Column index containing ask price
        delta: Column index containing delta Greek. **Required** — all strategies use per-leg delta targeting
        gamma: Optional column index containing gamma Greek
        theta: Optional column index containing theta Greek
        vega: Optional column index containing vega Greek
        implied_volatility: Optional column index containing implied volatility
        volume: Optional column index containing trading volume (used by liquidity slippage)
        open_interest: Optional column index containing open interest (reserved for future use)

    Returns:
        DataFrame with option chains and standardized column names

    Raises:
        FileNotFoundError: If CSV file doesn't exist at specified path
        ValueError: If CSV file is empty, has parsing errors, column mapping errors,
                   or other data processing issues

    """
    # Auto-detect old 9-column layout: if no column kwargs were overridden
    # (all match the new 8-column defaults) and the CSV has 9+ columns,
    # assume underlying_price lives at column 1 and shift indices up by 1.
    _new_defaults = (
        underlying_price is None
        and option_type == 1
        and expiration == 2
        and quote_date == 3
        and strike == 4
        and bid == 5
        and ask == 6
        and delta == 7
    )
    if _new_defaults:
        num_cols = len(pd.read_csv(file_path, nrows=0).columns)
        if num_cols >= 9:
            underlying_price = 1
            option_type = 2
            expiration = 3
            quote_date = 4
            strike = 5
            bid = 6
            ask = 7
            delta = 8

    params = {
        "start_date": start_date,
        "end_date": end_date,
        "underlying_symbol": underlying_symbol,
        "underlying_price": underlying_price,
        "option_type": option_type,
        "expiration": expiration,
        "quote_date": quote_date,
        "strike": strike,
        "bid": bid,
        "ask": ask,
        "delta": delta,
        "gamma": gamma,
        "theta": theta,
        "vega": vega,
        "implied_volatility": implied_volatility,
        "volume": volume,
        "open_interest": open_interest,
    }

    # Required columns
    column_mapping: List[Tuple[Optional[int], str]] = [
        (params["underlying_symbol"], "underlying_symbol"),
        (params["option_type"], "option_type"),
        (params["expiration"], "expiration"),
        (params["quote_date"], "quote_date"),
        (params["strike"], "strike"),
        (params["bid"], "bid"),
        (params["ask"], "ask"),
        (params["delta"], "delta"),
    ]

    # Add optional underlying_price and Greek columns if specified
    for col in ["underlying_price", "gamma", "theta", "vega", "implied_volatility"]:
        col_idx = params.get(col)
        if col_idx is not None:
            column_mapping.append((int(col_idx), col))

    # Add optional liquidity columns if specified
    for col in ["volume", "open_interest"]:
        col_idx = params.get(col)
        if col_idx is not None:
            column_mapping.append((int(col_idx), col))

    try:
        # Only read the columns we need from the CSV to save memory and I/O
        col_indices = sorted(c for c, _ in column_mapping if c is not None)
        return (
            pd.read_csv(file_path, usecols=col_indices)
            .pipe(_standardize_cols, column_mapping)
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
