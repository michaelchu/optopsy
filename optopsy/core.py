"""Strategy execution engine for options backtesting.

This module implements the core pipeline that transforms raw option chain data
into strategy performance results. The pipeline flows through several stages:

1. **Validation** -- ``_run_checks()`` verifies parameter types and DataFrame schemas.
2. **Evaluation** -- ``_evaluate_all_options()`` filters by DTE, delta targeting,
   and bid/ask thresholds; then merges entry and exit rows for each contract.
3. **Strategy construction** -- ``_strategy_engine()`` joins legs (single or multi-leg),
   applies strike-ordering rules, and calculates P&L with optional slippage.
4. **Output formatting** -- ``_format_output()`` returns raw trades or grouped
   descriptive statistics (with win_rate and profit_factor).

Calendar and diagonal spreads follow a parallel path via
``_process_calendar_strategy()``, which handles different expirations per leg
and a dedicated exit-price matching step.

Implementation details are split across focused submodules:

- ``filters`` -- row-level filtering primitives
- ``pricing`` -- fill price / slippage / P&L calculation
- ``evaluation`` -- entry/exit matching pipeline
- ``calendar`` -- calendar/diagonal-specific logic
- ``output`` -- result formatting and grouping
"""

from typing import Any, Callable, List, Optional, Tuple

import numpy as np
import pandas as pd

from .calendar import (
    _calculate_calendar_pnl,
    _evaluate_calendar_options,
    _find_calendar_exit_prices,
    _merge_calendar_legs,
    _prepare_calendar_leg,
)
from .checks import _run_calendar_checks, _run_checks
from .evaluation import _evaluate_all_options
from .filters import _apply_signal_filter, _assign_dte
from .output import _format_calendar_output, _format_output
from .pricing import _assign_profit, _calculate_commission, _calculate_fill_price
from .timestamps import normalize_dates


def _rename_leg_columns(
    data: pd.DataFrame, leg_idx: int, join_on: List[str]
) -> pd.DataFrame:
    """Rename columns with leg suffix, excluding join columns."""
    rename_map = {
        col: f"{col}_leg{leg_idx}" for col in data.columns if col not in join_on
    }
    return data.rename(columns=rename_map)


def _merge_legs(
    partials: List[pd.DataFrame],
    leg_def: List[Tuple],
    join_on: List[str],
    rules: Optional[Callable] = None,
    slippage: str = "mid",
    fill_ratio: float = 0.5,
    reference_volume: int = 1000,
    commission: Optional[dict] = None,
) -> pd.DataFrame:
    """Merge pre-renamed leg DataFrames, apply rules, and calculate P&L."""
    suffixes = [f"_leg{idx}" for idx in range(1, len(leg_def) + 1)]

    result = partials[0]
    for partial in partials[1:]:
        result = pd.merge(result, partial, on=join_on, how="inner")

    if rules is not None:
        result = rules(result, leg_def)

    return _assign_profit(
        result, leg_def, suffixes, slippage, fill_ratio, reference_volume, commission
    )


def _strategy_engine(
    data: pd.DataFrame,
    leg_def: List[Tuple],
    join_on: Optional[List[str]] = None,
    rules: Optional[Callable] = None,
    slippage: str = "mid",
    fill_ratio: float = 0.5,
    reference_volume: int = 1000,
    commission: Optional[dict] = None,
) -> pd.DataFrame:
    """
    Core strategy execution engine that constructs single or multi-leg option strategies.

    Args:
        data: DataFrame containing evaluated option data
        leg_def: List of tuples defining strategy legs (side, filter_function)
        join_on: Columns to join on for multi-leg strategies
        rules: Optional filtering rules to apply after joining legs
        slippage: Slippage mode - "mid", "spread", or "liquidity"
        fill_ratio: Base fill ratio for liquidity mode (0.0-1.0)
        reference_volume: Volume threshold for liquid options

    Returns:
        DataFrame with constructed strategy and calculated profit/loss
    """
    if len(leg_def) == 1:
        side = leg_def[0][0]
        has_bid_ask = "bid_entry" in data.columns and "ask_entry" in data.columns

        if has_bid_ask and slippage != "mid":
            data = data.copy()  # Avoid modifying original DataFrame
            # Calculate fill prices with slippage
            volume_entry = (
                data.get("volume_entry") if "volume_entry" in data.columns else None
            )

            data["entry"] = _calculate_fill_price(
                data["bid_entry"],
                data["ask_entry"],
                side.value,
                slippage,
                fill_ratio,
                volume_entry,
                reference_volume,
            )
            # Exit: reverse the side (closing the position)
            volume_exit = (
                data.get("volume_exit") if "volume_exit" in data.columns else None
            )
            data["exit"] = _calculate_fill_price(
                data["bid_exit"],
                data["ask_exit"],
                -side.value,
                slippage,
                fill_ratio,
                volume_exit,
                reference_volume,
            )

        net_pnl = side.value * (data["exit"] - data["entry"])

        if commission is not None:
            comm_per_side = _calculate_commission(leg_def, commission)
            data["total_commission"] = comm_per_side * 2
            net_pnl = net_pnl - data["total_commission"]

        data["pct_change"] = np.where(
            data["entry"].abs() > 0,
            net_pnl / data["entry"].abs(),
            np.nan,
        )
        return leg_def[0][1](data)

    # Filter data for each leg's option type (calls/puts) and pre-rename
    partials = [
        _rename_leg_columns(leg[1](data), idx, join_on or [])
        for idx, leg in enumerate(leg_def, start=1)
    ]

    return _merge_legs(
        partials,
        leg_def,
        join_on or [],
        rules,
        slippage,
        fill_ratio,
        reference_volume,
        commission,
    )


