"""Calendar spread and diagonal spread option strategies."""

from typing import Unpack

import pandas as pd

from ..evaluation import _calls, _puts
from ..types import StrategyParamsDict
from ._helpers import Side, _calendar_spread


def long_call_calendar(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParamsDict]
) -> pd.DataFrame:
    """
    Generate long call calendar spread strategy statistics.

    A long call calendar consists of:
    - Short 1 front-month call (near-term expiration)
    - Long 1 back-month call (longer-term expiration)
    - Both at the same strike

    This is a neutral strategy that profits from time decay differential
    between the two expirations. Maximum profit occurs when the underlying
    is at the strike price at front-month expiration.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters including:
            - front_dte_min: Minimum DTE for front leg (default: 20)
            - front_dte_max: Maximum DTE for front leg (default: 40)
            - back_dte_min: Minimum DTE for back leg (default: 50)
            - back_dte_max: Maximum DTE for back leg (default: 90)
            - exit_dte: Days before front expiration to exit (default: 7)

    Returns:
        DataFrame with long call calendar spread strategy performance statistics
    """
    return _calendar_spread(
        data, [(Side.short, _calls), (Side.long, _calls)], same_strike=True, **kwargs
    )


def short_call_calendar(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParamsDict]
) -> pd.DataFrame:
    """
    Generate short call calendar spread strategy statistics.

    A short call calendar consists of:
    - Long 1 front-month call (near-term expiration)
    - Short 1 back-month call (longer-term expiration)
    - Both at the same strike

    This strategy profits when the underlying moves significantly away
    from the strike price before front-month expiration.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short call calendar spread strategy performance statistics
    """
    return _calendar_spread(
        data, [(Side.long, _calls), (Side.short, _calls)], same_strike=True, **kwargs
    )


def long_put_calendar(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParamsDict]
) -> pd.DataFrame:
    """
    Generate long put calendar spread strategy statistics.

    A long put calendar consists of:
    - Short 1 front-month put (near-term expiration)
    - Long 1 back-month put (longer-term expiration)
    - Both at the same strike

    This is a neutral strategy that profits from time decay differential
    between the two expirations.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with long put calendar spread strategy performance statistics
    """
    return _calendar_spread(
        data, [(Side.short, _puts), (Side.long, _puts)], same_strike=True, **kwargs
    )


def short_put_calendar(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParamsDict]
) -> pd.DataFrame:
    """
    Generate short put calendar spread strategy statistics.

    A short put calendar consists of:
    - Long 1 front-month put (near-term expiration)
    - Short 1 back-month put (longer-term expiration)
    - Both at the same strike

    This strategy profits when the underlying moves significantly away
    from the strike price before front-month expiration.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short put calendar spread strategy performance statistics
    """
    return _calendar_spread(
        data, [(Side.long, _puts), (Side.short, _puts)], same_strike=True, **kwargs
    )


def long_call_diagonal(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParamsDict]
) -> pd.DataFrame:
    """
    Generate long call diagonal spread strategy statistics.

    A long call diagonal consists of:
    - Short 1 front-month call (near-term expiration)
    - Long 1 back-month call (longer-term expiration)
    - Different strikes for each leg

    This strategy combines elements of a calendar spread and a vertical spread.
    All strike combinations are evaluated.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with long call diagonal spread strategy performance statistics
    """
    return _calendar_spread(
        data, [(Side.short, _calls), (Side.long, _calls)], same_strike=False, **kwargs
    )


def short_call_diagonal(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParamsDict]
) -> pd.DataFrame:
    """
    Generate short call diagonal spread strategy statistics.

    A short call diagonal consists of:
    - Long 1 front-month call (near-term expiration)
    - Short 1 back-month call (longer-term expiration)
    - Different strikes for each leg

    This strategy combines elements of a calendar spread and a vertical spread.
    All strike combinations are evaluated.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short call diagonal spread strategy performance statistics
    """
    return _calendar_spread(
        data, [(Side.long, _calls), (Side.short, _calls)], same_strike=False, **kwargs
    )


def long_put_diagonal(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParamsDict]
) -> pd.DataFrame:
    """
    Generate long put diagonal spread strategy statistics.

    A long put diagonal consists of:
    - Short 1 front-month put (near-term expiration)
    - Long 1 back-month put (longer-term expiration)
    - Different strikes for each leg

    This strategy combines elements of a calendar spread and a vertical spread.
    All strike combinations are evaluated.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with long put diagonal spread strategy performance statistics
    """
    return _calendar_spread(
        data, [(Side.short, _puts), (Side.long, _puts)], same_strike=False, **kwargs
    )


def short_put_diagonal(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParamsDict]
) -> pd.DataFrame:
    """
    Generate short put diagonal spread strategy statistics.

    A short put diagonal consists of:
    - Long 1 front-month put (near-term expiration)
    - Short 1 back-month put (longer-term expiration)
    - Different strikes for each leg

    This strategy combines elements of a calendar spread and a vertical spread.
    All strike combinations are evaluated.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short put diagonal spread strategy performance statistics
    """
    return _calendar_spread(
        data, [(Side.long, _puts), (Side.short, _puts)], same_strike=False, **kwargs
    )
