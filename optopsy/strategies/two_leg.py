"""Two-leg option strategies: straddles, strangles, spreads, covered, protective."""

import pandas as pd
from typing_extensions import Unpack

from ..core import _process_strategy
from ..definitions import (
    double_strike_external_cols,
    double_strike_internal_cols,
)
from ..evaluation import _calls, _puts
from ..rules import _rule_non_overlapping_strike
from ..types import StrategyParams
from ._helpers import (
    Side,
    _covered_call,
    _spread,
    _straddles,
    _strangles,
    default_kwargs,
)


def long_straddles(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate long straddle strategy statistics (long call + long put at same strike).

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with long straddle strategy performance statistics
    """
    return _straddles(data, [(Side.long, _puts), (Side.long, _calls)], **kwargs)


def short_straddles(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate short straddle strategy statistics (short call + short put at same strike).

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short straddle strategy performance statistics
    """
    return _straddles(data, [(Side.short, _puts), (Side.short, _calls)], **kwargs)


def long_strangles(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate long strangle strategy statistics (long call + long put at different strikes).

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with long strangle strategy performance statistics
    """
    return _strangles(data, [(Side.long, _puts), (Side.long, _calls)], **kwargs)


def short_strangles(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate short strangle strategy statistics (short call + short put at different strikes).

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short strangle strategy performance statistics
    """
    return _strangles(data, [(Side.short, _puts), (Side.short, _calls)], **kwargs)


def long_call_spread(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate long call spread (bull call spread) statistics.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with long call spread strategy performance statistics
    """
    return _spread(data, [(Side.long, _calls), (Side.short, _calls)], **kwargs)


def short_call_spread(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate short call spread (bear call spread) statistics.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short call spread strategy performance statistics
    """
    return _spread(data, [(Side.short, _calls), (Side.long, _calls)], **kwargs)


def long_put_spread(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate long put spread (bear put spread) statistics.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with long put spread strategy performance statistics
    """
    return _spread(data, [(Side.short, _puts), (Side.long, _puts)], **kwargs)


def short_put_spread(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate short put spread (bull put spread) statistics.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short put spread strategy performance statistics
    """
    return _spread(data, [(Side.long, _puts), (Side.short, _puts)], **kwargs)


def covered_call(data: pd.DataFrame, **kwargs: Unpack[StrategyParams]) -> pd.DataFrame:
    """
    Generate covered call strategy statistics.

    A covered call consists of:
    - Long underlying position (simulated via long deep ITM call)
    - Short 1 call at higher strike

    This is an income strategy that profits from time decay on the short call
    while maintaining upside exposure up to the short strike. The long deep
    ITM call acts as a synthetic long stock position.

    Note: This implementation uses a synthetic approach with options only.
    For true covered call analysis with actual stock positions, additional
    data integration would be required.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with covered call strategy performance statistics
    """
    return _covered_call(
        data,
        [
            (Side.long, _calls),
            (Side.short, _calls),
        ],
        **kwargs,
    )


def protective_put(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate protective put (married put) strategy statistics.

    A protective put consists of:
    - Long underlying position (simulated via long deep ITM call)
    - Long 1 put at lower strike for protection

    This strategy provides downside protection while maintaining upside
    potential. The long deep ITM call acts as a synthetic long stock position.

    Note: This implementation uses a synthetic approach with options only.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with protective put strategy performance statistics
    """
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=double_strike_internal_cols,
        external_cols=double_strike_external_cols,
        leg_def=[
            (Side.long, _calls),
            (Side.long, _puts),
        ],
        rules=_rule_non_overlapping_strike,
        join_on=["underlying_symbol", "expiration", "dte_entry", "dte_range"],
        params=params,
    )
