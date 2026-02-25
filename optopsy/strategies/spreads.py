"""Two-leg option strategies: straddles, strangles, spreads, covered, protective."""

from typing import Optional, Unpack

import pandas as pd

from ..evaluation import _calls, _puts
from ..types import StrategyParamsDict
from ._helpers import (
    Side,
    _covered_call,
    _spread,
    _straddles,
    _strangles,
)


def long_straddles(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParamsDict]
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
    data: pd.DataFrame, **kwargs: Unpack[StrategyParamsDict]
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
    data: pd.DataFrame, **kwargs: Unpack[StrategyParamsDict]
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
    data: pd.DataFrame, **kwargs: Unpack[StrategyParamsDict]
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
    data: pd.DataFrame, **kwargs: Unpack[StrategyParamsDict]
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
    data: pd.DataFrame, **kwargs: Unpack[StrategyParamsDict]
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
    data: pd.DataFrame, **kwargs: Unpack[StrategyParamsDict]
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
    data: pd.DataFrame, **kwargs: Unpack[StrategyParamsDict]
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


def covered_call(
    data: pd.DataFrame,
    stock_data: Optional[pd.DataFrame] = None,
    **kwargs: Unpack[StrategyParamsDict],
) -> pd.DataFrame:
    """
    Generate covered call strategy statistics.

    A covered call consists of:
    - Long underlying position + short 1 OTM call at higher strike

    When *stock_data* is provided the underlying leg uses actual stock
    close prices.  Otherwise a long deep ITM call (default delta ~0.80)
    is used as a synthetic stock position.

    Args:
        data: DataFrame containing option chain data
        stock_data: Optional DataFrame of stock prices for the underlying.
            Accepts output from ``yfinance`` directly (``yf.download()``)
            as well as any DataFrame containing a ``close`` column and
            dates.  The data is normalized internally — column names are
            lowercased, a ``DatetimeIndex`` is converted to a column, and
            ``underlying_symbol`` is inferred from *data* when absent.
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
        stock_data=stock_data,
        **kwargs,
    )


def protective_put(
    data: pd.DataFrame,
    stock_data: Optional[pd.DataFrame] = None,
    **kwargs: Unpack[StrategyParamsDict],
) -> pd.DataFrame:
    """
    Generate protective put (married put) strategy statistics.

    A protective put consists of:
    - Long underlying position + long 1 OTM put at lower strike for protection

    When *stock_data* is provided the underlying leg uses actual stock
    close prices.  Otherwise a long deep ITM call (default delta ~0.80)
    is used as a synthetic stock position.

    Args:
        data: DataFrame containing option chain data
        stock_data: Optional DataFrame of stock prices for the underlying.
            Accepts output from ``yfinance`` directly (``yf.download()``)
            as well as any DataFrame containing a ``close`` column and
            dates.  The data is normalized internally — column names are
            lowercased, a ``DatetimeIndex`` is converted to a column, and
            ``underlying_symbol`` is inferred from *data* when absent.
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with protective put strategy performance statistics
    """
    return _covered_call(
        data,
        [
            (Side.long, _calls),
            (Side.long, _puts),
        ],
        stock_data=stock_data,
        **kwargs,
    )
