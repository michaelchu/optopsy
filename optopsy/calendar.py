"""Calendar and diagonal spread evaluation, leg preparation, and exit matching.

Calendar spreads involve options with the same strike but different
expirations; diagonal spreads allow different strikes as well.  This
module handles the specialised pipeline that differs from the regular
strategy path: per-leg DTE filtering, two-leg merging with independent
expirations, exit-price lookup keyed on the front-leg expiration, and
calendar-specific P&L calculation.
"""

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .filters import _remove_min_bid_ask, _select_closest_delta, _trim
from .pricing import _calculate_fill_price


def _evaluate_calendar_options(
    data: pd.DataFrame, dte_min: int, dte_max: int, **kwargs: Any
) -> pd.DataFrame:
    """
    Evaluate options for a single leg of a calendar/diagonal spread.

    Args:
        data: DataFrame containing option chain data with DTE assigned
        dte_min: Minimum DTE for this leg
        dte_max: Maximum DTE for this leg
        **kwargs: Additional parameters including min_bid_ask, delta_target

    Returns:
        DataFrame with evaluated options for this leg
    """
    # Filter by DTE range for this leg
    leg_data = _trim(data, "dte", dte_min, dte_max)

    # Remove options with bid/ask below minimum
    leg_data = _remove_min_bid_ask(leg_data, kwargs["min_bid_ask"])

    # Apply delta targeting
    dt = kwargs["delta_target"]
    leg_data = _select_closest_delta(leg_data, dt["target"], dt["min"], dt["max"])

    return leg_data


def _get_strike_column(same_strike: bool, leg_num: int) -> str:
    """Return the appropriate strike column name based on spread type."""
    return "strike" if same_strike else f"strike_leg{leg_num}"


def _prepare_calendar_leg(
    options: pd.DataFrame, leg_num: int, same_strike: bool
) -> pd.DataFrame:
    """
    Rename columns for a calendar/diagonal spread leg.

    Args:
        options: DataFrame with option data for this leg
        leg_num: Leg number (1 for front, 2 for back)
        same_strike: True for calendar spreads, False for diagonal

    Returns:
        DataFrame with renamed columns
    """
    strike_col = _get_strike_column(same_strike, leg_num)
    price_col = "underlying_price_entry" if leg_num == 1 else "underlying_price_back"

    return options.rename(
        columns={
            "expiration": f"expiration_leg{leg_num}",
            "dte": f"dte_entry_leg{leg_num}",
            "strike": strike_col,
            "bid": f"bid_leg{leg_num}",
            "ask": f"ask_leg{leg_num}",
            "delta": f"delta_leg{leg_num}",
            "underlying_price": price_col,
        }
    )


def _get_calendar_leg_columns(leg_num: int, same_strike: bool) -> List[str]:
    """Return the columns needed for a calendar spread leg."""
    strike_col = _get_strike_column(same_strike, leg_num)
    cols = [
        "underlying_symbol",
        "quote_date",
        "option_type",
        f"expiration_leg{leg_num}",
        f"dte_entry_leg{leg_num}",
        f"bid_leg{leg_num}",
        f"ask_leg{leg_num}",
        f"delta_leg{leg_num}",
    ]
    if leg_num == 1:
        cols.append("underlying_price_entry")
    cols.append(strike_col)
    return cols


def _merge_calendar_legs(
    front: pd.DataFrame, back: pd.DataFrame, same_strike: bool
) -> pd.DataFrame:
    """
    Merge front and back legs of a calendar/diagonal spread.

    Args:
        front: DataFrame with front leg data
        back: DataFrame with back leg data
        same_strike: True for calendar spreads, False for diagonal

    Returns:
        Merged DataFrame
    """
    join_cols = ["underlying_symbol", "quote_date", "option_type"]
    if same_strike:
        join_cols.append("strike")

    front_cols = _get_calendar_leg_columns(1, same_strike)
    back_cols = _get_calendar_leg_columns(2, same_strike)

    return pd.merge(front[front_cols], back[back_cols], on=join_cols, how="inner")


