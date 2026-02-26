"""Internal helpers for options strategy processing.

Contains the ``Side`` enum and private helper functions that assemble leg
definitions and call the core strategy engine.  These are not part of the
public API.

Parameter defaults and validation are handled by the Pydantic models in
``types.py`` (``StrategyParams``, ``CalendarStrategyParams``).  Helpers
pass raw user ``kwargs`` through to ``_process_strategy()`` /
``_process_calendar_strategy()``, which validate and apply defaults.
"""

from enum import Enum
from typing import List, Optional, Tuple, Unpack

import numpy as np
import pandas as pd

from ..core import _process_calendar_strategy, _process_strategy
from ..definitions import (
    calendar_spread_external_cols,
    calendar_spread_internal_cols,
    describe_cols,
    diagonal_spread_external_cols,
    diagonal_spread_internal_cols,
    double_strike_internal_cols,
    quadruple_strike_internal_cols,
    single_strike_internal_cols,
    straddle_internal_cols,
    triple_strike_internal_cols,
)
from ..rules import (
    _rule_butterfly_strikes,
    _rule_expiration_ordering,
    _rule_iron_butterfly_strikes,
    _rule_iron_condor_strikes,
    _rule_non_overlapping_strike,
)
from ..types import CalendarStrategyParamsDict, StrategyParamsDict


class Side(Enum):
    """Enum representing long or short position side with multiplier values."""

    long = 1
    short = -1


# ---------------------------------------------------------------------------
# Default delta TargetRange dicts for each role
# ---------------------------------------------------------------------------
_DEFAULT_DELTA = {"target": 0.30, "min": 0.20, "max": 0.40}
_DEFAULT_ATM_DELTA = {"target": 0.50, "min": 0.40, "max": 0.60}
_DEFAULT_OTM_DELTA = {"target": 0.10, "min": 0.05, "max": 0.20}
_DEFAULT_WING_DELTA = {"target": 0.20, "min": 0.10, "max": 0.30}
_DEFAULT_DEEP_ITM_DELTA = {"target": 0.80, "min": 0.60, "max": 0.95}
_DEFAULT_ITM_WING_DELTA = {"target": 0.40, "min": 0.30, "max": 0.50}
_DEFAULT_OTM_WING_DELTA = {"target": 0.10, "min": 0.05, "max": 0.20}


def _singles(
    data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Unpack[StrategyParamsDict]
) -> pd.DataFrame:
    """Process single-leg option strategies (calls or puts)."""
    kwargs.setdefault("leg1_delta", _DEFAULT_DELTA)
    return _process_strategy(
        data,
        internal_cols=single_strike_internal_cols,
        leg_def=leg_def,
        params=kwargs,
    )


def _straddles(
    data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Unpack[StrategyParamsDict]
) -> pd.DataFrame:
    """Process straddle strategies (call and put at same strike)."""
    kwargs.setdefault("leg1_delta", _DEFAULT_ATM_DELTA)
    kwargs.setdefault("leg2_delta", _DEFAULT_ATM_DELTA)
    return _process_strategy(
        data,
        internal_cols=straddle_internal_cols,
        leg_def=leg_def,
        join_on=[
            "underlying_symbol",
            "expiration",
            "strike",
            "dte_entry",
            "dte_range",
            "underlying_price_entry",
        ],
        params=kwargs,
    )


def _strangles(
    data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Unpack[StrategyParamsDict]
) -> pd.DataFrame:
    """Process strangle strategies (call and put at different strikes)."""
    kwargs.setdefault("leg1_delta", _DEFAULT_DELTA)
    kwargs.setdefault("leg2_delta", _DEFAULT_DELTA)
    return _process_strategy(
        data,
        internal_cols=double_strike_internal_cols,
        leg_def=leg_def,
        rules=_rule_non_overlapping_strike,
        join_on=["underlying_symbol", "expiration", "dte_entry", "dte_range"],
        params=kwargs,
    )


def _spread(
    data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Unpack[StrategyParamsDict]
) -> pd.DataFrame:
    """Process vertical spread strategies (call or put spreads at different strikes)."""
    kwargs.setdefault("leg1_delta", _DEFAULT_ATM_DELTA)
    kwargs.setdefault("leg2_delta", _DEFAULT_OTM_DELTA)
    return _process_strategy(
        data,
        internal_cols=double_strike_internal_cols,
        leg_def=leg_def,
        rules=_rule_non_overlapping_strike,
        join_on=["underlying_symbol", "expiration", "dte_entry", "dte_range"],
        params=kwargs,
    )


