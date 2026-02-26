"""Calendar-based signals: day_of_week."""

import pandas as pd

from ._helpers import SignalFunc


def day_of_week(*days: int) -> SignalFunc:
    """True on specific days of the week.

    Args:
        *days: Day numbers where Monday=0, Tuesday=1, ..., Sunday=6.
    """
    day_set = set(days)

    def _signal(data: pd.DataFrame) -> "pd.Series[bool]":
        return data["quote_date"].dt.dayofweek.isin(day_set)

    return _signal
