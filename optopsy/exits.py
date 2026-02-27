"""Early exit logic (stop-loss, take-profit, and max-hold-days).

This module provides vectorized early exit detection for options strategies.
It scans intermediate quote dates between each trade's entry and planned exit
to find the first date where unrealized P&L crosses a stop-loss or take-profit
threshold, or the position has been held for ``max_hold_days`` calendar days.

The main entry point is ``_apply_early_exits()``, called from
``core._process_strategy()`` when ``stop_loss``, ``take_profit``, or
``max_hold_days`` is set.
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
    max_hold_days = params.get("max_hold_days")

    if stop_loss is None and take_profit is None and max_hold_days is None:
        return result

    if result.empty:
        result["exit_type"] = pd.Series(dtype="object")
        return result

    result = result.copy()

    if len(leg_def) == 1:
        return _apply_single_leg_exits(
            result, data, leg_def, stop_loss, take_profit, max_hold_days
        )
    else:
        return _apply_multi_leg_exits(
            result, data, leg_def, stop_loss, take_profit, max_hold_days
        )


def _apply_single_leg_exits(
    result: pd.DataFrame,
    data: pd.DataFrame,
    leg_def: List[Tuple],
    stop_loss: Optional[float],
    take_profit: Optional[float],
    max_hold_days: Optional[int] = None,
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

    # Merge entry price and entry date onto intermediates
    trade_entry = result[["_trade_id", "entry", "quote_date_entry"]].rename(
        columns={"entry": "_entry_price", "quote_date_entry": "_entry_date"}
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
    triggered = _find_first_threshold_crossing(
        intermediates, stop_loss, take_profit, max_hold_days
    )

    if not triggered.empty:
        result = _replace_exits_single_leg(result, triggered, data, side_value)

    result.drop(columns=["_trade_id"], inplace=True)
    return result


def _apply_multi_leg_exits(
    result: pd.DataFrame,
    data: pd.DataFrame,
    leg_def: List[Tuple],
    stop_loss: Optional[float],
    take_profit: Optional[float],
    max_hold_days: Optional[int] = None,
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

    # Pre-compute max_dates once for all legs
    available_cols = [c for c in contract_cols if c in data.columns]
    precomputed_max_dates = (
        data.groupby(available_cols, observed=True)["quote_date"]
        .max()
        .reset_index()
        .rename(columns={"quote_date": "_max_date"})
    )

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
            data,
            trades_lookup,
            contract_cols,
            "quote_date_entry",
            max_dates=precomputed_max_dates,
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

    # Merge entry date for max_hold_days calculation
    # Calendar strategies use plain "quote_date" as the entry date column
    entry_date_col = None
    for col in [
        "quote_date_entry",
        "quote_date_entry_leg1",
        "quote_date",
    ]:
        if col in result.columns:
            entry_date_col = col
            break
    if entry_date_col is not None:
        trade_dates = result[["_trade_id", entry_date_col]].rename(
            columns={entry_date_col: "_entry_date"}
        )
        combined = combined.merge(trade_dates, on="_trade_id")

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
    triggered = _find_first_threshold_crossing(
        combined, stop_loss, take_profit, max_hold_days
    )

    if not triggered.empty:
        result = _replace_exits_multi_leg(result, triggered, data, leg_def)

    result.drop(columns=["_trade_id"], inplace=True)
    return result


def _get_intermediate_snapshots(
    data: pd.DataFrame,
    trades: pd.DataFrame,
    contract_cols: List[str],
    entry_date_col: str,
    max_dates: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Extract intermediate quotes between entry and exit dates.

    Args:
        data: Full option chain data with all quote dates.
        trades: Trade DataFrame with _trade_id and contract columns.
        contract_cols: Columns identifying a contract (symbol, type, exp, strike).
        entry_date_col: Column name for entry date in trades.
        max_dates: Pre-computed max quote_date per contract group. When provided,
            skips the internal groupby computation. Callers processing multiple
            legs should pre-compute this once and pass it to each call.

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
    if max_dates is None:
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
    max_hold_days: Optional[int] = None,
) -> pd.DataFrame:
    """Find the first date per trade where an early-exit condition is met.

    Conditions checked (priority when multiple trigger on same date):
    1. stop_loss — unrealized P&L <= threshold
    2. take_profit — unrealized P&L >= threshold
    3. max_hold — calendar days held >= max_hold_days

    Args:
        intermediates: DataFrame with _trade_id, quote_date, _unrealized_pct,
            and optionally _entry_date (required when max_hold_days is set).
        stop_loss: Negative float threshold (e.g., -0.50).
        take_profit: Positive float threshold (e.g., 0.50).
        max_hold_days: Maximum calendar days to hold a position.

    Returns:
        DataFrame with _trade_id, quote_date, _exit_type for triggered trades.
    """
    # Build crossing mask
    mask = pd.Series(False, index=intermediates.index)

    if stop_loss is not None:
        mask = mask | (intermediates["_unrealized_pct"] <= stop_loss)
    if take_profit is not None:
        mask = mask | (intermediates["_unrealized_pct"] >= take_profit)
    if max_hold_days is not None and "_entry_date" in intermediates.columns:
        hold_duration = (
            intermediates["quote_date"] - intermediates["_entry_date"]
        ).dt.days
        mask = mask | (hold_duration >= max_hold_days)

    crossed = intermediates[mask].copy()

    if crossed.empty:
        return pd.DataFrame(columns=["_trade_id", "quote_date", "_exit_type"])

    # For each trade, take the first crossing date (chronologically)
    crossed = crossed.sort_values(["_trade_id", "quote_date"])
    first_per_trade = crossed.drop_duplicates(subset=["_trade_id"], keep="first")

    # Determine exit type — priority: stop_loss > take_profit > max_hold
    conditions = []
    choices = []
    if stop_loss is not None:
        conditions.append(first_per_trade["_unrealized_pct"] <= stop_loss)
        choices.append("stop_loss")
    if take_profit is not None:
        conditions.append(first_per_trade["_unrealized_pct"] >= take_profit)
        choices.append("take_profit")
    if max_hold_days is not None:
        conditions.append(pd.Series(True, index=first_per_trade.index))
        choices.append("max_hold")

    first_per_trade["_exit_type"] = np.select(conditions, choices, default="")

    return first_per_trade[["_trade_id", "quote_date", "_exit_type"]].reset_index(
        drop=True
    )


def _replace_exits_single_leg(
    result: pd.DataFrame,
    triggered: pd.DataFrame,
    data: pd.DataFrame,
    side_value: int,
) -> pd.DataFrame:
    """Replace exit data for triggered single-leg trades.

    Updates bid_exit, ask_exit, exit, dte_exit (if present), pct_change,
    exit_type, and _early_exit_date for each triggered trade. The planned
    exit date in quote_date_exit (if present) is not modified; the actual
    early-exit quote date is stored in _early_exit_date.
    """
    # Build lookup keys: join triggered trades with result to get contract info,
    # then merge with data to get exit prices — all vectorized.
    trig_trades = triggered[["_trade_id", "quote_date", "_exit_type"]].rename(
        columns={"quote_date": "_exit_quote_date"}
    )

    # Get contract details from result for triggered trades
    result_cols = ["_trade_id", "underlying_symbol", "expiration", "strike", "entry"]
    if "option_type" in result.columns:
        result_cols.append("option_type")

    lookup = trig_trades.merge(result[result_cols], on="_trade_id", how="inner")

    # Merge with data to get bid/ask at exit date
    data_merge_cols = ["underlying_symbol", "expiration", "strike"]
    if "option_type" in lookup.columns and "option_type" in data.columns:
        data_merge_cols.append("option_type")

    lookup = lookup.rename(columns={"_exit_quote_date": "quote_date"})
    # Deduplicate data on merge keys to avoid expanding trades
    data_exit_keys = ["quote_date"] + data_merge_cols
    data_exit = data[data_exit_keys + ["bid", "ask"]].drop_duplicates(
        subset=data_exit_keys, keep="first"
    )
    lookup = lookup.merge(
        data_exit,
        on=data_exit_keys,
        how="inner",
    )

    if lookup.empty:
        return result

    # Compute new exit prices and pct_change using known side_value
    lookup["_new_exit"] = (lookup["bid"] + lookup["ask"]) / 2
    entry_price = lookup["entry"]
    lookup["_new_pct"] = np.where(
        entry_price.abs() > 0,
        side_value * (lookup["_new_exit"] - entry_price) / entry_price.abs(),
        np.nan,
    )

    # Set result index on lookup for bulk update
    result_indexed = result.set_index("_trade_id")

    for col_name, lookup_col in [
        ("bid_exit", "bid"),
        ("ask_exit", "ask"),
    ]:
        if col_name in result.columns:
            updates = lookup.set_index("_trade_id")[lookup_col]
            result_indexed.loc[updates.index, col_name] = updates.values

    # Update exit, pct_change, exit_type, _early_exit_date
    updates = lookup.set_index("_trade_id")
    result_indexed.loc[updates.index, "exit"] = updates["_new_exit"].values
    result_indexed.loc[updates.index, "pct_change"] = updates["_new_pct"].values
    result_indexed.loc[updates.index, "exit_type"] = updates["_exit_type"].values
    result_indexed.loc[updates.index, "_early_exit_date"] = pd.to_datetime(
        updates["quote_date"]
    ).values

    if "dte_exit" in result.columns and "expiration" in result_indexed.columns:
        new_dte = (updates["expiration"] - updates["quote_date"]).dt.days
        result_indexed.loc[updates.index, "dte_exit"] = new_dte.values

    result = result_indexed.reset_index()
    return result


def _replace_exits_multi_leg(
    result: pd.DataFrame,
    triggered: pd.DataFrame,
    data: pd.DataFrame,
    leg_def: List[Tuple],
) -> pd.DataFrame:
    """Replace exit data for triggered multi-leg trades."""
    n_legs = len(leg_def)

    trig_trades = triggered[["_trade_id", "quote_date", "_exit_type"]].rename(
        columns={"quote_date": "_exit_quote_date"}
    )

    # Collect result columns needed for contract lookup
    result_cols = ["_trade_id", "underlying_symbol", "expiration"]
    for leg_idx in range(1, n_legs + 1):
        for col in [
            f"option_type_leg{leg_idx}",
            f"strike_leg{leg_idx}",
            f"entry_leg{leg_idx}",
        ]:
            if col in result.columns:
                result_cols.append(col)
    if "option_type" in result.columns:
        result_cols.append("option_type")
    if "strike" in result.columns:
        result_cols.append("strike")
    if "total_entry_cost" in result.columns:
        result_cols.append("total_entry_cost")

    lookup = trig_trades.merge(
        result[list(dict.fromkeys(result_cols))], on="_trade_id", how="inner"
    )

    if lookup.empty:
        return result

    # For each leg, merge with data to get exit bid/ask, then compute exit values
    # Track which trade_ids have all legs found
    valid_ids = set(lookup["_trade_id"].values)

    leg_updates: Dict[int, pd.DataFrame] = {}
    for leg_idx in range(1, n_legs + 1):
        leg = leg_def[leg_idx - 1]
        side_value = leg[0].value
        quantity = leg[2] if len(leg) > 2 else 1
        multiplier = side_value * quantity

        opt_type_col = f"option_type_leg{leg_idx}"
        strike_col = f"strike_leg{leg_idx}"

        # Build per-leg lookup with contract identifiers
        leg_lookup = lookup[lookup["_trade_id"].isin(valid_ids)].copy()
        leg_lookup["_strike"] = leg_lookup.get(
            strike_col, leg_lookup.get("strike", pd.Series(dtype="float64"))
        )
        leg_lookup["_opt_type"] = leg_lookup.get(
            opt_type_col, leg_lookup.get("option_type", pd.Series(dtype="object"))
        )

        # Merge with data at exit date
        leg_lookup = leg_lookup.rename(columns={"_exit_quote_date": "quote_date"})

        data_merge = data[
            ["quote_date", "underlying_symbol", "expiration", "strike", "bid", "ask"]
        ].copy()
        if "option_type" in data.columns:
            data_merge["option_type"] = data["option_type"]
            leg_lookup_merge = leg_lookup.rename(
                columns={"_strike": "strike", "_opt_type": "option_type"}
            )
            merge_cols = [
                "quote_date",
                "underlying_symbol",
                "expiration",
                "strike",
                "option_type",
            ]
        else:
            leg_lookup_merge = leg_lookup.rename(columns={"_strike": "strike"})
            merge_cols = ["quote_date", "underlying_symbol", "expiration", "strike"]

        # Deduplicate data on merge keys to avoid expanding trades
        data_merge = data_merge.drop_duplicates(subset=merge_cols, keep="first")
        merged = leg_lookup_merge.merge(
            data_merge, on=merge_cols, how="inner", suffixes=("", "_data")
        )

        # Remove trade_ids that had no data match for this leg
        bid_col_data = "bid_data" if "bid_data" in merged.columns else "bid"
        ask_col_data = "ask_data" if "ask_data" in merged.columns else "ask"

        found_ids = set(merged["_trade_id"].values)
        valid_ids &= found_ids

        merged["_new_mid"] = (merged[bid_col_data] + merged[ask_col_data]) / 2

        leg_updates[leg_idx] = (
            merged[["_trade_id", bid_col_data, ask_col_data, "_new_mid"]]
            .rename(columns={bid_col_data: "_bid", ask_col_data: "_ask"})
            .copy()
        )
        leg_updates[leg_idx]["_multiplier"] = multiplier

    if not valid_ids:
        return result

    # Apply updates to result using _trade_id index
    result_indexed = result.set_index("_trade_id")

    # Filter triggered to valid trades only
    valid_trig = trig_trades[trig_trades["_trade_id"].isin(valid_ids)].set_index(
        "_trade_id"
    )

    new_exit_totals = pd.Series(0.0, index=valid_trig.index)

    for leg_idx in range(1, n_legs + 1):
        updates = leg_updates[leg_idx]
        updates = updates[updates["_trade_id"].isin(valid_ids)].set_index("_trade_id")

        bid_col = f"bid_exit_leg{leg_idx}"
        ask_col = f"ask_exit_leg{leg_idx}"
        exit_col = f"exit_leg{leg_idx}"

        if bid_col in result_indexed.columns:
            result_indexed.loc[updates.index, bid_col] = updates["_bid"].values
        if ask_col in result_indexed.columns:
            result_indexed.loc[updates.index, ask_col] = updates["_ask"].values
        if exit_col in result_indexed.columns:
            result_indexed.loc[updates.index, exit_col] = (
                updates["_new_mid"] * updates["_multiplier"]
            ).values

        leg_exit_values = np.asarray(
            (updates["_new_mid"] * updates["_multiplier"]).values
        )
        new_exit_totals.loc[updates.index] = (
            new_exit_totals.loc[updates.index].values + leg_exit_values
        )

    # Update totals and pct_change
    if "total_entry_cost" in result_indexed.columns:
        entry_totals = result_indexed.loc[valid_trig.index, "total_entry_cost"]
    else:
        entry_cols = [f"entry_leg{i}" for i in range(1, n_legs + 1)]
        available_entry_cols = [c for c in entry_cols if c in result_indexed.columns]
        entry_totals = result_indexed.loc[valid_trig.index, available_entry_cols].sum(
            axis=1
        )

    if "total_exit_proceeds" in result_indexed.columns:
        result_indexed.loc[valid_trig.index, "total_exit_proceeds"] = (
            new_exit_totals.values
        )

    result_indexed.loc[valid_trig.index, "pct_change"] = np.where(
        entry_totals.abs() > 0,
        (np.asarray(new_exit_totals.values) - np.asarray(entry_totals.values))
        / np.asarray(entry_totals.abs().values),
        np.nan,
    )

    result_indexed.loc[valid_trig.index, "exit_type"] = valid_trig["_exit_type"].values
    result_indexed.loc[valid_trig.index, "_early_exit_date"] = pd.to_datetime(
        valid_trig["_exit_quote_date"]
    ).values

    result = result_indexed.reset_index()
    return result
