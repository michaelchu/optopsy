__version__ = "2.0.3"

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
]
