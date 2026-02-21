"""Type definitions for Optopsy strategy parameters."""

from typing import Literal, Optional, TypedDict

import pandas as pd


class StrategyParams(TypedDict, total=False):
    """Common parameters for all option strategies.

    All fields are optional to allow partial parameter specification.
    """

    # Timing parameters
    max_entry_dte: int
    exit_dte: int
    exit_dte_tolerance: int
    dte_interval: int

    # Filtering parameters
    max_otm_pct: float
    otm_pct_interval: float
    min_bid_ask: float

    # Greeks filtering (optional)
    delta_min: Optional[float]
    delta_max: Optional[float]

    # Greeks grouping (optional)
    delta_interval: Optional[float]

    # Pre-computed signal dates (optional).
    # DataFrames with (underlying_symbol, quote_date) pairs indicating
    # valid dates for entry/exit.  Use signals.apply_signal() to generate.
    entry_dates: Optional[pd.DataFrame]
    exit_dates: Optional[pd.DataFrame]

    # Timestamp resolution for cross-source date matching (default "D" for
    # daily).  Use "h", "min", "s" for intraday granularity.
    date_resolution: Optional[str]

    # Slippage settings
    slippage: Literal["mid", "spread", "liquidity"]
    fill_ratio: float
    reference_volume: int

    # Output control
    raw: bool
    drop_nan: bool


class CalendarStrategyParams(StrategyParams):
    """Parameters for calendar and diagonal spread strategies.

    Extends StrategyParams with additional timing parameters for
    front and back month legs.
    """

    # Additional timing parameters for calendar/diagonal strategies
    front_dte_min: int
    front_dte_max: int
    back_dte_min: int
    back_dte_max: int
