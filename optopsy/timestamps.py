"""Timestamp normalization for cross-source date matching.

When option chain data (from EODHD, CSV, etc.) and signal data (from yfinance,
custom sources, etc.) need to be joined by date, small representation
differences — timezone-aware vs naive, midnight vs market-close timestamps —
cause silent inner-join failures.

This module provides a single normalization function applied at **match
boundaries** (merges / ``.isin()`` lookups) that strips timezones and
truncates to date-level so both sides always agree.
"""

import pandas as pd


def normalize_dates(series: pd.Series) -> pd.Series:
    """Normalize a datetime Series to timezone-naive, date-only values.

    1. Strip timezone information (if present).
    2. Floor to day so that e.g. ``16:30:00`` and ``00:00:00`` both become
       midnight of the same date.

    Args:
        series: A ``datetime64`` Series (may be tz-aware or tz-naive).

    Returns:
        Timezone-naive Series with time component removed.
    """
    s = series.copy()

    # Strip timezone if present
    if hasattr(s.dt, "tz") and s.dt.tz is not None:
        s = s.dt.tz_localize(None)

    # Floor to day
    return s.dt.normalize()
