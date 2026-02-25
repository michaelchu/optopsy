"""Option evaluation pipeline — entry/exit matching and option-type filters.

This module evaluates raw option chain data by filtering candidates,
matching entry rows with corresponding exit rows, and producing a
DataFrame ready for strategy construction.  It also provides the
``_calls`` and ``_puts`` convenience filters used by ``strategies.py``.
"""

from typing import Any

import pandas as pd

from .definitions import evaluated_cols
from .filters import (
    _apply_signal_filter,
    _assign_dte,
    _cut_options_by_delta,
    _cut_options_by_dte,
    _cut_options_by_otm,
    _filter_by_delta,
    _get,
    _remove_invalid_evaluated_options,
    _remove_min_bid_ask,
    _select_closest_delta,
    _trim,
)
from .pricing import _calculate_otm_pct


def _get_exits(
    data: pd.DataFrame, exit_dte: int, exit_dte_tolerance: int = 0
) -> pd.DataFrame:
    """
    Get exit rows from option data, optionally using tolerance-based DTE matching.

    When tolerance is 0 (default), only rows with exactly the target exit_dte are
    returned. When tolerance > 0, rows within [max(0, exit_dte - tolerance),
    exit_dte + tolerance] are considered, and for each contract the row with DTE
    closest to exit_dte is selected.

    Args:
        data: DataFrame containing option data with 'dte' column
        exit_dte: Target DTE for exit
        exit_dte_tolerance: Maximum allowed deviation from exit_dte (default 0)

    Returns:
        DataFrame of exit rows
    """
    if exit_dte_tolerance == 0:
        return _get(data, "dte", exit_dte)

    lower = max(0, exit_dte - exit_dte_tolerance)
    upper = exit_dte + exit_dte_tolerance
    candidates = _trim(data, "dte", lower, upper)

    if candidates.empty:
        return candidates

    # For each contract, pick the row with DTE closest to exit_dte
    contract_cols = ["underlying_symbol", "option_type", "expiration", "strike"]
    candidates = candidates.copy()
    candidates["_dte_diff"] = (candidates["dte"] - exit_dte).abs()
    exits = (
        candidates.sort_values("_dte_diff")
        .drop_duplicates(subset=contract_cols, keep="first")
        .drop(columns=["_dte_diff"])
    )
    return exits