def _butterfly(
    data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Unpack[StrategyParamsDict]
) -> pd.DataFrame:
    """Process butterfly strategies (3 legs at different strikes)."""
    kwargs.setdefault("leg1_delta", _DEFAULT_ITM_WING_DELTA)
    kwargs.setdefault("leg2_delta", _DEFAULT_ATM_DELTA)
    kwargs.setdefault("leg3_delta", _DEFAULT_OTM_WING_DELTA)
    return _process_strategy(
        data,
        internal_cols=triple_strike_internal_cols,
        leg_def=leg_def,
        rules=_rule_butterfly_strikes,
        join_on=["underlying_symbol", "expiration", "dte_entry", "dte_range"],
        params=kwargs,
    )


def _iron_condor(
    data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Unpack[StrategyParamsDict]
) -> pd.DataFrame:
    """Process iron condor strategies (4 legs at different strikes)."""
    kwargs.setdefault("leg1_delta", _DEFAULT_OTM_DELTA)
    kwargs.setdefault("leg2_delta", _DEFAULT_DELTA)
    kwargs.setdefault("leg3_delta", _DEFAULT_DELTA)
    kwargs.setdefault("leg4_delta", _DEFAULT_OTM_DELTA)
    return _process_strategy(
        data,
        internal_cols=quadruple_strike_internal_cols,
        leg_def=leg_def,
        rules=_rule_iron_condor_strikes,
        join_on=["underlying_symbol", "expiration", "dte_entry", "dte_range"],
        params=kwargs,
    )


def _iron_butterfly(
    data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Unpack[StrategyParamsDict]
) -> pd.DataFrame:
    """Process iron butterfly strategies (4 legs, middle legs share strike)."""
    kwargs.setdefault("leg1_delta", _DEFAULT_OTM_DELTA)
    kwargs.setdefault("leg2_delta", _DEFAULT_ATM_DELTA)
    kwargs.setdefault("leg3_delta", _DEFAULT_ATM_DELTA)
    kwargs.setdefault("leg4_delta", _DEFAULT_OTM_DELTA)
    return _process_strategy(
        data,
        internal_cols=quadruple_strike_internal_cols,
        leg_def=leg_def,
        rules=_rule_iron_butterfly_strikes,
        join_on=["underlying_symbol", "expiration", "dte_entry", "dte_range"],
        params=kwargs,
    )


def _covered_call(
    data: pd.DataFrame,
    leg_def: List[Tuple],
    stock_data: Optional[pd.DataFrame] = None,
    **kwargs: Unpack[StrategyParamsDict],
) -> pd.DataFrame:
    """
    Process covered call strategy.

    When *stock_data* is ``None`` (default), the underlying position is
    approximated via a deep ITM call.  When a DataFrame of stock prices
    is provided, actual stock close prices are used for the underlying
    leg instead.

    Args:
        data: DataFrame containing option chain data.
        leg_def: Leg definitions – ``[(Side, filter), ...]``.
        stock_data: Optional DataFrame of stock prices.  Accepts
            ``yf.download()`` output directly; normalized internally
            via ``_normalize_stock_data()``.
        **kwargs: Strategy parameters forwarded to the processing pipeline.
    """
    if stock_data is not None:
        return _covered_with_stock(data, leg_def, stock_data, **kwargs)

    kwargs.setdefault("leg1_delta", _DEFAULT_DEEP_ITM_DELTA)
    kwargs.setdefault("leg2_delta", _DEFAULT_DELTA)
    return _process_strategy(
        data,
        internal_cols=double_strike_internal_cols,
        leg_def=leg_def,
        rules=_rule_non_overlapping_strike,
        join_on=["underlying_symbol", "expiration", "dte_entry", "dte_range"],
        params=kwargs,
    )


