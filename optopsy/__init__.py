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

from .strategies import (
    long_calls,
    long_puts,
    short_calls,
    short_puts,
    long_straddles,
    short_straddles,
    long_strangles,
    short_strangles,
    long_call_spread,
    short_call_spread,
    long_put_spread,
    short_put_spread,
    # Butterfly strategies
    long_call_butterfly,
    short_call_butterfly,
    long_put_butterfly,
    short_put_butterfly,
    # Iron condor and iron butterfly strategies
    iron_condor,
    reverse_iron_condor,
    iron_butterfly,
    reverse_iron_butterfly,
    # Covered strategies
    covered_call,
    protective_put,
    # Calendar spread strategies
    long_call_calendar,
    short_call_calendar,
    long_put_calendar,
    short_put_calendar,
    # Diagonal spread strategies
    long_call_diagonal,
    short_call_diagonal,
    long_put_diagonal,
    short_put_diagonal,
)
from .datafeeds import csv_data
from .types import StrategyParams, CalendarStrategyParams
from .signals import (
    rsi_below,
    rsi_above,
    day_of_week,
    sma_below,
    sma_above,
    and_signals,
    or_signals,
)

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
    "rsi_below",
    "rsi_above",
    "day_of_week",
    "sma_below",
    "sma_above",
    "and_signals",
    "or_signals",
]