def _process_strategy(data: pd.DataFrame, **context: Any) -> pd.DataFrame:
    """
    Main entry point for processing option strategies.

    Each leg is evaluated independently with its own delta TargetRange,
    then legs are joined via _strategy_engine().

    Args:
        data: DataFrame containing raw option chain data
        **context: Dictionary containing strategy parameters, leg definitions,
                   and formatting options

    Returns:
        DataFrame with processed strategy results
    """
    params = _run_checks(context["params"], data)

    # Normalize date columns once at the root so all downstream merges
    # (signal filtering, entry/exit matching) work regardless of source.
    data = data.copy()
    data["quote_date"] = normalize_dates(data["quote_date"])
    data["expiration"] = normalize_dates(data["expiration"])
    # Normalize option_type once so _calls/_puts avoid repeated .str.lower() calls
    data["option_type"] = data["option_type"].str.lower()

    leg_def = context["leg_def"]
    leg_deltas = [params.get(f"leg{i}_delta") for i in range(1, 5)]

    # Validate that each leg has a delta target
    active_deltas = [d for d in leg_deltas[: len(leg_def)] if d is not None]
    if len(active_deltas) != len(leg_def):
        raise ValueError(
            f"Expected {len(leg_def)} leg*_delta parameters for "
            f"{len(leg_def)}-leg strategy, got {len(active_deltas)}"
        )

    # Build join_on from context
    join_on = context.get("join_on")

    # Evaluate each leg independently
    leg_results = []
    for leg, delta_target in zip(leg_def, leg_deltas[: len(leg_def)]):
        option_filter = leg[1]  # _calls or _puts
        leg_data = option_filter(data)

        evaluated = _evaluate_all_options(
            leg_data,
            dte_interval=params["dte_interval"],
            max_entry_dte=params["max_entry_dte"],
            exit_dte=params["exit_dte"],
            exit_dte_tolerance=params["exit_dte_tolerance"],
            min_bid_ask=params["min_bid_ask"],
            delta_target=delta_target["target"],
            delta_range_min=delta_target["min"],
            delta_range_max=delta_target["max"],
            delta_interval=params["delta_interval"],
            entry_dates=params["entry_dates"],
            exit_dates=params["exit_dates"],
        )
        leg_results.append(evaluated)

    # Build external_cols with delta_range_legN
    if len(leg_def) == 1:
        external_cols = ["dte_range", "delta_range"]
    else:
        external_cols = ["dte_range"]
        for idx in range(1, len(leg_def) + 1):
            external_cols.append(f"delta_range_leg{idx}")

    # Commission is already a plain dict after _run_checks() -> model_dump()
    commission = params.get("commission")

    # For single-leg, use _strategy_engine directly
    if len(leg_def) == 1:
        result = _strategy_engine(
            leg_results[0],
            leg_def,
            slippage=params["slippage"],
            fill_ratio=params["fill_ratio"],
            reference_volume=params["reference_volume"],
            commission=commission,
        )
    else:
        if not join_on:
            join_on = ["underlying_symbol", "expiration", "dte_entry", "dte_range"]

        partials = [
            _rename_leg_columns(lr, idx, join_on)
            for idx, lr in enumerate(leg_results, start=1)
        ]

        result = _merge_legs(
            partials,
            leg_def,
            join_on,
            context.get("rules"),
            params["slippage"],
            params["fill_ratio"],
            params["reference_volume"],
            commission,
        )

    return _format_output(
        result,
        params,
        context["internal_cols"],
        external_cols,
    )


