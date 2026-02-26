"""P&L-based early exit logic (stop-loss and take-profit).

This module provides vectorized early exit detection for options strategies.
It scans intermediate quote dates between each trade's entry and planned exit
to find the first date where unrealized P&L crosses a stop-loss or take-profit
threshold.

The main entry point is ``_apply_early_exits()``, called from
``core._process_strategy()`` when ``stop_loss`` or ``take_profit`` is set.
"""

from typing import Any, Dict, List, Optional, Tuple, cast

import numpy as np
import pandas as pd


def _scalar_float(val: Any) -> float:
    """Extract a scalar float from a DataFrame.at[] value."""
    return float(cast(float, val))


def _apply_early_exits(
    result: pd.DataFrame,
    data: pd.DataFrame,
    leg_def: List[Tuple],
    params: Dict[str, Any],
) -> pd.DataFrame:
    """Apply early exit logic to strategy results.

    Dispatcher that handles both single-leg and multi-leg strategies.
    Only modifies trades where an early exit threshold is crossed.

    Args:
        result: Strategy result DataFrame from _strategy_engine / _merge_legs.
        data: Normalized option chain data with all quote dates.
        leg_def: Strategy leg definitions [(Side, filter_fn, qty), ...].
        params: Validated strategy parameters dict.

    Returns:
        Modified result DataFrame with early exits applied where triggered.
    """
    stop_loss = params.get("stop_loss")
    take_profit = params.get("take_profit")

    if stop_loss is None and take_profit is None:
        return result

    if result.empty:
        result["exit_type"] = pd.Series(dtype="object")
        return result

    result = result.copy()

    if len(leg_def) == 1:
        return _apply_single_leg_exits(result, data, leg_def, stop_loss, take_profit)
    else:
        return _apply_multi_leg_exits(result, data, leg_def, stop_loss, take_profit)


def _apply_single_leg_exits(
    result: pd.DataFrame,
    data: pd.DataFrame,
    leg_def: List[Tuple],
    stop_loss: Optional[float],
    take_profit: Optional[float],
) -> pd.DataFrame:
    """Apply early exits for single-leg strategies.

    For each trade, find intermediate quotes between entry and exit dates,
    compute unrealized P&L as a percentage, and check against thresholds.
    """
    side_value = leg_def[0][0].value  # +1 (long) or -1 (short)

    # Assign trade IDs for tracking
    result["_trade_id"] = np.arange(len(result))
    result["exit_type"] = "expiration"
    result["_early_exit_date"] = pd.NaT

    # Get intermediate snapshots
    contract_cols = ["underlying_symbol", "option_type", "expiration", "strike"]
    intermediates = _get_intermediate_snapshots(
        data, result, contract_cols, "quote_date_entry"
    )

    if intermediates.empty:
        result.drop(columns=["_trade_id"], inplace=True)
        return result

    # Merge entry price onto intermediates to compute unrealized P&L
    trade_entry = result[["_trade_id", "entry"]].rename(
        columns={"entry": "_entry_price"}
    )
    intermediates = intermediates.merge(trade_entry, on="_trade_id")

    # Compute unrealized P&L percentage
    # mid_now is the intermediate midpoint price
    intermediates["_unrealized_pct"] = np.where(
        intermediates["_entry_price"].abs() > 0,
        side_value
        * (intermediates["_mid"] - intermediates["_entry_price"])
        / intermediates["_entry_price"].abs(),
        np.nan,
    )

    # Find first threshold crossing per trade
    triggered = _find_first_threshold_crossing(intermediates, stop_loss, take_profit)

    if not triggered.empty:
        result = _replace_exits_single_leg(result, triggered, data, contract_cols)

    result.drop(columns=["_trade_id"], inplace=True)
    return result


