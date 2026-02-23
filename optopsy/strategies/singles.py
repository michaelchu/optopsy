"""Single-leg option strategies (long/short calls and puts)."""

import pandas as pd
from typing_extensions import Unpack

from ..core import _calls, _puts
from ..types import StrategyParams
from ._helpers import Side, _singles


def long_calls(data: pd.DataFrame, **kwargs: Unpack[StrategyParams]) -> pd.DataFrame:
    """
    Generate long call strategy statistics.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters (see StrategyParams)

    Returns:
        DataFrame with long call strategy performance statistics
    """
    return _singles(data, [(Side.long, _calls)], **kwargs)


def long_puts(data: pd.DataFrame, **kwargs: Unpack[StrategyParams]) -> pd.DataFrame:
    """
    Generate long put strategy statistics.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with long put strategy performance statistics
    """
    return _singles(data, [(Side.long, _puts)], **kwargs)


def short_calls(data: pd.DataFrame, **kwargs: Unpack[StrategyParams]) -> pd.DataFrame:
    """
    Generate short call strategy statistics.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short call strategy performance statistics
    """
    return _singles(data, [(Side.short, _calls)], **kwargs)


def short_puts(data: pd.DataFrame, **kwargs: Unpack[StrategyParams]) -> pd.DataFrame:
    """
    Generate short put strategy statistics.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Optional strategy parameters

    Returns:
        DataFrame with short put strategy performance statistics
    """
    return _singles(data, [(Side.short, _puts)], **kwargs)
