"""Data import and column normalization for option chain data.

Entry points:

- ``csv_data()`` — reads a CSV file and maps columns by integer index.
- ``options_data()`` — validates/normalizes an already-loaded DataFrame.
- ``load_cached_options()`` — reads from the parquet cache produced by
  ``optopsy-data download`` and returns a normalized DataFrame.

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


_REQUIRED_COLUMNS = [
    "underlying_symbol",
    "option_type",
    "expiration",
    "quote_date",
    "strike",
    "bid",
    "ask",
    "delta",
]


def options_data(
    df: pd.DataFrame,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """Validate and normalize an existing DataFrame for use with strategies.

    Accepts a DataFrame that already has named columns matching the standard
    optopsy schema.  Unlike ``csv_data()`` which maps columns by integer index,
    this function expects columns to already be named correctly.

    Args:
        df: DataFrame with named columns (at minimum the 8 required columns:
            underlying_symbol, option_type, expiration, quote_date, strike,
            bid, ask, delta).  Extra columns (greeks, volume, etc.) are
            passed through unchanged.
        start_date: Optional start date for filtering (inclusive).
        end_date: Optional end date for filtering (inclusive).

    Returns:
        Normalized DataFrame with date columns converted to datetime64 and
        optional date filtering applied.

    Raises:
        ValueError: If any required column is missing from the DataFrame.
    """
    missing = [col for col in _REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    return df.pipe(_infer_date_cols).pipe(_trim_dates, start_date, end_date)


def load_cached_options(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """Load cached options data downloaded by ``optopsy-data download``.

    Reads from the parquet cache and normalizes the DataFrame for use with
    strategy functions.  Requires the ``optopsy[data]`` extra (pyarrow).

    Args:
        symbol: Ticker symbol (e.g. ``"SPY"``).
        start_date: Optional start date for filtering (inclusive).
        end_date: Optional end date for filtering (inclusive).

    Returns:
        Normalized DataFrame ready for strategy functions.

    Raises:
        FileNotFoundError: If no cached data exists for *symbol*.
        ImportError: If pyarrow is not installed.
    """
    try:
        from .data.providers.cache import ParquetCache
    except ImportError as exc:
        raise ImportError(
            "pyarrow is required for load_cached_options. "
            "Install it with: pip install optopsy[data]"
        ) from exc

    cache = ParquetCache()
    df = cache.read("options", symbol)
    if df is None or df.empty:
        raise FileNotFoundError(
            f"No cached options data for '{symbol}'. "
            f"Download it first with: optopsy-data download {symbol}"
        )

    # Select columns matching _select_options_columns from EODHDProvider
    keep = [
        "underlying_symbol",
        "option_type",
        "expiration",
        "quote_date",
        "strike",
        "bid",
        "ask",
    ]
    optional = [
        "delta",
        "gamma",
        "theta",
        "vega",
        "rho",
        "implied_volatility",
        "volume",
        "open_interest",
    ]
    keep.extend([c for c in optional if c in df.columns])
    df = df[[c for c in keep if c in df.columns]]

    # Normalize option_type to lowercase single char (c/p)
    if "option_type" in df.columns:
        df = df.copy()
        df["option_type"] = (
            df["option_type"]
            .astype(str)
            .str.strip()
            .str.lower()
            .map({"call": "c", "put": "p", "c": "c", "p": "p"})
        )

    return options_data(df, start_date=start_date, end_date=end_date)


def load_cached_stocks(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """Load cached stock OHLCV data downloaded by ``optopsy-data download -s``.

    Reads from the yfinance parquet cache and returns a DataFrame suitable for
    use with ``signal_dates()`` and the signals system.
    Requires the ``optopsy[data]`` extra (pyarrow).

    Args:
        symbol: Ticker symbol (e.g. ``"SPY"``).
        start_date: Optional start date for filtering (inclusive).
        end_date: Optional end date for filtering (inclusive).

    Returns:
        DataFrame with columns ``underlying_symbol``, ``quote_date``,
        ``open``, ``high``, ``low``, ``close``, ``volume`` (where available).

    Raises:
        FileNotFoundError: If no cached stock data exists for *symbol*.
        ImportError: If pyarrow is not installed.
    """
    try:
        from .data.providers.cache import ParquetCache
    except ImportError as exc:
        raise ImportError(
            "pyarrow is required for load_cached_stocks. "
            "Install it with: pip install optopsy[data]"
        ) from exc

    cache = ParquetCache()
    df = cache.read("yf_stocks", symbol)
    if df is None or df.empty:
        raise FileNotFoundError(
            f"No cached stock data for '{symbol}'. "
            f"Download it first with: optopsy-data download {symbol} -s"
        )

    df = df.copy()

    # Rename 'date' → 'quote_date' for compatibility with signal_dates
    if "quote_date" not in df.columns and "date" in df.columns:
        df = df.rename(columns={"date": "quote_date"})

    # Ensure quote_date is datetime
    if "quote_date" in df.columns:
        df["quote_date"] = pd.to_datetime(df["quote_date"])

    # Apply date filtering on quote_date
    if start_date is not None:
        df = df[df["quote_date"] >= pd.to_datetime(start_date)]
    if end_date is not None:
        df = df[df["quote_date"] <= pd.to_datetime(end_date)]

    return df