def _apply_multi_leg_exits(
    result: pd.DataFrame,
    data: pd.DataFrame,
    leg_def: List[Tuple],
    stop_loss: Optional[float],
    take_profit: Optional[float],
) -> pd.DataFrame:
    """Apply early exits for multi-leg strategies.

    For multi-leg strategies, all legs must have quotes on the same
    intermediate date. Total unrealized P&L is computed across all legs
    before checking thresholds.
    """
    n_legs = len(leg_def)
    result["_trade_id"] = np.arange(len(result))
    result["exit_type"] = "expiration"
    result["_early_exit_date"] = pd.NaT

    # For each leg, get intermediate snapshots and compute per-leg unrealized P&L
    contract_cols = ["underlying_symbol", "option_type", "expiration", "strike"]

    # Build per-leg intermediate DataFrames
    leg_intermediates = []
    for idx in range(1, n_legs + 1):
        leg = leg_def[idx - 1]
        side_value = leg[0].value
        quantity = leg[2] if len(leg) > 2 else 1
        multiplier = side_value * quantity

        # Map leg-specific columns back to generic names for lookup
        leg_contract_cols = {
            "option_type": f"option_type_leg{idx}",
            "strike": f"strike_leg{idx}",
        }

        # Build a trades-for-lookup DataFrame with generic contract column names
        trades_lookup = result[["_trade_id", "underlying_symbol", "expiration"]].copy()

        # Handle quote_date_entry which may or may not have a leg suffix
        if f"quote_date_entry_leg{idx}" in result.columns:
            trades_lookup["quote_date_entry"] = result[f"quote_date_entry_leg{idx}"]
        elif "quote_date_entry" in result.columns:
            trades_lookup["quote_date_entry"] = result["quote_date_entry"]
        elif "quote_date_entry_leg1" in result.columns:
            trades_lookup["quote_date_entry"] = result["quote_date_entry_leg1"]

        for generic, specific in leg_contract_cols.items():
            if specific in result.columns:
                trades_lookup[generic] = result[specific]

        # For straddles, strike is shared (not suffixed)
        if "strike" not in trades_lookup.columns and "strike" in result.columns:
            trades_lookup["strike"] = result["strike"]

        intermediates = _get_intermediate_snapshots(
            data, trades_lookup, contract_cols, "quote_date_entry"
        )

        if intermediates.empty:
            result.drop(columns=["_trade_id"], inplace=True)
            return result

        # Get entry price for this leg
        entry_col = f"entry_leg{idx}"
        trade_entry = result[["_trade_id", entry_col]].rename(
            columns={entry_col: "_entry_price"}
        )
        intermediates = intermediates.merge(trade_entry, on="_trade_id")

        # Per-leg unrealized P&L contribution
        # _entry_price already has multiplier baked in (from _apply_ratios)
        intermediates["_leg_entry_cost"] = intermediates["_entry_price"]
        intermediates["_leg_exit_value"] = intermediates["_mid"] * multiplier

        leg_intermediates.append(
            intermediates[
                ["_trade_id", "quote_date", "_leg_entry_cost", "_leg_exit_value"]
            ].rename(
                columns={
                    "_leg_entry_cost": f"_leg_entry_{idx}",
                    "_leg_exit_value": f"_leg_exit_{idx}",
                }
            )
        )

    # Merge all legs on (_trade_id, quote_date) — inner join ensures all legs present
    combined = leg_intermediates[0]
    for li in leg_intermediates[1:]:
        combined = combined.merge(li, on=["_trade_id", "quote_date"], how="inner")

    if combined.empty:
        result.drop(columns=["_trade_id"], inplace=True)
        return result

    # Compute total unrealized P&L
    entry_cols = [f"_leg_entry_{i}" for i in range(1, n_legs + 1)]
    exit_cols = [f"_leg_exit_{i}" for i in range(1, n_legs + 1)]

    combined["_total_entry"] = combined[entry_cols].sum(axis=1)
    combined["_total_exit"] = combined[exit_cols].sum(axis=1)

    combined["_unrealized_pct"] = np.where(
        combined["_total_entry"].abs() > 0,
        (combined["_total_exit"] - combined["_total_entry"])
        / combined["_total_entry"].abs(),
        np.nan,
    )

    # Find first threshold crossing
    triggered = _find_first_threshold_crossing(combined, stop_loss, take_profit)

    if not triggered.empty:
        result = _replace_exits_multi_leg(
            result, triggered, data, leg_def, contract_cols
        )

    result.drop(columns=["_trade_id"], inplace=True)
    return result


