"""Butterfly option strategies (3-leg)."""

import pandas as pd
from typing_extensions import Unpack

from ..evaluation import _calls, _puts
from ..types import StrategyParams
from ._helpers import Side, _butterfly


def long_call_butterfly(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate long call butterfly strategy statistics.

    A long call butterfly consists of:
    - Long 1 call at lower strike (wing)
    - Short 2 calls at middle strike (body)
    - Long 1 call at upper strike (wing)

    This is a neutral strategy that profits when the underlying stays near
    the middle strike at expiration. Maximum profit occurs at the middle strike.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with long call butterfly strategy performance statistics
    """
    return _butterfly(
        data,
        [
            (Side.long, _calls, 1),
            (Side.short, _calls, 2),
            (Side.long, _calls, 1),
        ],
        **kwargs,
    )


def short_call_butterfly(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate short call butterfly strategy statistics.

    A short call butterfly consists of:
    - Short 1 call at lower strike (wing)
    - Long 2 calls at middle strike (body)
    - Short 1 call at upper strike (wing)

    This strategy profits when the underlying moves significantly away from
    the middle strike in either direction.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short call butterfly strategy performance statistics
    """
    return _butterfly(
        data,
        [
            (Side.short, _calls, 1),
            (Side.long, _calls, 2),
            (Side.short, _calls, 1),
        ],
        **kwargs,
    )


def long_put_butterfly(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate long put butterfly strategy statistics.

    A long put butterfly consists of:
    - Long 1 put at lower strike (wing)
    - Short 2 puts at middle strike (body)
    - Long 1 put at upper strike (wing)

    This is a neutral strategy that profits when the underlying stays near
    the middle strike at expiration. Maximum profit occurs at the middle strike.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with long put butterfly strategy performance statistics
    """
    return _butterfly(
        data,
        [
            (Side.long, _puts, 1),
            (Side.short, _puts, 2),
            (Side.long, _puts, 1),
        ],
        **kwargs,
    )


def short_put_butterfly(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate short put butterfly strategy statistics.

    A short put butterfly consists of:
    - Short 1 put at lower strike (wing)
    - Long 2 puts at middle strike (body)
    - Short 1 put at upper strike (wing)

    This strategy profits when the underlying moves significantly away from
    the middle strike in either direction.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short put butterfly strategy performance statistics
    """
    return _butterfly(
        data,
        [
            (Side.short, _puts, 1),
            (Side.long, _puts, 2),
            (Side.short, _puts, 1),
        ],
        **kwargs,
    )
