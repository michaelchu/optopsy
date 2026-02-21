"""Timestamp normalization utilities for cross-source date matching.

When option chain data (from EODHD, CSV, etc.) and signal data (from yfinance,
custom sources, etc.) need to be joined by date, small representation
differences — timezone-aware vs naive, midnight vs market-close timestamps —
cause silent inner-join failures.

This module provides a single normalization function that is applied at
**match boundaries** (merges / ``.isin()`` lookups) rather than at data
ingestion, so full timestamp precision is preserved in the underlying data
and only aligned when two DataFrames need to agree on a date key.

The ``resolution`` parameter (a pandas frequency string) controls the
truncation granularity:

* ``"D"``   — daily (default, current use-case)
* ``"h"``   — hourly
* ``"min"`` — minute-level
* ``"s"``   — second-level

When intraday support is added, callers simply pass a finer resolution.
"""

from typing import Optional

import pandas as pd

# Default resolution used throughout the library.  Strategy parameters can
# override this per-call via the ``date_resolution`` key.
DEFAULT_RESOLUTION: str = "D"


def normalize_timestamps(
    series: pd.Series,
    resolution: Optional[str] = None,
) -> pd.Series:
    """Normalize a datetime Series for reliable cross-source matching.

    1. Strip timezone information (convert to naive UTC-equivalent).
    2. Floor to the requested *resolution* so that, e.g., ``16:30:00`` and
       ``00:00:00`` both map to midnight when ``resolution="D"``.

    Args:
        series: A ``datetime64`` Series (may be tz-aware or tz-naive).
        resolution: Pandas frequency string (``"D"``, ``"h"``, ``"min"``,
            ``"s"``, …).  Defaults to :data:`DEFAULT_RESOLUTION` (``"D"``).

    Returns:
        Timezone-naive Series floored to *resolution*.
    """
    if resolution is None:
        resolution = DEFAULT_RESOLUTION

    s = series.copy()

    # 1. Strip timezone if present
    if hasattr(s.dt, "tz") and s.dt.tz is not None:
        s = s.dt.tz_localize(None)

    # 2. Floor to resolution
    return s.dt.floor(resolution)