def _normalize_stock_data(
    stock_data: pd.DataFrame, options_data: pd.DataFrame
) -> pd.DataFrame:
    """Normalize stock data to the internal format expected by the pipeline.

    Accepts stock data from various sources (yfinance, CSV, user-provided
    DataFrames) and returns a DataFrame with columns:
    ``[underlying_symbol, quote_date, close]``.

    Normalization steps:

    1. If the index is a ``DatetimeIndex``, reset it to a column (handles
       yfinance output where dates are the index).
    2. Flatten ``MultiIndex`` columns (yfinance multi-ticker downloads).
    3. Lowercase all column names (``Close`` → ``close``).
    4. Map ``date`` → ``quote_date`` if ``quote_date`` is missing.
    5. If ``underlying_symbol`` is absent, infer it from *options_data*
       (works for single-symbol datasets, raises for multi-symbol).
    """
    from ..timestamps import normalize_dates

    df = stock_data.copy()

    # Flatten MultiIndex columns (yfinance multi-ticker downloads)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]

    # Reset DatetimeIndex to a column (yfinance uses date as index)
    if isinstance(df.index, pd.DatetimeIndex):
        df = df.reset_index()

    # Lowercase all column names
    df.columns = [c.lower() for c in df.columns]

    # Map common date column names to quote_date
    if "quote_date" not in df.columns:
        if "date" in df.columns:
            df = df.rename(columns={"date": "quote_date"})
        elif "index" in df.columns:
            df = df.rename(columns={"index": "quote_date"})

    # Infer underlying_symbol from options data if missing
    if "underlying_symbol" not in df.columns:
        symbols = options_data["underlying_symbol"].unique()
        if len(symbols) == 1:
            df["underlying_symbol"] = symbols[0]
        else:
            raise KeyError(
                "stock_data has no 'underlying_symbol' column and the options "
                "data contains multiple symbols. Please add an "
                "'underlying_symbol' column to your stock data."
            )

    # Validate required columns are present after normalization
    required = {"underlying_symbol", "quote_date", "close"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(
            f"stock_data is missing required columns after normalization: "
            f"{', '.join(sorted(missing))}. "
            f"Expected columns: underlying_symbol (or inferred), "
            f"quote_date (or date/DatetimeIndex), close."
        )

    df["quote_date"] = normalize_dates(df["quote_date"])
    return df[["underlying_symbol", "quote_date", "close"]]


def _covered_with_stock(
    data: pd.DataFrame,
    leg_def: List[Tuple],
    stock_data: pd.DataFrame,
    **kwargs: Unpack[StrategyParamsDict],
) -> pd.DataFrame:
    """Process a covered strategy using actual stock data for the underlying.

    The option leg (``leg_def[1]``) is evaluated through the normal
    single-leg pipeline.  Stock close prices are then matched by date to
    compute a combined entry cost, exit proceeds, and percentage change.
    """
    from ..checks import _run_checks
    from ..evaluation import _evaluate_all_options
    from ..output import _format_output
    from ..timestamps import normalize_dates

    # The option is always the second leg definition
    option_leg = leg_def[1]
    option_side = option_leg[0]
    option_filter = option_leg[1]

    # Only one delta target is needed (for the option leg).  The option is
    # evaluated as a single leg, so we pass its delta target via
    # ``leg1_delta`` to the single-leg pipeline.  However, for consistency
    # with the synthetic 2-leg covered/protective strategies, allow a
    # user-provided ``leg2_delta`` (which normally controls the option leg)
    # to take effect when ``leg1_delta`` is not explicitly set.
    if "leg1_delta" not in kwargs and "leg2_delta" in kwargs:
        kwargs["leg1_delta"] = kwargs["leg2_delta"]
    else:
        kwargs.setdefault("leg1_delta", _DEFAULT_DELTA)
    params = _run_checks(dict(kwargs), data)

    # --- evaluate the option leg ---
    data = data.copy()
    data["quote_date"] = normalize_dates(data["quote_date"])
    data["expiration"] = normalize_dates(data["expiration"])
    data["option_type"] = data["option_type"].str.lower()

    delta_target = params["leg1_delta"]
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

    # Stock delta is always 1.0, so delta_range_leg1 is constant and not
    # useful for grouping.  Only the option leg's delta range is included.
    external_cols = ["dte_range", "delta_range_leg2"]

    def _empty_result() -> pd.DataFrame:
        """Return a correctly shaped empty DataFrame for both raw and aggregated."""
        if params["raw"]:
            return pd.DataFrame(columns=double_strike_internal_cols)
        return pd.DataFrame(columns=external_cols + describe_cols)

    if evaluated.empty:
        return _empty_result()

    # --- match stock prices ---
    stock_prices = _normalize_stock_data(stock_data, data)

    # Entry price
    entry_map = stock_prices.rename(
        columns={"quote_date": "quote_date_entry", "close": "_stock_entry"}
    )
    result = evaluated.merge(
        entry_map, on=["underlying_symbol", "quote_date_entry"], how="inner"
    )

    # Exit price – exit date = expiration − exit_dte calendar days
    exit_dte = params["exit_dte"]
    result["_exit_date"] = result["expiration"] - pd.Timedelta(days=exit_dte)
    exit_map = stock_prices.rename(
        columns={"quote_date": "_exit_date", "close": "_stock_exit"}
    )
    result = result.merge(exit_map, on=["underlying_symbol", "_exit_date"], how="inner")

    if result.empty:
        return _empty_result()

    # --- compute combined P&L ---
    stock_entry = result["_stock_entry"]
    stock_exit = result["_stock_exit"]
    option_entry = result["entry"] * option_side.value
    option_exit = result["exit"] * option_side.value

    total_entry = stock_entry + option_entry
    total_exit = stock_exit + option_exit
    net_pnl = total_exit - total_entry

    # Apply commission if configured
    commission_obj = params.get("commission")
    total_commission = 0.0
    if commission_obj is not None:
        from ..pricing import _calculate_commission

        comm_dict = (
            commission_obj.model_dump()
            if hasattr(commission_obj, "model_dump")
            else commission_obj
        )
        # Option leg only — use leg_def[1:] (the option leg)
        option_leg_def = [leg_def[1]]
        comm_per_side = _calculate_commission(
            option_leg_def, comm_dict, has_stock_leg=True, num_shares=100
        )
        total_commission = comm_per_side * 2
        net_pnl = net_pnl - total_commission

    output = pd.DataFrame(
        {
            "underlying_symbol": result["underlying_symbol"].values,
            "underlying_price_entry_leg1": result["_stock_entry"].values,
            "expiration": result["expiration"].values,
            "dte_entry": result["dte_entry"].values,
            "option_type_leg1": "stock",
            "strike_leg1": result["_stock_entry"].values,
            "option_type_leg2": result["option_type"].values,
            "strike_leg2": result["strike"].values,
            "total_entry_cost": total_entry.values,
            "total_exit_proceeds": total_exit.values,
            "pct_change": np.where(
                total_entry.abs() > 0,
                net_pnl / total_entry.abs(),
                np.nan,
            ),
            "delta_entry_leg1": 1.0,
            "delta_entry_leg2": (
                result["delta_entry"].values
                if "delta_entry" in result.columns
                else np.nan
            ),
        }
    )

    if total_commission > 0:
        output["total_commission"] = total_commission

    # Carry over grouping columns produced by the evaluation pipeline
    if "dte_range" in result.columns:
        output["dte_range"] = result["dte_range"].values
    if "delta_range" in result.columns:
        output["delta_range_leg2"] = result["delta_range"].values

    return _format_output(output, params, double_strike_internal_cols, external_cols)


def _calendar_spread(
    data: pd.DataFrame,
    leg_def: List[Tuple],
    same_strike: bool = True,
    **kwargs: Unpack[CalendarStrategyParamsDict],
) -> pd.DataFrame:
    """
    Process calendar or diagonal spread strategies.

    Calendar spreads have the same strike but different expirations.
    Diagonal spreads have different strikes and different expirations.

    Args:
        data: DataFrame containing option chain data
        leg_def: List of tuples defining strategy legs [(side, option_filter), ...]
        same_strike: True for calendar spreads, False for diagonal spreads
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with calendar/diagonal spread strategy results
    """
    kwargs.setdefault("leg1_delta", _DEFAULT_DELTA)
    if not same_strike:
        kwargs.setdefault("leg2_delta", _DEFAULT_DELTA)

    internal_cols = (
        calendar_spread_internal_cols if same_strike else diagonal_spread_internal_cols
    )
    external_cols = (
        calendar_spread_external_cols if same_strike else diagonal_spread_external_cols
    )

    return _process_calendar_strategy(
        data,
        internal_cols=internal_cols,
        external_cols=external_cols,
        leg_def=leg_def,
        rules=_rule_expiration_ordering,
        same_strike=same_strike,
        params=kwargs,
    )
