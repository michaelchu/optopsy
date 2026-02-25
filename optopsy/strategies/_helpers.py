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
from typing import List, Tuple, Unpack

import pandas as pd

from ..core import _process_calendar_strategy, _process_strategy
from ..definitions import (
    calendar_spread_external_cols,
    calendar_spread_internal_cols,
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


def _butterfly(
    data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Unpack[StrategyParamsDict]
) -> pd.DataFrame:
    """Process butterfly strategies (3 legs at different strikes)."""
    kwargs.setdefault("leg1_delta", _DEFAULT_WING_DELTA)
    kwargs.setdefault("leg2_delta", _DEFAULT_ATM_DELTA)
    kwargs.setdefault("leg3_delta", _DEFAULT_WING_DELTA)
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
    data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Unpack[StrategyParamsDict]
) -> pd.DataFrame:
    """
    Process covered call strategy.

    Note: This implementation simulates a covered call using options data only,
    approximating the underlying position through the relationship between
    option premiums and underlying price changes.
    """
    kwargs.setdefault("leg1_delta", _DEFAULT_ATM_DELTA)
    kwargs.setdefault("leg2_delta", _DEFAULT_DELTA)
    return _process_strategy(
        data,
        internal_cols=double_strike_internal_cols,
        leg_def=leg_def,
        rules=_rule_non_overlapping_strike,
        join_on=["underlying_symbol", "expiration", "dte_entry", "dte_range"],
        params=kwargs,
    )


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
