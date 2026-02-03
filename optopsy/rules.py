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

    query = " & ".join(
        [f"strike_leg{leg + 1} > strike_leg{leg}" for leg in range(1, leg_count)]
    )

    return data.query(query)


def _rule_butterfly_strikes(
    data: pd.DataFrame, leg_def: List[Tuple]
) -> pd.DataFrame:
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

    return data.query(
        "strike_leg1 < strike_leg2 < strike_leg3 & "
        "(strike_leg2 - strike_leg1) == (strike_leg3 - strike_leg2)"
    )


def _rule_iron_condor_strikes(
    data: pd.DataFrame, leg_def: List[Tuple]
) -> pd.DataFrame:
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

    return data.query(
        "strike_leg1 < strike_leg2 < strike_leg3 < strike_leg4"
    )


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

    return data.query(
        "strike_leg1 < strike_leg2 & strike_leg2 == strike_leg3 & strike_leg3 < strike_leg4"
    )
