"""
Optopsy - Options Backtesting Library

Optopsy is a Python library for backtesting options trading strategies using
historical options chain data. It provides:

- 28 built-in options strategies (singles, spreads, butterflies, condors, calendars)
- Flexible filtering by DTE, OTM%, bid-ask spread, and option Greeks
- Configurable slippage models (mid, spread, liquidity-based)
- Statistical analysis with aggregated performance metrics
- Raw trade data export for custom analysis

Example:
    >>> import optopsy as op
    >>> data = op.csv_data('./SPX_2018.csv')
    >>> results = op.long_calls(data, max_entry_dte=60, exit_dte=30)

For detailed documentation, visit: https://github.com/michaelchu/optopsy
"""

__version__ = "2.2.0"

from .datafeeds import csv_data
from .signals import (
    Signal,
    and_signals,
    apply_signal,
    atr_above,
    atr_below,
    bb_above_upper,
    bb_below_lower,
    day_of_week,
    ema_cross_above,
    ema_cross_below,
    macd_cross_above,
    macd_cross_below,
    or_signals,
    rsi_above,
    rsi_below,
    signal,
    sma_above,
    sma_below,
    sustained,
)
from .simulator import SimulationResult, simulate
from .strategies import (
    # Covered strategies
    covered_call,
    iron_butterfly,
    # Iron condor and iron butterfly strategies
    iron_condor,
    # Butterfly strategies
    long_call_butterfly,
    # Calendar spread strategies
    long_call_calendar,
    # Diagonal spread strategies
    long_call_diagonal,
    long_call_spread,
    long_calls,
    long_put_butterfly,
    long_put_calendar,
    long_put_diagonal,
    long_put_spread,
    long_puts,
    long_straddles,
    long_strangles,
    protective_put,
    reverse_iron_butterfly,
    reverse_iron_condor,
    short_call_butterfly,
    short_call_calendar,
    short_call_diagonal,
    short_call_spread,
    short_calls,
    short_put_butterfly,
    short_put_calendar,
    short_put_diagonal,
    short_put_spread,
    short_puts,
    short_straddles,
    short_strangles,
)
from .timestamps import normalize_dates
from .types import CalendarStrategyParams, StrategyParams

__all__ = [
    "__version__",
    "long_calls",
    "long_puts",
    "short_calls",
    "short_puts",
    "long_straddles",
    "short_straddles",
    "long_strangles",
    "short_strangles",
    "long_call_spread",
    "short_call_spread",
    "long_put_spread",
    "short_put_spread",
    # Butterfly strategies
    "long_call_butterfly",
    "short_call_butterfly",
    "long_put_butterfly",
    "short_put_butterfly",
    # Iron condor and iron butterfly strategies
    "iron_condor",
    "reverse_iron_condor",
    "iron_butterfly",
    "reverse_iron_butterfly",
    # Covered strategies
    "covered_call",
    "protective_put",
    # Calendar spread strategies
    "long_call_calendar",
    "short_call_calendar",
    "long_put_calendar",
    "short_put_calendar",
    # Diagonal spread strategies
    "long_call_diagonal",
    "short_call_diagonal",
    "long_put_diagonal",
    "short_put_diagonal",
    "csv_data",
    # Type definitions
    "StrategyParams",
    "CalendarStrategyParams",
    # Signal functions
    "apply_signal",
    "rsi_below",
    "rsi_above",
    "day_of_week",
    "sma_below",
    "sma_above",
    "and_signals",
    "or_signals",
    "macd_cross_above",
    "macd_cross_below",
    "bb_above_upper",
    "bb_below_lower",
    "ema_cross_above",
    "ema_cross_below",
    "atr_above",
    "atr_below",
    "sustained",
    "Signal",
    "signal",
    # Simulation
    "simulate",
    "SimulationResult",
    # Timestamp utilities
    "normalize_dates",
]
