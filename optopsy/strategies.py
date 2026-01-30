from typing import Any, Dict, List, Tuple
import pandas as pd
from .core import _calls, _puts, _process_strategy
from .definitions import (
    single_strike_external_cols,
    single_strike_internal_cols,
    double_strike_external_cols,
    double_strike_internal_cols,
    straddle_internal_cols,
)
from .rules import _rule_non_overlapping_strike
from enum import Enum

default_kwargs: Dict[str, Any] = {
    "dte_interval": 7,
    "max_entry_dte": 90,
    "exit_dte": 0,
    "otm_pct_interval": 0.05,
    "max_otm_pct": 0.5,
    "min_bid_ask": 0.05,
    "drop_nan": True,
    "raw": False,
}


class Side(Enum):
    """Enum representing long or short position side with multiplier values."""

    long = 1
    short = -1


def _singles(data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Any) -> pd.DataFrame:
    """Process single-leg option strategies (calls or puts)."""
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=single_strike_internal_cols,
        external_cols=single_strike_external_cols,
        leg_def=leg_def,
        params=params,
    )


def _straddles(data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Any) -> pd.DataFrame:
    """Process straddle strategies (call and put at same strike)."""
    params = {**default_kwargs, **kwargs}

    return _process_strategy(
        data,
        internal_cols=straddle_internal_cols,
        external_cols=single_strike_external_cols,
        leg_def=leg_def,
        join_on=[
            "underlying_symbol",
            "expiration",
            "strike",
            "dte_entry",
            "dte_range",
            "otm_pct_range",
            "underlying_price_entry",
        ],
        params=params,
    )


def _strangles(data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Any) -> pd.DataFrame:
    """Process strangle strategies (call and put at different strikes)."""
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=double_strike_internal_cols,
        external_cols=double_strike_external_cols,
        leg_def=leg_def,
        rules=_rule_non_overlapping_strike,
        join_on=["underlying_symbol", "expiration", "dte_entry", "dte_range"],
        params=params,
    )


def _call_spread(
    data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Any
) -> pd.DataFrame:
    """Process call spread strategies (long and short calls at different strikes)."""
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=double_strike_internal_cols,
        external_cols=double_strike_external_cols,
        leg_def=leg_def,
        rules=_rule_non_overlapping_strike,
        join_on=["underlying_symbol", "expiration", "dte_entry", "dte_range"],
        params=params,
    )


def _put_spread(
    data: pd.DataFrame, leg_def: List[Tuple], **kwargs: Any
) -> pd.DataFrame:
    """Process put spread strategies (long and short puts at different strikes)."""
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=double_strike_internal_cols,
        external_cols=double_strike_external_cols,
        leg_def=leg_def,
        rules=_rule_non_overlapping_strike,
        join_on=["underlying_symbol", "expiration", "dte_entry", "dte_range"],
        params=params,
    )


def long_calls(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate long call strategy statistics.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters (dte_interval, max_entry_dte, etc.)

    Returns:
        DataFrame with long call strategy performance statistics
    """
    return _singles(data, [(Side.long, _calls)], **kwargs)


def long_puts(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate long put strategy statistics.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with long put strategy performance statistics
    """
    return _singles(data, [(Side.long, _puts)], **kwargs)


def short_calls(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate short call strategy statistics.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short call strategy performance statistics
    """
    return _singles(data, [(Side.short, _calls)], **kwargs)


def short_puts(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate short put strategy statistics.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short put strategy performance statistics
    """
    return _singles(data, [(Side.short, _puts)], **kwargs)


def long_straddles(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate long straddle strategy statistics (long call + long put at same strike).

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with long straddle strategy performance statistics
    """
    return _straddles(data, [(Side.long, _puts), (Side.long, _calls)], **kwargs)


def short_straddles(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate short straddle strategy statistics (short call + short put at same strike).

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short straddle strategy performance statistics
    """
    return _straddles(data, [(Side.short, _puts), (Side.short, _calls)], **kwargs)


def long_strangles(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate long strangle strategy statistics (long call + long put at different strikes).

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with long strangle strategy performance statistics
    """
    return _strangles(data, [(Side.long, _puts), (Side.long, _calls)], **kwargs)


def short_strangles(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate short strangle strategy statistics (short call + short put at different strikes).

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short strangle strategy performance statistics
    """
    return _strangles(data, [(Side.short, _puts), (Side.short, _calls)], **kwargs)


def long_call_spread(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate long call spread (bull call spread) statistics.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with long call spread strategy performance statistics
    """
    return _call_spread(data, [(Side.long, _calls), (Side.short, _calls)], **kwargs)


def short_call_spread(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate short call spread (bear call spread) statistics.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short call spread strategy performance statistics
    """
    return _call_spread(data, [(Side.short, _calls), (Side.long, _calls)], **kwargs)


def long_put_spread(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate long put spread (bear put spread) statistics.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with long put spread strategy performance statistics
    """
    return _put_spread(data, [(Side.short, _puts), (Side.long, _puts)], **kwargs)


def short_put_spread(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Generate short put spread (bull put spread) statistics.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short put spread strategy performance statistics
    """
    return _put_spread(data, [(Side.long, _puts), (Side.short, _puts)], **kwargs)