def _evaluate_options(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Evaluate options by filtering, merging entry and exit data, and calculating costs.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Configuration parameters including max_otm_pct, min_bid_ask, exit_dte,
                  delta_min, delta_max

    Returns:
        DataFrame with evaluated options including entry and exit prices
    """
    # trim option chains with strikes too far out from current price
    data = data.pipe(_calculate_otm_pct).pipe(
        _trim,
        "otm_pct",
        lower=kwargs["max_otm_pct"] * -1,
        upper=kwargs["max_otm_pct"],
    )

    has_delta = "delta" in data.columns
    delta_min = kwargs.get("delta_min")
    delta_max = kwargs.get("delta_max")

    # Pre-computed signal date DataFrames (from apply_signal)
    entry_dates = kwargs.get("entry_dates")
    exit_dates = kwargs.get("exit_dates")

    # remove option chains that are worthless, it's unrealistic to enter
    # trades with worthless options
    entries = _remove_min_bid_ask(data, kwargs["min_bid_ask"])

    # Apply delta filtering only to entries (not exits) - delta changes over time
    if has_delta and (delta_min is not None or delta_max is not None):
        entries = _filter_by_delta(entries, delta_min, delta_max)

    # Apply entry date filtering (only to entries, exits are unaffected)
    if entry_dates is not None:
        entries = _apply_signal_filter(entries, entry_dates)

    # to reduce unnecessary computation, filter for options with the desired exit DTE
    exits = _get_exits(data, kwargs["exit_dte"], kwargs.get("exit_dte_tolerance", 0))

    # Apply exit date filtering (only to exits, entries are unaffected)
    if exit_dates is not None:
        exits = _apply_signal_filter(exits, exit_dates)

    # Determine merge columns
    merge_cols = ["underlying_symbol", "option_type", "expiration", "strike"]

    result = (
        entries.merge(
            right=exits,
            on=merge_cols,
            suffixes=("_entry", "_exit"),
        )
        # by default we use the midpoint spread price to calculate entry and exit costs
        .assign(
            entry=lambda r: (r["bid_entry"] + r["ask_entry"]) / 2,
            exit=lambda r: (r["bid_exit"] + r["ask_exit"]) / 2,
        )
        .pipe(_remove_invalid_evaluated_options)
    )

    # Determine output columns based on whether delta is present
    output_cols = evaluated_cols.copy()
    if has_delta and "delta_entry" in result.columns:
        output_cols = output_cols + ["delta_entry"]

    # Include implied volatility if present (for IV-aware analysis)
    if "implied_volatility_entry" in result.columns:
        output_cols = output_cols + ["implied_volatility_entry"]

    # Include volume if present (for liquidity-based slippage)
    if "volume_entry" in result.columns:
        output_cols = output_cols + ["volume_entry"]
    if "volume_exit" in result.columns:
        output_cols = output_cols + ["volume_exit"]

    return result[output_cols]


def _evaluate_all_options(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Complete pipeline to evaluate all options with DTE and OTM percentage categorization.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Configuration parameters for evaluation and categorization

    Returns:
        DataFrame with evaluated and categorized options
    """
    result = (
        data.pipe(_assign_dte)
        .pipe(_trim, "dte", kwargs["exit_dte"], kwargs["max_entry_dte"])
        .pipe(_evaluate_options, **kwargs)
        .pipe(_cut_options_by_dte, kwargs["dte_interval"], kwargs["max_entry_dte"])
        .pipe(
            _cut_options_by_otm,
            kwargs["otm_pct_interval"],
            kwargs["max_otm_pct"],
        )
    )

    # Apply delta grouping if delta_interval is specified
    delta_interval = kwargs.get("delta_interval")
    if delta_interval is not None:
        result = result.pipe(_cut_options_by_delta, delta_interval)

    return result


def _evaluate_options_by_delta(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """Evaluate options using per-leg delta targeting instead of OTM% filtering.

    Selects the closest-delta option per group, then matches entry/exit rows.
    """
    target = kwargs["delta_target"]
    delta_min = kwargs["delta_range_min"]
    delta_max = kwargs["delta_range_max"]

    entry_dates = kwargs.get("entry_dates")
    exit_dates = kwargs.get("exit_dates")

    entries = _remove_min_bid_ask(data, kwargs["min_bid_ask"])
    entries = _select_closest_delta(entries, target, delta_min, delta_max)

    if entry_dates is not None:
        entries = _apply_signal_filter(entries, entry_dates)

    exits = _get_exits(data, kwargs["exit_dte"], kwargs.get("exit_dte_tolerance", 0))

    if exit_dates is not None:
        exits = _apply_signal_filter(exits, exit_dates)

    merge_cols = ["underlying_symbol", "option_type", "expiration", "strike"]

    result = (
        entries.merge(right=exits, on=merge_cols, suffixes=("_entry", "_exit"))
        .assign(
            entry=lambda r: (r["bid_entry"] + r["ask_entry"]) / 2,
            exit=lambda r: (r["bid_exit"] + r["ask_exit"]) / 2,
        )
        .pipe(_remove_invalid_evaluated_options)
    )

    # Build output columns — skip otm_pct_entry since delta path doesn't compute it
    output_cols = [c for c in evaluated_cols if c in result.columns]
    if "delta_entry" in result.columns and "delta_entry" not in output_cols:
        output_cols.append("delta_entry")
    if "implied_volatility_entry" in result.columns:
        output_cols.append("implied_volatility_entry")
    if "volume_entry" in result.columns:
        output_cols.append("volume_entry")
    if "volume_exit" in result.columns:
        output_cols.append("volume_exit")

    return result[output_cols]


def _evaluate_all_options_by_delta(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """Complete pipeline to evaluate options with delta targeting.

    Pipeline: assign DTE -> trim DTE -> evaluate by delta -> cut by DTE -> cut by delta.
    """
    delta_interval = kwargs.get("delta_interval") or 0.05

    result = (
        data.pipe(_assign_dte)
        .pipe(_trim, "dte", kwargs["exit_dte"], kwargs["max_entry_dte"])
        .pipe(_evaluate_options_by_delta, **kwargs)
        .pipe(_cut_options_by_dte, kwargs["dte_interval"], kwargs["max_entry_dte"])
        .pipe(_cut_options_by_delta, delta_interval)
    )

    return result


def _calls(data: pd.DataFrame) -> pd.DataFrame:
    """Filter dataframe for call options only."""
    return data[data["option_type"].str.startswith("c", na=False)]


def _puts(data: pd.DataFrame) -> pd.DataFrame:
    """Filter dataframe for put options only."""
    return data[data["option_type"].str.startswith("p", na=False)]
