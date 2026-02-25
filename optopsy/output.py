"""Output formatting for strategy results.

Provides two formatting paths — one for regular (non-calendar) strategies
and one for calendar/diagonal spreads — that either return raw trade rows
or grouped descriptive statistics with win_rate and profit_factor.
"""

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from .definitions import describe_cols


def _group_by_intervals(
    data: pd.DataFrame, cols: List[str], drop_na: bool
) -> pd.DataFrame:
    """Group options by intervals and calculate descriptive statistics.

    In addition to the standard ``describe()`` output (count, mean, std, min,
    25%, 50%, 75%, max), this also computes **win_rate** and **profit_factor**
    per group from the raw ``pct_change`` values.
    """
    # Use observed=True to only return groups with actual data (avoids pandas 3.0
    # issue where observed=False returns all category combinations as empty rows)
    grouped = data.groupby(cols, observed=True)["pct_change"]
    grouped_dataset = grouped.describe()

    # Compute win_rate and profit_factor per group using fully vectorized
    # operations.  Pre-compute boolean/masked columns once, then let
    # groupby.sum() run at C level — avoids per-group Python lambdas and
    # repeated dropna() calls.
    pct = data["pct_change"]
    _metrics = pd.DataFrame(
        {
            "_valid": pct.notna().astype(int),
            "_win": (pct > 0).astype(int),
            "_win_amt": pct.where(pct > 0, 0.0).fillna(0.0),
            "_loss_amt": pct.where(pct < 0, 0.0).fillna(0.0),
        },
        index=data.index,
    )
    for c in cols:
        _metrics[c] = data[c]
    _g = _metrics.groupby(cols, observed=True)
    valid_counts = _g["_valid"].sum()
    win_counts = _g["_win"].sum()
    gross_wins = _g["_win_amt"].sum()
    gross_losses = _g["_loss_amt"].sum()

    grouped_dataset["win_rate"] = np.where(
        valid_counts > 0, win_counts / valid_counts, np.nan
    )
    grouped_dataset["profit_factor"] = np.where(
        gross_losses != 0,
        np.abs(gross_wins / gross_losses),
        np.where(gross_wins > 0, np.inf, 0.0),
    )

    # if any non-count columns return NaN remove the row
    if drop_na:
        subset = [col for col in grouped_dataset.columns if "_count" not in col]
        grouped_dataset = grouped_dataset.dropna(subset=subset, how="all")

    return grouped_dataset


def _format_output(
    data: pd.DataFrame,
    params: Dict[str, Any],
    internal_cols: List[str],
    external_cols: List[str],
) -> pd.DataFrame:
    """
    Format strategy output as either raw data or grouped statistics.

    Args:
        data: DataFrame with strategy results
        params: Parameters including 'raw' and 'drop_nan' flags
        internal_cols: Columns to include in raw output
        external_cols: Columns to group by for statistics output

    Returns:
        Formatted DataFrame with either raw data or descriptive statistics
    """
    if params["raw"]:
        cols = internal_cols.copy()
        # Conditionally include optional columns when present in data
        for opt_col in ("implied_volatility_entry", "delta_entry"):
            if opt_col in data.columns and opt_col not in cols:
                cols.append(opt_col)
        # Include per-leg delta columns from delta-targeted path
        for leg_idx in range(1, 5):
            col = f"delta_entry_leg{leg_idx}"
            if col in data.columns and col not in cols:
                cols.append(col)
        return data[cols].reset_index(drop=True)

    return data.pipe(
        _group_by_intervals, external_cols, params["drop_nan"]
    ).reset_index()


def _format_calendar_output(
    data: pd.DataFrame,
    params: Dict[str, Any],
    internal_cols: List[str],
    external_cols: List[str],
    same_strike: bool,
) -> pd.DataFrame:
    """
    Format calendar/diagonal strategy output as either raw data or grouped statistics.

    Args:
        data: DataFrame with strategy results
        params: Parameters including 'raw' and 'drop_nan' flags
        internal_cols: Columns to include in raw output
        external_cols: Columns to group by for statistics output
        same_strike: Whether this is a calendar spread (True) or diagonal spread (False)

    Returns:
        Formatted DataFrame with either raw data or descriptive statistics
    """
    if data.empty:
        if params["raw"]:
            return pd.DataFrame(columns=internal_cols)
        return pd.DataFrame(columns=external_cols + describe_cols)

    if params["raw"]:
        # Return only the columns that exist in the data
        available_cols = [c for c in internal_cols if c in data.columns]
        return data[available_cols].reset_index(drop=True)

    # Work with a copy to avoid modifying input
    data = data.copy()

    # For aggregated output, create DTE ranges and OTM ranges
    dte_interval = params["dte_interval"]

    # Create DTE ranges for both legs
    front_dte_intervals = list(
        range(0, params["front_dte_max"] + dte_interval, dte_interval)
    )
    back_dte_intervals = list(
        range(0, params["back_dte_max"] + dte_interval, dte_interval)
    )

    data["dte_range_leg1"] = pd.cut(data["dte_entry_leg1"], front_dte_intervals)
    data["dte_range_leg2"] = pd.cut(data["dte_entry_leg2"], back_dte_intervals)

    # Create OTM ranges
    otm_pct_interval = params["otm_pct_interval"]
    max_otm_pct = params["max_otm_pct"]
    otm_pct_intervals = np.round(
        np.arange(max_otm_pct * -1, max_otm_pct, otm_pct_interval), 2
    ).tolist()

    if same_strike:
        data["otm_pct_range"] = pd.cut(data["otm_pct_leg1"], otm_pct_intervals)
    else:
        data["otm_pct_range_leg1"] = pd.cut(data["otm_pct_leg1"], otm_pct_intervals)
        data["otm_pct_range_leg2"] = pd.cut(data["otm_pct_leg2"], otm_pct_intervals)

    return data.pipe(
        _group_by_intervals, external_cols, params["drop_nan"]
    ).reset_index()
