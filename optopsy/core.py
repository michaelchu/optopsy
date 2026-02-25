"""Strategy execution engine for options backtesting.

This module implements the core pipeline that transforms raw option chain data
into strategy performance results. The pipeline flows through several stages:

1. **Validation** -- ``_run_checks()`` verifies parameter types and DataFrame schemas.
2. **Evaluation** -- ``_evaluate_all_options()`` filters by DTE, OTM%, bid/ask thresholds,
   and optionally delta; then merges entry and exit rows for each contract.
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
from .evaluation import _evaluate_all_options, _evaluate_all_options_by_delta
from .filters import _apply_signal_filter, _assign_dte
from .output import _format_calendar_output, _format_output
from .pricing import _assign_profit, _calculate_fill_price
from .timestamps import normalize_dates


def _rename_leg_columns(
    data: pd.DataFrame, leg_idx: int, join_on: List[str]
) -> pd.DataFrame:
    """Rename columns with leg suffix, excluding join columns."""
    rename_map = {
        col: f"{col}_leg{leg_idx}" for col in data.columns if col not in join_on
    }
    return data.rename(columns=rename_map)


def _strategy_engine(
    data: pd.DataFrame,
    leg_def: List[Tuple],
    join_on: Optional[List[str]] = None,
    rules: Optional[Callable] = None,
    slippage: str = "mid",
    fill_ratio: float = 0.5,
    reference_volume: int = 1000,
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

        data["pct_change"] = np.where(
            data["entry"].abs() > 0,
            (data["exit"] - data["entry"]) / data["entry"].abs(),
            np.nan,
        )
        return leg_def[0][1](data)

    def _rule_func(
        d: pd.DataFrame, r: Optional[Callable], ld: List[Tuple]
    ) -> pd.DataFrame:
        return d if r is None else r(d, ld)

    # Multi-leg construction:
    # 1. Filter data for each leg's option type (calls/puts) and pre-rename
    #    columns with _legN suffixes to avoid ambiguity during merges.
    # 2. Sequentially inner-join all legs on shared columns (symbol,
    #    expiration, DTE, etc.) to produce every valid leg combination.
    # 3. Apply strategy-specific rules (e.g. ascending strikes, equal wings).
    # 4. Calculate P&L across all legs with slippage adjustments.
    partials = [
        _rename_leg_columns(leg[1](data), idx, join_on or [])
        for idx, leg in enumerate(leg_def, start=1)
    ]
    suffixes = [f"_leg{idx}" for idx in range(1, len(leg_def) + 1)]

    # Merge all legs sequentially on shared columns (inner join ensures
    # only rows present in ALL legs are kept)
    result = partials[0]
    for partial in partials[1:]:
        result = pd.merge(result, partial, on=join_on, how="inner")

    return result.pipe(_rule_func, rules, leg_def).pipe(
        _assign_profit, leg_def, suffixes, slippage, fill_ratio, reference_volume
    )


def _get_leg_deltas(params: dict) -> List[Optional[dict]]:
    """Extract per-leg delta TargetRange objects from params."""
    return [params.get(f"leg{i}_delta") for i in range(1, 5)]


def _has_leg_deltas(params: dict) -> bool:
    """Check if any per-leg delta targets are set."""
    return any(d is not None for d in _get_leg_deltas(params))


def _process_strategy_delta_targeted(
    data: pd.DataFrame, params: dict, context: dict
) -> pd.DataFrame:
    """Process strategy using per-leg delta targeting.

    Each leg is evaluated independently with its own TargetRange,
    then legs are joined via _strategy_engine().
    """
    leg_def = context["leg_def"]
    leg_deltas = _get_leg_deltas(params)

    # Validate that each leg has a delta target
    active_deltas = [d for d in leg_deltas[: len(leg_def)] if d is not None]
    if len(active_deltas) != len(leg_def):
        raise ValueError(
            f"Expected {len(leg_def)} leg*_delta parameters for "
            f"{len(leg_def)}-leg strategy, got {len(active_deltas)}"
        )

    # Build join_on — strip otm_pct_range* since legs target different deltas
    join_on = context.get("join_on")
    if join_on:
        join_on = [c for c in join_on if not c.startswith("otm_pct_range")]

    # Evaluate each leg independently
    leg_results = []
    for idx, (leg, delta_target) in enumerate(
        zip(leg_def, leg_deltas[: len(leg_def)]), start=1
    ):
        option_filter = leg[1]  # _calls or _puts
        leg_data = option_filter(data)

        evaluated = _evaluate_all_options_by_delta(
            leg_data,
            dte_interval=params["dte_interval"],
            max_entry_dte=params["max_entry_dte"],
            exit_dte=params["exit_dte"],
            exit_dte_tolerance=params["exit_dte_tolerance"],
            min_bid_ask=params["min_bid_ask"],
            delta_target=delta_target["target"],
            delta_range_min=delta_target["min"],
            delta_range_max=delta_target["max"],
            delta_interval=params["delta_interval"]
            if params["delta_interval"] is not None
            else 0.05,
            entry_dates=params["entry_dates"],
            exit_dates=params["exit_dates"],
        )
        leg_results.append(evaluated)

    # Build external_cols with delta_range_legN instead of otm_pct_range*
    if len(leg_def) == 1:
        external_cols = ["dte_range", "delta_range"]
    else:
        external_cols = ["dte_range"]
        for idx in range(1, len(leg_def) + 1):
            external_cols.append(f"delta_range_leg{idx}")

    # For single-leg, use _strategy_engine directly
    if len(leg_def) == 1:
        result = _strategy_engine(
            leg_results[0],
            leg_def,
            slippage=params["slippage"],
            fill_ratio=params["fill_ratio"],
            reference_volume=params["reference_volume"],
        )
    else:
        # Rename columns per leg and merge
        if not join_on:
            join_on = ["underlying_symbol", "expiration", "dte_entry", "dte_range"]

        partials = []
        for idx, lr in enumerate(leg_results, start=1):
            renamed = _rename_leg_columns(lr, idx, join_on)
            partials.append(renamed)

        result = partials[0]
        for partial in partials[1:]:
            result = pd.merge(result, partial, on=join_on, how="inner")

        # Apply rules
        rules = context.get("rules")
        if rules is not None:
            result = rules(result, leg_def)

        # Calculate P&L
        suffixes = [f"_leg{idx}" for idx in range(1, len(leg_def) + 1)]
        result = _assign_profit(
            result,
            leg_def,
            suffixes,
            params["slippage"],
            params["fill_ratio"],
            params["reference_volume"],
        )

    return _format_output(
        result,
        params,
        context["internal_cols"],
        external_cols,
    )


def _process_strategy(data: pd.DataFrame, **context: Any) -> pd.DataFrame:
    """
    Main entry point for processing option strategies.

    Args:
        data: DataFrame containing raw option chain data
        **context: Dictionary containing strategy parameters, leg definitions, and formatting options

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

    # Branch to delta-targeted path when leg*_delta params are set
    if _has_leg_deltas(params):
        return _process_strategy_delta_targeted(data, params, context)

    # Build external_cols, adding delta_range if delta grouping is enabled
    external_cols = context["external_cols"].copy()
    if params["delta_interval"] is not None:
        external_cols = ["delta_range"] + external_cols

    return (
        _evaluate_all_options(
            data,
            dte_interval=params["dte_interval"],
            max_entry_dte=params["max_entry_dte"],
            exit_dte=params["exit_dte"],
            exit_dte_tolerance=params["exit_dte_tolerance"],
            otm_pct_interval=params["otm_pct_interval"],
            max_otm_pct=params["max_otm_pct"],
            min_bid_ask=params["min_bid_ask"],
            delta_min=params["delta_min"],
            delta_max=params["delta_max"],
            delta_interval=params["delta_interval"],
            entry_dates=params["entry_dates"],
            exit_dates=params["exit_dates"],
        )
        .pipe(
            _strategy_engine,
            context["leg_def"],
            context.get("join_on"),
            context.get("rules"),
            params["slippage"],
            params["fill_ratio"],
            params["reference_volume"],
        )
        .pipe(
            _format_output,
            params,
            context["internal_cols"],
            external_cols,
        )
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

    # Get front and back leg options
    front_options = _evaluate_calendar_options(
        data,
        params["front_dte_min"],
        params["front_dte_max"],
        max_otm_pct=params["max_otm_pct"],
        min_bid_ask=params["min_bid_ask"],
    )

    back_options = _evaluate_calendar_options(
        data,
        params["back_dte_min"],
        params["back_dte_max"],
        max_otm_pct=params["max_otm_pct"],
        min_bid_ask=params["min_bid_ask"],
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

    # Calculate P&L
    merged = _calculate_calendar_pnl(
        merged,
        leg_def,
        params["slippage"],
        params["fill_ratio"],
        params["reference_volume"],
    )

    return _fmt(merged)
