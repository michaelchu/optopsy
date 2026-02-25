"""Fill price calculation, slippage models, and P&L computation.

This module handles all monetary calculations: converting raw bid/ask quotes
into fill prices under different slippage assumptions, applying position
multipliers (long/short direction and quantity), and computing total P&L
with percentage change.
"""

from typing import List, Optional, Tuple

import numpy as np
import pandas as pd


def _calculate_fill_price(
    bid: pd.Series,
    ask: pd.Series,
    side_value: int,
    slippage: str,
    fill_ratio: float = 0.5,
    volume: Optional[pd.Series] = None,
    reference_volume: int = 1000,
) -> pd.Series:
    """
    Calculate fill price based on slippage model.

    Args:
        bid: Series of bid prices
        ask: Series of ask prices
        side_value: 1 for long (buying), -1 for short (selling)
        slippage: Slippage mode - "mid", "spread", or "liquidity"
        fill_ratio: Base fill ratio for liquidity mode (0.0-1.0)
        volume: Optional series of volume data for liquidity-based slippage
        reference_volume: Volume threshold for "liquid" option

    Returns:
        Series of fill prices adjusted for slippage
    """
    mid = (bid + ask) / 2
    half_spread = (ask - bid) / 2

    if slippage == "mid":
        return mid

    if slippage == "spread":
        ratio = 1.0
    else:  # liquidity
        if volume is None:
            ratio = fill_ratio
        else:
            # Higher fill ratio for illiquid options
            liquidity_score = (volume.fillna(0) / reference_volume).clip(upper=1.0)
            ratio = fill_ratio + (1 - fill_ratio) * (1 - liquidity_score)

    if side_value == 1:  # long - buying at higher price
        return mid + (half_spread * ratio)
    else:  # short - selling at lower price
        return mid - (half_spread * ratio)


def _calculate_otm_pct(data: pd.DataFrame) -> pd.DataFrame:
    """Calculate out-of-the-money percentage for each option."""
    return data.assign(
        otm_pct=lambda r: round((r["strike"] - r["underlying_price"]) / r["strike"], 2)
    )


def _get_leg_quantity(leg: Tuple) -> int:
    """Get quantity for a leg, defaulting to 1 if not specified."""
    return leg[2] if len(leg) > 2 else 1


def _apply_ratios(
    data: pd.DataFrame,
    leg_def: List[Tuple],
    slippage: str = "mid",
    fill_ratio: float = 0.5,
    reference_volume: int = 1000,
) -> pd.DataFrame:
    """
    Apply position ratios (long/short multipliers) and quantities to entry and exit prices.

    When slippage is enabled, recalculates fill prices from bid/ask based on position side.
    """
    data = data.copy()
    for idx in range(1, len(leg_def) + 1):
        entry_col = f"entry_leg{idx}"
        exit_col = f"exit_leg{idx}"
        bid_entry_col = f"bid_entry_leg{idx}"
        ask_entry_col = f"ask_entry_leg{idx}"
        bid_exit_col = f"bid_exit_leg{idx}"
        ask_exit_col = f"ask_exit_leg{idx}"
        volume_col = f"volume_entry_leg{idx}"

        leg = leg_def[idx - 1]
        side_value = leg[0].value  # +1 (long/buy) or -1 (short/sell)
        quantity = _get_leg_quantity(leg)
        # Combined multiplier: direction x quantity, e.g. short 2 calls -> -2
        multiplier = side_value * quantity

        # Check if bid/ask columns exist for slippage calculation
        has_bid_ask = bid_entry_col in data.columns and ask_entry_col in data.columns

        if has_bid_ask and slippage != "mid":
            # Slippage recalculates fill prices from raw bid/ask rather than
            # using the midpoint.  Long entries fill closer to the ask (worse
            # price for buyer); short entries fill closer to the bid (worse
            # price for seller).  The degree depends on the slippage model:
            # "spread" uses the full spread; "liquidity" scales by volume.
            volume_entry = data.get(volume_col) if volume_col in data.columns else None

            # Entry: use side_value to determine buy/sell direction
            entry_fill = _calculate_fill_price(
                data[bid_entry_col],
                data[ask_entry_col],
                side_value,
                slippage,
                fill_ratio,
                volume_entry,
                reference_volume,
            )

            # Exit: reverse the side (closing the position)
            volume_exit_col = f"volume_exit_leg{idx}"
            volume_exit = (
                data.get(volume_exit_col) if volume_exit_col in data.columns else None
            )
            exit_fill = _calculate_fill_price(
                data[bid_exit_col],
                data[ask_exit_col],
                -side_value,
                slippage,
                fill_ratio,
                volume_exit,
                reference_volume,
            )

            # Apply multiplier (includes quantity)
            data[entry_col] = entry_fill * multiplier
            data[exit_col] = exit_fill * multiplier
        else:
            # Apply multiplier directly via vectorized column multiplication
            data[entry_col] = data[entry_col] * multiplier
            data[exit_col] = data[exit_col] * multiplier

    return data


def _assign_profit(
    data: pd.DataFrame,
    leg_def: List[Tuple],
    suffixes: List[str],
    slippage: str = "mid",
    fill_ratio: float = 0.5,
    reference_volume: int = 1000,
) -> pd.DataFrame:
    """Calculate total profit/loss and percentage change for multi-leg strategies."""
    data = _apply_ratios(data, leg_def, slippage, fill_ratio, reference_volume)

    # determine all entry and exit columns
    entry_cols = ["entry" + s for s in suffixes]
    exit_cols = ["exit" + s for s in suffixes]

    # calculate the total entry costs and exit proceeds
    data["total_entry_cost"] = data.loc[:, entry_cols].sum(axis=1)
    data["total_exit_proceeds"] = data.loc[:, exit_cols].sum(axis=1)

    data["pct_change"] = np.where(
        data["total_entry_cost"].abs() > 0,
        (data["total_exit_proceeds"] - data["total_entry_cost"])
        / data["total_entry_cost"].abs(),
        np.nan,
    )

    return data
