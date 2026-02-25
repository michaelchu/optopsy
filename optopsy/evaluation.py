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


def _match_entries_exits(
    entries: pd.DataFrame, data: pd.DataFrame, **kwargs: Any
) -> pd.DataFrame:
    """Match filtered entries with exit rows, compute midpoint prices, and select output columns.

    Shared by both OTM% and delta-targeted evaluation paths.
    """
    entry_dates = kwargs.get("entry_dates")
    exit_dates = kwargs.get("exit_dates")

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

    # Build output columns, including only those present in the result
    output_cols = [c for c in evaluated_cols if c in result.columns]
    for opt_col in (
        "delta_entry",
        "implied_volatility_entry",
        "volume_entry",
        "volume_exit",
    ):
        if opt_col in result.columns and opt_col not in output_cols:
            output_cols.append(opt_col)

    return result[output_cols]


def _evaluate_options(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Evaluate options by filtering, merging entry and exit data, and calculating costs.

    Supports two entry-selection modes:
    - OTM% path (default): filters by OTM percentage range, optionally by delta range
    - Delta targeting: selects closest-delta option per group within [min, max] range

    The mode is determined by the presence of ``delta_target`` in kwargs.
    """
    # Delta-targeted entry selection
    if "delta_target" in kwargs:
        entries = _remove_min_bid_ask(data, kwargs["min_bid_ask"])
        entries = _select_closest_delta(
            entries,
            kwargs["delta_target"],
            kwargs["delta_range_min"],
            kwargs["delta_range_max"],
        )
        return _match_entries_exits(entries, data, **kwargs)

    # OTM% entry selection (original path)
    data = data.pipe(_calculate_otm_pct).pipe(
        _trim,
        "otm_pct",
        lower=kwargs["max_otm_pct"] * -1,
        upper=kwargs["max_otm_pct"],
    )

    has_delta = "delta" in data.columns
    delta_min = kwargs.get("delta_min")
    delta_max = kwargs.get("delta_max")

    entries = _remove_min_bid_ask(data, kwargs["min_bid_ask"])

    if has_delta and (delta_min is not None or delta_max is not None):
        entries = _filter_by_delta(entries, delta_min, delta_max)

    return _match_entries_exits(entries, data, **kwargs)


def _evaluate_all_options(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Complete pipeline to evaluate all options with DTE categorization.

    Supports two modes:
    - OTM% path (default): groups by OTM percentage intervals, optionally by delta
    - Delta targeting: always groups by delta intervals (skips OTM% grouping)

    The mode is determined by the presence of ``delta_target`` in kwargs.
    """
    is_delta_targeted = "delta_target" in kwargs

    result = (
        data.pipe(_assign_dte)
        .pipe(_trim, "dte", kwargs["exit_dte"], kwargs["max_entry_dte"])
        .pipe(_evaluate_options, **kwargs)
        .pipe(_cut_options_by_dte, kwargs["dte_interval"], kwargs["max_entry_dte"])
    )

    if is_delta_targeted:
        delta_interval = kwargs.get("delta_interval") or 0.05
        result = result.pipe(_cut_options_by_delta, delta_interval)
    else:
        result = result.pipe(
            _cut_options_by_otm,
            kwargs["otm_pct_interval"],
            kwargs["max_otm_pct"],
        )
        delta_interval = kwargs.get("delta_interval")
        if delta_interval is not None:
            result = result.pipe(_cut_options_by_delta, delta_interval)

    return result


def _calls(data: pd.DataFrame) -> pd.DataFrame:
    """Filter dataframe for call options only."""
    return data[data["option_type"].str.startswith("c", na=False)]


def _puts(data: pd.DataFrame) -> pd.DataFrame:
    """Filter dataframe for put options only."""
    return data[data["option_type"].str.startswith("p", na=False)]
