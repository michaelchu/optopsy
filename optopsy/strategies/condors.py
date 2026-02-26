"""Condor option strategies (4-leg, same option type)."""

from typing import Unpack

import pandas as pd

from ..evaluation import _calls, _puts
from ..types import StrategyParamsDict
from ._helpers import Side, _condor


def long_call_condor(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParamsDict]
) -> pd.DataFrame:
    """
    Generate long call condor strategy statistics.

    A long call condor consists of:
    - Long 1 call at lowest strike (K1)
    - Short 1 call at lower-middle strike (K2)
    - Short 1 call at upper-middle strike (K3)
    - Long 1 call at highest strike (K4)

    This is a neutral strategy that profits when the underlying stays
    between the two short strikes. Similar to an iron condor but uses
    only calls.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with long call condor strategy performance statistics
    """
    return _condor(
        data,
        [
            (Side.long, _calls),
            (Side.short, _calls),
            (Side.short, _calls),
            (Side.long, _calls),
        ],
        **kwargs,
    )


def short_call_condor(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParamsDict]
) -> pd.DataFrame:
    """
    Generate short call condor strategy statistics.

    A short call condor consists of:
    - Short 1 call at lowest strike (K1)
    - Long 1 call at lower-middle strike (K2)
    - Long 1 call at upper-middle strike (K3)
    - Short 1 call at highest strike (K4)

    This strategy profits when the underlying makes a significant move
    in either direction away from the middle strikes.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short call condor strategy performance statistics
    """
    return _condor(
        data,
        [
            (Side.short, _calls),
            (Side.long, _calls),
            (Side.long, _calls),
            (Side.short, _calls),
        ],
        **kwargs,
    )


def long_put_condor(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParamsDict]
) -> pd.DataFrame:
    """
    Generate long put condor strategy statistics.

    A long put condor consists of:
    - Long 1 put at lowest strike (K1)
    - Short 1 put at lower-middle strike (K2)
    - Short 1 put at upper-middle strike (K3)
    - Long 1 put at highest strike (K4)

    This is a neutral strategy that profits when the underlying stays
    between the two short strikes. Similar to an iron condor but uses
    only puts.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with long put condor strategy performance statistics
    """
    return _condor(
        data,
        [
            (Side.long, _puts),
            (Side.short, _puts),
            (Side.short, _puts),
            (Side.long, _puts),
        ],
        **kwargs,
    )


def short_put_condor(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParamsDict]
) -> pd.DataFrame:
    """
    Generate short put condor strategy statistics.

    A short put condor consists of:
    - Short 1 put at lowest strike (K1)
    - Long 1 put at lower-middle strike (K2)
    - Long 1 put at upper-middle strike (K3)
    - Short 1 put at highest strike (K4)

    This strategy profits when the underlying makes a significant move
    in either direction away from the middle strikes.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short put condor strategy performance statistics
    """
    return _condor(
        data,
        [
            (Side.short, _puts),
            (Side.long, _puts),
            (Side.long, _puts),
            (Side.short, _puts),
        ],
        **kwargs,
    )
