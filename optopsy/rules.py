"""Strike and expiration validation rules for multi-leg option strategies.

Each rule function receives a DataFrame of candidate leg combinations and a
leg definition list, then filters out rows that violate the strategy's
structural constraints.  Rules are passed to ``core._strategy_engine()`` via
the ``rules`` parameter and are applied after legs are joined but before
P&L calculation.

Rule functions:
- ``_rule_non_overlapping_strike`` — ascending strike ordering for spreads/strangles
- ``_rule_butterfly_strikes`` — ascending strikes with equal-width wings
- ``_rule_iron_condor_strikes`` — four strictly ascending strikes
- ``_rule_iron_butterfly_strikes`` — four strikes where middle two are equal
- ``_rule_expiration_ordering`` — front leg expires before back leg (calendar/diagonal)
"""

from typing import List, Tuple

import pandas as pd


def _rule_non_overlapping_strike(
    data: pd.DataFrame, leg_def: List[Tuple]
) -> pd.DataFrame:
    """
    Filter multi-leg strategies to ensure strikes don't overlap.

    For spreads and strangles, this ensures leg1 strike < leg2 strike < leg3 strike, etc.

    Args:
        data: DataFrame containing multi-leg strategy data
        leg_def: List of tuples defining strategy legs

    Returns:
        Filtered DataFrame with non-overlapping strikes
    """
    leg_count = len(leg_def)
    if leg_count == 1:
        return data

    mask = pd.Series(True, index=data.index)
    for leg in range(1, leg_count):
        mask = mask & (data[f"strike_leg{leg + 1}"] > data[f"strike_leg{leg}"])

    return data[mask]


def _rule_butterfly_strikes(data: pd.DataFrame, leg_def: List[Tuple]) -> pd.DataFrame:
    """
    Filter butterfly strategies to ensure proper strike ordering and equal width.

    A butterfly requires:
    - strike_leg1 < strike_leg2 < strike_leg3
    - Equal wing widths: (strike_leg2 - strike_leg1) == (strike_leg3 - strike_leg2)

    Args:
        data: DataFrame containing butterfly strategy data
        leg_def: List of tuples defining strategy legs

    Returns:
        Filtered DataFrame with valid butterfly strike configurations
    """
    if len(leg_def) != 3:
        return data

    mask = (
        (data["strike_leg1"] < data["strike_leg2"])
        & (data["strike_leg2"] < data["strike_leg3"])
        & (
            (data["strike_leg2"] - data["strike_leg1"])
            == (data["strike_leg3"] - data["strike_leg2"])
        )
    )
    return data[mask]


def _rule_iron_condor_strikes(data: pd.DataFrame, leg_def: List[Tuple]) -> pd.DataFrame:
    """
    Filter iron condor strategies to ensure proper strike ordering.

    An iron condor requires 4 strikes in ascending order:
    - strike_leg1 (long put) < strike_leg2 (short put) < strike_leg3 (short call) < strike_leg4 (long call)

    Args:
        data: DataFrame containing iron condor strategy data
        leg_def: List of tuples defining strategy legs

    Returns:
        Filtered DataFrame with valid iron condor strike configurations
    """
    if len(leg_def) != 4:
        return data

    mask = (
        (data["strike_leg1"] < data["strike_leg2"])
        & (data["strike_leg2"] < data["strike_leg3"])
        & (data["strike_leg3"] < data["strike_leg4"])
    )
    return data[mask]


def _rule_iron_butterfly_strikes(
    data: pd.DataFrame, leg_def: List[Tuple]
) -> pd.DataFrame:
    """
    Filter iron butterfly strategies to ensure proper strike ordering.

    An iron butterfly requires:
    - strike_leg1 (long put) < strike_leg2 (short put) = strike_leg3 (short call) < strike_leg4 (long call)
    - The short put and short call share the same strike (ATM)

    Args:
        data: DataFrame containing iron butterfly strategy data
        leg_def: List of tuples defining strategy legs

    Returns:
        Filtered DataFrame with valid iron butterfly strike configurations
    """
    if len(leg_def) != 4:
        return data

    mask = (
        (data["strike_leg1"] < data["strike_leg2"])
        & (data["strike_leg2"] == data["strike_leg3"])
        & (data["strike_leg3"] < data["strike_leg4"])
    )
    return data[mask]


def _rule_expiration_ordering(data: pd.DataFrame, leg_def: List[Tuple]) -> pd.DataFrame:
    """
    Filter calendar/diagonal spread strategies to ensure front leg expires before back leg.

    Both calendar and diagonal spreads require:
    - expiration_leg1 (front/short-term) < expiration_leg2 (back/long-term)

    Args:
        data: DataFrame containing calendar/diagonal spread strategy data
        leg_def: List of tuples defining strategy legs

    Returns:
        Filtered DataFrame with valid expiration configurations
    """
    if len(leg_def) != 2:
        return data

    return data[data["expiration_leg1"] < data["expiration_leg2"]]
