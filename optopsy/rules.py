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
