"""Filtering primitives for option chain data.

Functions in this module apply row-level filters to DataFrames — by DTE,
OTM percentage, delta, bid/ask thresholds, and signal dates.  They are
pure functions with no side effects and no dependencies on other optopsy
modules.
"""

from typing import Any

import numpy as np
import pandas as pd


def _assign_dte(data: pd.DataFrame) -> pd.DataFrame:
    """Assign days to expiration (DTE) to the dataset."""
    return data.assign(dte=lambda r: (r["expiration"] - r["quote_date"]).dt.days)


def _trim(data: pd.DataFrame, col: str, lower: Any, upper: Any) -> pd.DataFrame:
    """Filter dataframe rows where column value is between lower and upper bounds."""
    return data.loc[(data[col] >= lower) & (data[col] <= upper)]


def _ltrim(data: pd.DataFrame, col: str, lower: Any) -> pd.DataFrame:
    """Filter dataframe rows where column value is greater than or equal to lower bound."""
    return data.loc[data[col] >= lower]


def _rtrim(data: pd.DataFrame, col: str, upper: Any) -> pd.DataFrame:
    """Filter dataframe rows where column value is less than or equal to upper bound."""
    return data.loc[data[col] <= upper]


def _get(data: pd.DataFrame, col: str, val: Any) -> pd.DataFrame:
    """Filter dataframe rows where column equals specified value."""
    return data.loc[data[col] == val]


def _remove_min_bid_ask(data: pd.DataFrame, min_bid_ask: float) -> pd.DataFrame:
    """Remove options with bid or ask prices below minimum threshold."""
    return data.loc[(data["bid"] > min_bid_ask) & (data["ask"] > min_bid_ask)]


def _remove_invalid_evaluated_options(data: pd.DataFrame) -> pd.DataFrame:
    """Keep evaluated options where entry DTE is greater than exit DTE."""
    return data.loc[
        (data["dte_exit"] <= data["dte_entry"])
        & (data["dte_entry"] != data["dte_exit"])
    ]


def _apply_signal_filter(
    data: pd.DataFrame,
    valid_dates: pd.DataFrame,
    date_col: str = "quote_date",
) -> pd.DataFrame:
    """
    Filter data to only include rows matching valid (symbol, date) pairs.

    Both the option chain data (normalized at the root of _process_strategy /
    _process_calendar_strategy) and signal dates (normalized in apply_signal)
    are already date-only, so this is a straightforward inner join.

    Args:
        data: DataFrame to filter (already date-normalized)
        valid_dates: DataFrame with (underlying_symbol, quote_date) of valid dates
            (already date-normalized via apply_signal)
        date_col: Name of the date column in data to match against (default: quote_date)

    Returns:
        Filtered DataFrame
    """
    if date_col != "quote_date":
        valid_dates = valid_dates.rename(columns={"quote_date": date_col})
    return data.merge(valid_dates, on=["underlying_symbol", date_col], how="inner")


def _select_closest_delta(
    data: pd.DataFrame, target: float, delta_min: float, delta_max: float
) -> pd.DataFrame:
    """Select the option with abs(delta) closest to target per group.

    Filters to options within [delta_min, delta_max] abs(delta) range,
    then picks the single closest-to-target row per
    (underlying_symbol, quote_date, expiration, option_type) group.
    """
    data = data.copy()
    data["_abs_delta"] = data["delta"].abs()
    data = data.loc[
        (data["_abs_delta"] >= delta_min) & (data["_abs_delta"] <= delta_max)
    ]

    if data.empty:
        return data.drop(columns=["_abs_delta"])

    data["_delta_diff"] = (data["_abs_delta"] - target).abs()
    group_cols = ["underlying_symbol", "quote_date", "expiration", "option_type"]
    result = (
        data.sort_values("_delta_diff")
        .drop_duplicates(subset=group_cols, keep="first")
        .drop(columns=["_abs_delta", "_delta_diff"])
    )
    return result


def _cut_options_by_dte(
    data: pd.DataFrame, dte_interval: int, max_entry_dte: int
) -> pd.DataFrame:
    """Categorize options into DTE intervals for grouping."""
    dte_intervals = list(range(0, max_entry_dte, dte_interval))
    data["dte_range"] = pd.cut(data["dte_entry"], dte_intervals)
    return data


def _cut_options_by_delta(data: pd.DataFrame, delta_interval: float) -> pd.DataFrame:
    """
    Categorize options into delta intervals for grouping.

    Args:
        data: DataFrame with delta_entry column
        delta_interval: Interval size for delta grouping

    Returns:
        DataFrame with delta_range column added
    """
    # Delta ranges from -1 to 1 for puts and calls
    delta_intervals = np.round(
        np.arange(-1.0, 1.0 + delta_interval, delta_interval), 2
    ).tolist()
    data["delta_range"] = pd.cut(data["delta_entry"], delta_intervals)
    return data
