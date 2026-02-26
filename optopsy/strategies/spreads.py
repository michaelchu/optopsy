"""Two-leg option strategies: straddles, strangles, spreads, covered, protective."""

from typing import Optional, Unpack

import pandas as pd

from ..evaluation import _calls, _puts
from ..types import StrategyParamsDict
from ._helpers import (
    Side,
    _collar,
    _covered_call,
    _spread,
    _straddles,
    _strangles,
)
from .singles import short_puts


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
    *,
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
    *,
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


def collar(
    data: pd.DataFrame,
    *,
    stock_data: Optional[pd.DataFrame] = None,
    **kwargs: Unpack[StrategyParamsDict],
) -> pd.DataFrame:
    """
    Generate collar strategy statistics.

    A collar consists of:
    - Long underlying position + short 1 OTM call + long 1 OTM put

    When *stock_data* is provided the underlying leg uses actual stock
    close prices.  Otherwise a long deep ITM call (default delta ~0.80)
    is used as a synthetic stock position.

    Args:
        data: DataFrame containing option chain data
        stock_data: Optional DataFrame of stock prices for the underlying.
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with collar strategy performance statistics
    """
    return _collar(
        data,
        [
            (Side.long, _calls),
            (Side.short, _calls),
            (Side.long, _puts),
        ],
        stock_data=stock_data,
        **kwargs,
    )


def cash_secured_put(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParamsDict]
) -> pd.DataFrame:
    """
    Generate cash-secured put strategy statistics.

    A cash-secured put is functionally identical to a short put — the
    trader sells a put while holding enough cash to buy the underlying
    if assigned.  This is an alias for ``short_puts`` provided for
    convenience with common retail terminology.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with cash-secured put strategy performance statistics
    """
    return short_puts(data, **kwargs)


def call_back_spread(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParamsDict]
) -> pd.DataFrame:
    """
    Generate call back spread (call ratio backspread) statistics.

    A call back spread consists of:
    - Short 1 ITM call at lower strike
    - Long 2 OTM calls at higher strike

    This is a bullish strategy that profits from a large upward move.
    The 2:1 ratio provides unlimited upside with limited downside.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with call back spread strategy performance statistics
    """
    return _spread(data, [(Side.short, _calls, 1), (Side.long, _calls, 2)], **kwargs)


def put_back_spread(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParamsDict]
) -> pd.DataFrame:
    """
    Generate put back spread (put ratio backspread) statistics.

    A put back spread consists of:
    - Short 1 ITM put at higher strike
    - Long 2 OTM puts at lower strike

    This is a bearish strategy that profits from a large downward move.
    The 2:1 ratio provides large downside profit with limited upside risk.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with put back spread strategy performance statistics
    """
    return _spread(data, [(Side.short, _puts, 1), (Side.long, _puts, 2)], **kwargs)


def call_front_spread(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParamsDict]
) -> pd.DataFrame:
    """
    Generate call front spread (call ratio spread) statistics.

    A call front spread consists of:
    - Long 1 ITM call at lower strike
    - Short 2 OTM calls at higher strike

    This is a neutral-to-slightly-bullish strategy that profits from
    time decay when the underlying stays near the short strike.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with call front spread strategy performance statistics
    """
    return _spread(data, [(Side.long, _calls, 1), (Side.short, _calls, 2)], **kwargs)


def put_front_spread(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParamsDict]
) -> pd.DataFrame:
    """
    Generate put front spread (put ratio spread) statistics.

    A put front spread consists of:
    - Long 1 ITM put at higher strike
    - Short 2 OTM puts at lower strike

    This is a neutral-to-slightly-bearish strategy that profits from
    time decay when the underlying stays near the short strike.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with put front spread strategy performance statistics
    """
    return _spread(data, [(Side.long, _puts, 1), (Side.short, _puts, 2)], **kwargs)