def _process_calendar_strategy(data: pd.DataFrame, **context: Any) -> pd.DataFrame:
    """
    Process calendar/diagonal spread strategies with different expirations.

    Calendar spreads have the same strike but different expirations.
    Diagonal spreads have different strikes and different expirations.

    Args:
        data: DataFrame containing raw option chain data
        **context: Dictionary containing strategy parameters, leg definitions, and formatting options

    Returns:
        DataFrame with processed calendar/diagonal strategy results
    """
    params = _run_calendar_checks(context["params"], data)

    leg_def = context["leg_def"]
    same_strike = context.get("same_strike", True)
    rules = context.get("rules")
    internal_cols = context["internal_cols"]
    external_cols = context["external_cols"]

    # Extract per-leg delta targets
    leg1_delta = params.get("leg1_delta")
    leg2_delta = params.get("leg2_delta")

    # For calendar spreads (same strike), both legs target the same delta
    # For diagonal spreads, each leg can target a different delta
    if leg1_delta is None:
        raise ValueError("leg1_delta is required for calendar/diagonal strategies")
    if not same_strike and leg2_delta is None:
        raise ValueError("leg2_delta is required for diagonal strategies")

    def _fmt(df: pd.DataFrame) -> pd.DataFrame:
        return _format_calendar_output(
            df, params, internal_cols, external_cols, same_strike
        )

    # Work with a copy and normalize dates/option_type once at the root
    data = data.copy()
    data["quote_date"] = normalize_dates(data["quote_date"])
    data["expiration"] = normalize_dates(data["expiration"])
    data["option_type"] = data["option_type"].str.lower()
    data = _assign_dte(data)

    # Get front and back leg options with delta targeting
    front_delta = leg1_delta
    back_delta = leg2_delta if leg2_delta is not None else leg1_delta

    front_options = _evaluate_calendar_options(
        data,
        params["front_dte_min"],
        params["front_dte_max"],
        min_bid_ask=params["min_bid_ask"],
        delta_target=front_delta,
    )

    back_options = _evaluate_calendar_options(
        data,
        params["back_dte_min"],
        params["back_dte_max"],
        min_bid_ask=params["min_bid_ask"],
        delta_target=back_delta,
    )

    # Filter by option type (calls or puts) based on leg definition
    option_filter = leg_def[0][1]
    front_options = option_filter(front_options)
    back_options = option_filter(back_options)

    # Prepare and merge legs
    front_renamed = _prepare_calendar_leg(front_options, 1, same_strike)
    back_renamed = _prepare_calendar_leg(back_options, 2, same_strike)
    merged = _merge_calendar_legs(front_renamed, back_renamed, same_strike)

    # Apply expiration ordering rule
    if rules is not None:
        merged = rules(merged, leg_def)

    # Apply entry date filtering to calendar/diagonal spreads
    entry_dates = params["entry_dates"]
    if entry_dates is not None and not merged.empty:
        merged = _apply_signal_filter(merged, entry_dates)

    if merged.empty:
        return _fmt(merged)

    # Find exit prices
    merged = _find_calendar_exit_prices(
        merged,
        data,
        params["exit_dte"],
        same_strike,
        params["exit_dte_tolerance"],
    )

    if merged.empty:
        return _fmt(merged)

    # Apply exit date filtering to calendar/diagonal spreads
    exit_dates = params["exit_dates"]
    if exit_dates is not None and not merged.empty:
        merged = _apply_signal_filter(merged, exit_dates, date_col="exit_date")

    if merged.empty:
        return _fmt(merged)

    # Commission is already a plain dict after _run_calendar_checks() -> model_dump()
    cal_commission = params.get("commission")

    # Calculate P&L
    merged = _calculate_calendar_pnl(
        merged,
        leg_def,
        params["slippage"],
        params["fill_ratio"],
        params["reference_volume"],
        cal_commission,
    )

    return _fmt(merged)