def _get_exit_leg_subset(
    exit_data: pd.DataFrame, leg_num: int, same_strike: bool
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Prepare exit data for joining with a specific leg.

    Args:
        exit_data: DataFrame with exit date prices
        leg_num: Leg number (1 or 2)
        same_strike: True for calendar spreads, False for diagonal

    Returns:
        Tuple of (subset DataFrame, join columns)
    """
    strike_col = _get_strike_column(same_strike, leg_num)

    renamed = exit_data.rename(
        columns={
            "quote_date": "exit_date",
            "expiration": f"expiration_leg{leg_num}",
            "bid": f"exit_bid_leg{leg_num}",
            "ask": f"exit_ask_leg{leg_num}",
        }
    )

    if not same_strike:
        renamed = renamed.rename(columns={"strike": strike_col})

    join_cols = [
        "underlying_symbol",
        "exit_date",
        "option_type",
        f"expiration_leg{leg_num}",
        strike_col,
    ]

    subset_cols = join_cols + [f"exit_bid_leg{leg_num}", f"exit_ask_leg{leg_num}"]

    return renamed[subset_cols], join_cols


def _find_calendar_exit_prices(
    merged: pd.DataFrame,
    data: pd.DataFrame,
    exit_dte: int,
    same_strike: bool,
    exit_dte_tolerance: int = 0,
) -> pd.DataFrame:
    """
    Find exit prices for calendar/diagonal spread positions.

    Args:
        merged: DataFrame with merged entry positions
        data: Original DataFrame with all option data (with DTE assigned)
        exit_dte: Days before front expiration to exit
        same_strike: True for calendar spreads, False for diagonal
        exit_dte_tolerance: Maximum days of deviation from target exit date (default 0)

    Returns:
        DataFrame with exit prices merged in, or empty DataFrame if no exit data
    """
    # Calculate exit date for each position.
    # Exit is timed relative to front leg (leg1) expiration, which is standard
    # calendar spread management: close before the short-dated option expires.
    # Both expiration and quote_date are already date-normalized at the root.
    merged["exit_date"] = merged["expiration_leg1"] - pd.Timedelta(days=exit_dte)

    all_exit_dates = merged["exit_date"].unique()

    if exit_dte_tolerance == 0:
        # Exact date matching (original behavior)
        exit_data = data[data["quote_date"].isin(all_exit_dates)]
    else:
        # Tolerance-based matching: snap each target exit_date to the
        # closest available quote_date within tolerance using vectorized
        # searchsorted instead of a Python loop.
        tolerance_td = np.timedelta64(exit_dte_tolerance, "D")
        available_dates = np.sort(data["quote_date"].unique())

        if len(available_dates) == 0:
            return merged.iloc[:0]

        targets = np.asarray(all_exit_dates, dtype=available_dates.dtype)

        # searchsorted finds the insertion point; check both neighbors
        # to find the closest available date for each target.
        idx = np.searchsorted(available_dates, targets, side="left")
        idx = np.clip(idx, 0, len(available_dates) - 1)

        # Compare left and right neighbors to find the nearest
        left = np.clip(idx - 1, 0, len(available_dates) - 1)
        right = np.clip(idx, 0, len(available_dates) - 1)
        diff_left = np.abs(available_dates[left] - targets)
        diff_right = np.abs(available_dates[right] - targets)
        nearest_idx = np.where(diff_left <= diff_right, left, right)
        nearest_dates = available_dates[nearest_idx]
        nearest_diffs = np.abs(nearest_dates - targets)

        # Build mapping only for targets within tolerance
        within = nearest_diffs <= tolerance_td
        date_map = dict(zip(targets[within], nearest_dates[within]))

        if not date_map:
            return merged.iloc[:0]

        merged["exit_date"] = (
            merged["exit_date"].map(date_map).fillna(merged["exit_date"])
        )
        exit_data = data[data["quote_date"].isin(date_map.values())]

    if exit_data.empty:
        return merged.iloc[:0]

    # Merge exit prices for each leg
    for leg_num in [1, 2]:
        exit_subset, join_cols = _get_exit_leg_subset(exit_data, leg_num, same_strike)
        merged = pd.merge(merged, exit_subset, on=join_cols, how="inner")
        if merged.empty:
            return merged

    return merged


def _calculate_calendar_pnl(
    merged: pd.DataFrame,
    leg_def: List[Tuple],
    slippage: str = "mid",
    fill_ratio: float = 0.5,
    reference_volume: int = 1000,
    commission: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame:
    """
    Calculate P&L for calendar/diagonal spread positions.

    Args:
        merged: DataFrame with entry and exit prices
        leg_def: List of tuples defining strategy legs
        slippage: Slippage mode - "mid", "spread", or "liquidity"
        fill_ratio: Base fill ratio for liquidity mode (0.0-1.0)
        reference_volume: Volume threshold for liquid options

    Returns:
        DataFrame with P&L columns added
    """
    front_side = leg_def[0][0].value
    back_side = leg_def[1][0].value

    # Calculate entry prices based on slippage model
    volume_leg1 = merged.get("volume_leg1") if "volume_leg1" in merged.columns else None
    volume_leg2 = merged.get("volume_leg2") if "volume_leg2" in merged.columns else None

    merged["entry_leg1"] = _calculate_fill_price(
        merged["bid_leg1"],
        merged["ask_leg1"],
        front_side,
        slippage,
        fill_ratio,
        volume_leg1,
        reference_volume,
    )
    merged["entry_leg2"] = _calculate_fill_price(
        merged["bid_leg2"],
        merged["ask_leg2"],
        back_side,
        slippage,
        fill_ratio,
        volume_leg2,
        reference_volume,
    )

    # Calculate exit prices (reverse sides for closing positions)
    # Note: Exit volume is not currently tracked for calendar spreads since exit
    # data comes from a different quote date. For liquidity mode, exits use
    # the base fill_ratio without volume adjustment.
    merged["exit_leg1"] = _calculate_fill_price(
        merged["exit_bid_leg1"],
        merged["exit_ask_leg1"],
        -front_side,
        slippage,
        fill_ratio,
        None,
        reference_volume,
    )
    merged["exit_leg2"] = _calculate_fill_price(
        merged["exit_bid_leg2"],
        merged["exit_ask_leg2"],
        -back_side,
        slippage,
        fill_ratio,
        None,
        reference_volume,
    )

    # Apply position multipliers based on leg definition
    front_multiplier = front_side
    back_multiplier = back_side

    merged["entry_leg1"] = merged["entry_leg1"] * front_multiplier
    merged["exit_leg1"] = merged["exit_leg1"] * front_multiplier
    merged["entry_leg2"] = merged["entry_leg2"] * back_multiplier
    merged["exit_leg2"] = merged["exit_leg2"] * back_multiplier

    # Calculate totals
    merged["total_entry_cost"] = merged["entry_leg1"] + merged["entry_leg2"]
    merged["total_exit_proceeds"] = merged["exit_leg1"] + merged["exit_leg2"]

    net_pnl = merged["total_exit_proceeds"] - merged["total_entry_cost"]

    if commission is not None:
        from .pricing import _calculate_commission

        comm_per_side = _calculate_commission(leg_def, commission)
        merged["total_commission"] = comm_per_side * 2
        net_pnl = net_pnl - merged["total_commission"]

    # Calculate percentage change.
    # Use a minimum threshold to avoid misleading percentages from near-zero entries.
    min_entry_threshold = 0.01
    merged["pct_change"] = np.where(
        merged["total_entry_cost"].abs() >= min_entry_threshold,
        net_pnl / merged["total_entry_cost"].abs(),
        np.nan,
    )

    return merged