def _get_intermediate_snapshots(
    data: pd.DataFrame,
    trades: pd.DataFrame,
    contract_cols: List[str],
    entry_date_col: str,
) -> pd.DataFrame:
    """Extract intermediate quotes between entry and exit dates.

    Args:
        data: Full option chain data with all quote dates.
        trades: Trade DataFrame with _trade_id and contract columns.
        contract_cols: Columns identifying a contract (symbol, type, exp, strike).
        entry_date_col: Column name for entry date in trades.

    Returns:
        DataFrame with _trade_id, quote_date, and _mid (midpoint price)
        for each intermediate date.
    """
    if trades.empty:
        return pd.DataFrame(columns=["_trade_id", "quote_date", "_mid"])

    # Get the exit date column — for evaluated options, it's the expiration
    # matched at exit_dte. We need to compute exit quote_date from the result.
    # The exit quote date is determined by looking at what quote dates exist
    # for each contract in the original data.

    # Semi-join: get all rows from data that match trade contracts
    available_cols = [c for c in contract_cols if c in trades.columns]
    if not available_cols:
        return pd.DataFrame(columns=["_trade_id", "quote_date", "_mid"])

    # Build mapping from trades to contracts
    trade_contracts = trades[["_trade_id"] + [entry_date_col] + available_cols].copy()

    # Merge data with trade contracts to find matching rows
    merged = data.merge(trade_contracts, on=available_cols, how="inner")

    if merged.empty:
        return pd.DataFrame(columns=["_trade_id", "quote_date", "_mid"])

    # Filter to dates strictly between entry and the trade's planned exit
    # Entry date comes from the trade; we need to find the exit date per trade
    # The exit is the max quote_date per contract in the original data that was used
    merged = merged[merged["quote_date"] > merged[entry_date_col]]

    # For each trade, find the planned exit date (max quote_date in the data
    # for this contract that was actually used as an exit)
    # The planned exit is the quote date at exit_dte — we can get it from the
    # original result's exit info. But we don't have that here directly.
    # Instead, get max quote_date per contract from the data as the "end" boundary.
    max_dates = (
        data.groupby(available_cols, observed=True)["quote_date"]
        .max()
        .reset_index()
        .rename(columns={"quote_date": "_max_date"})
    )
    merged = merged.merge(max_dates, on=available_cols, how="left")
    # Only keep dates strictly before the planned exit
    merged = merged[merged["quote_date"] < merged["_max_date"]]

    if merged.empty:
        return pd.DataFrame(columns=["_trade_id", "quote_date", "_mid"])

    # Compute midpoint
    merged["_mid"] = (merged["bid"] + merged["ask"]) / 2

    return merged[["_trade_id", "quote_date", "_mid"]].reset_index(drop=True)


def _find_first_threshold_crossing(
    intermediates: pd.DataFrame,
    stop_loss: Optional[float],
    take_profit: Optional[float],
) -> pd.DataFrame:
    """Find the first date per trade where unrealized P&L crosses a threshold.

    Args:
        intermediates: DataFrame with _trade_id, quote_date, _unrealized_pct.
        stop_loss: Negative float threshold (e.g., -0.50).
        take_profit: Positive float threshold (e.g., 0.50).

    Returns:
        DataFrame with _trade_id, quote_date, _exit_type for triggered trades.
    """
    # Build crossing mask
    mask = pd.Series(False, index=intermediates.index)

    if stop_loss is not None:
        mask = mask | (intermediates["_unrealized_pct"] <= stop_loss)
    if take_profit is not None:
        mask = mask | (intermediates["_unrealized_pct"] >= take_profit)

    crossed = intermediates[mask].copy()

    if crossed.empty:
        return pd.DataFrame(columns=["_trade_id", "quote_date", "_exit_type"])

    # For each trade, take the first crossing date (chronologically)
    crossed = crossed.sort_values(["_trade_id", "quote_date"])
    first_per_trade = crossed.drop_duplicates(subset=["_trade_id"], keep="first")

    # Determine exit type — if both thresholds could trigger, check which one
    # When both trigger on the same date, stop_loss takes priority (conservative)
    def _classify(row):
        pct = row["_unrealized_pct"]
        if stop_loss is not None and pct <= stop_loss:
            return "stop_loss"
        return "take_profit"

    first_per_trade["_exit_type"] = first_per_trade.apply(_classify, axis=1)

    return first_per_trade[["_trade_id", "quote_date", "_exit_type"]].reset_index(
        drop=True
    )


def _replace_exits_single_leg(
    result: pd.DataFrame,
    triggered: pd.DataFrame,
    data: pd.DataFrame,
    contract_cols: List[str],
) -> pd.DataFrame:
    """Replace exit data for triggered single-leg trades.

    Updates bid_exit, ask_exit, exit, dte_exit (if present), quote_date_exit
    (if present), pct_change, and exit_type for each triggered trade.
    """
    # For each triggered trade, look up the actual bid/ask at the exit date
    for _, trig_row in triggered.iterrows():
        trade_id = trig_row["_trade_id"]
        exit_date = trig_row["quote_date"]
        exit_type = trig_row["_exit_type"]

        trade = result.loc[result["_trade_id"] == trade_id]
        if trade.empty:
            continue

        trade_row = trade.iloc[0]

        # Look up the contract in data at the exit date
        mask = (
            (data["quote_date"] == exit_date)
            & (data["underlying_symbol"] == trade_row["underlying_symbol"])
            & (data["expiration"] == trade_row["expiration"])
            & (data["strike"] == trade_row["strike"])
        )
        if "option_type" in trade_row.index and "option_type" in data.columns:
            mask = mask & (data["option_type"] == trade_row["option_type"])

        exit_rows = data[mask]
        if exit_rows.empty:
            continue

        exit_data = exit_rows.iloc[0]
        idx = trade.index[0]

        # Update exit columns
        if "bid_exit" in result.columns:
            result.at[idx, "bid_exit"] = exit_data["bid"]
        if "ask_exit" in result.columns:
            result.at[idx, "ask_exit"] = exit_data["ask"]

        new_exit = (exit_data["bid"] + exit_data["ask"]) / 2
        result.at[idx, "exit"] = new_exit

        # Recalculate pct_change
        entry_price = _scalar_float(result.at[idx, "entry"])
        side_value = 1
        # Recover the side from the original pct_change calculation:
        # pct = side * (exit - entry) / |entry|
        if abs(entry_price) > 0:
            old_exit = _scalar_float(trade_row.get("exit", 0))
            old_pct = _scalar_float(trade_row.get("pct_change", 0))
            if abs(old_exit - entry_price) > 1e-10 and not np.isnan(old_pct):
                inferred_side = old_pct * abs(entry_price) / (old_exit - entry_price)
                side_value = 1 if inferred_side > 0 else -1
            result.at[idx, "pct_change"] = (
                side_value * (new_exit - entry_price) / abs(entry_price)
            )
        else:
            result.at[idx, "pct_change"] = np.nan

        result.at[idx, "exit_type"] = exit_type
        result.at[idx, "_early_exit_date"] = pd.Timestamp(exit_date)

        # Update DTE at exit if column exists
        if "dte_exit" in result.columns and "expiration" in trade_row.index:
            new_dte = (trade_row["expiration"] - exit_date).days
            result.at[idx, "dte_exit"] = new_dte

    return result


