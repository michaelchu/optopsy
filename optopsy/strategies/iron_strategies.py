"""Iron condor and iron butterfly option strategies (4-leg)."""

import pandas as pd
from typing_extensions import Unpack

from ..evaluation import _calls, _puts
from ..types import StrategyParams
from ._helpers import Side, _iron_butterfly, _iron_condor


def iron_condor(data: pd.DataFrame, **kwargs: Unpack[StrategyParams]) -> pd.DataFrame:
    """
    Generate iron condor strategy statistics.

    An iron condor consists of:
    - Long 1 put at lowest strike (protection)
    - Short 1 put at lower-middle strike (income)
    - Short 1 call at upper-middle strike (income)
    - Long 1 call at highest strike (protection)

    This is a neutral income strategy that profits when the underlying stays
    between the two short strikes. Maximum profit is the net credit received.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with iron condor strategy performance statistics
    """
    return _iron_condor(
        data,
        [
            (Side.long, _puts),
            (Side.short, _puts),
            (Side.short, _calls),
            (Side.long, _calls),
        ],
        **kwargs,
    )


def reverse_iron_condor(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate reverse iron condor strategy statistics.

    A reverse iron condor consists of:
    - Short 1 put at lowest strike
    - Long 1 put at lower-middle strike
    - Long 1 call at upper-middle strike
    - Short 1 call at highest strike

    This strategy profits when the underlying makes a significant move
    in either direction.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with reverse iron condor strategy performance statistics
    """
    return _iron_condor(
        data,
        [
            (Side.short, _puts),
            (Side.long, _puts),
            (Side.long, _calls),
            (Side.short, _calls),
        ],
        **kwargs,
    )


def iron_butterfly(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate iron butterfly strategy statistics.

    An iron butterfly consists of:
    - Long 1 put at lowest strike (wing)
    - Short 1 put at middle strike (body)
    - Short 1 call at middle strike (body) - same strike as short put
    - Long 1 call at highest strike (wing)

    This is a neutral income strategy with higher profit potential than
    an iron condor, but a narrower profit zone. Maximum profit occurs
    when the underlying is exactly at the middle strike at expiration.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with iron butterfly strategy performance statistics
    """
    return _iron_butterfly(
        data,
        [
            (Side.long, _puts),
            (Side.short, _puts),
            (Side.short, _calls),
            (Side.long, _calls),
        ],
        **kwargs,
    )


def reverse_iron_butterfly(
    data: pd.DataFrame, **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    """
    Generate reverse iron butterfly strategy statistics.

    A reverse iron butterfly consists of:
    - Short 1 put at lowest strike (wing)
    - Long 1 put at middle strike (body)
    - Long 1 call at middle strike (body) - same strike as long put
    - Short 1 call at highest strike (wing)

    This strategy profits when the underlying makes a significant move
    away from the middle strike in either direction.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with reverse iron butterfly strategy performance statistics
    """
    return _iron_butterfly(
        data,
        [
            (Side.short, _puts),
            (Side.long, _puts),
            (Side.long, _calls),
            (Side.short, _calls),
        ],
        **kwargs,
    )