def _replace_exits_multi_leg(
    result: pd.DataFrame,
    triggered: pd.DataFrame,
    data: pd.DataFrame,
    leg_def: List[Tuple],
    contract_cols: List[str],
) -> pd.DataFrame:
    """Replace exit data for triggered multi-leg trades."""
    n_legs = len(leg_def)

    for _, trig_row in triggered.iterrows():
        trade_id = trig_row["_trade_id"]
        exit_date = trig_row["quote_date"]
        exit_type = trig_row["_exit_type"]

        trade = result.loc[result["_trade_id"] == trade_id]
        if trade.empty:
            continue

        trade_row = trade.iloc[0]
        idx = trade.index[0]

        all_legs_found = True
        new_entry_total = 0.0
        new_exit_total = 0.0

        for leg_idx in range(1, n_legs + 1):
            leg = leg_def[leg_idx - 1]
            side_value = leg[0].value
            quantity = leg[2] if len(leg) > 2 else 1
            multiplier = side_value * quantity

            # Get contract identifiers for this leg
            opt_type_col = f"option_type_leg{leg_idx}"
            strike_col = f"strike_leg{leg_idx}"

            opt_type = trade_row.get(opt_type_col, trade_row.get("option_type"))
            strike = trade_row.get(strike_col, trade_row.get("strike"))

            # Look up in data
            mask = (
                (data["quote_date"] == exit_date)
                & (data["underlying_symbol"] == trade_row["underlying_symbol"])
                & (data["expiration"] == trade_row["expiration"])
                & (data["strike"] == strike)
            )
            if "option_type" in data.columns and opt_type is not None:
                mask = mask & (data["option_type"] == opt_type)

            exit_rows = data[mask]
            if exit_rows.empty:
                all_legs_found = False
                break

            exit_data = exit_rows.iloc[0]
            new_mid = (exit_data["bid"] + exit_data["ask"]) / 2

            # Update per-leg exit columns
            bid_col = f"bid_exit_leg{leg_idx}"
            ask_col = f"ask_exit_leg{leg_idx}"
            exit_col = f"exit_leg{leg_idx}"

            if bid_col in result.columns:
                result.at[idx, bid_col] = exit_data["bid"]
            if ask_col in result.columns:
                result.at[idx, ask_col] = exit_data["ask"]
            if exit_col in result.columns:
                # exit_leg columns store price * multiplier
                result.at[idx, exit_col] = new_mid * multiplier

            entry_col = f"entry_leg{leg_idx}"
            if entry_col in result.columns:
                new_entry_total += _scalar_float(result.at[idx, entry_col])
            new_exit_total += new_mid * multiplier

        if not all_legs_found:
            continue

        # Update totals
        if "total_entry_cost" in result.columns:
            new_entry_total = _scalar_float(result.at[idx, "total_entry_cost"])
        result.at[idx, "total_exit_proceeds"] = new_exit_total

        # Recalculate pct_change
        if abs(new_entry_total) > 0:
            result.at[idx, "pct_change"] = (new_exit_total - new_entry_total) / abs(
                new_entry_total
            )
        else:
            result.at[idx, "pct_change"] = np.nan

        result.at[idx, "exit_type"] = exit_type
        result.at[idx, "_early_exit_date"] = pd.Timestamp(exit_date)

    return result
