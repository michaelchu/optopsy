"""Public API for options strategy backtesting.

Each strategy function (e.g. ``long_calls``, ``iron_condor``) accepts a DataFrame
of option chain data and optional ``StrategyParams`` keyword arguments, then
returns a DataFrame of either raw trades or aggregated descriptive statistics.

**Pattern:** Every public function delegates to a private helper (``_singles``,
``_spread``, ``_butterfly``, etc.) that assembles leg definitions and calls
``core._process_strategy()`` (or ``_process_calendar_strategy()`` for calendar
and diagonal spreads).

**Leg definitions** are lists of tuples: ``(Side.long/short, filter_fn, quantity)``.
The ``Side`` enum encodes direction as a multiplier (``long=1``, ``short=-1``).
``filter_fn`` is ``_calls`` or ``_puts`` from ``core.py``.

**Default parameters** are defined in ``default_kwargs`` (standard strategies) and
``calendar_default_kwargs`` (calendar/diagonal spreads).  Users override any
parameter via keyword arguments.
"""

from ._helpers import Side, calendar_default_kwargs, default_kwargs
from .butterflies import (
    long_call_butterfly,
    long_put_butterfly,
    short_call_butterfly,
    short_put_butterfly,
)
from .calendar import (
    long_call_calendar,
    long_call_diagonal,
    long_put_calendar,
    long_put_diagonal,
    short_call_calendar,
    short_call_diagonal,
    short_put_calendar,
    short_put_diagonal,
)
from .iron_strategies import (
    iron_butterfly,
    iron_condor,
    reverse_iron_butterfly,
    reverse_iron_condor,
)
from .singles import long_calls, long_puts, short_calls, short_puts
from .spreads import (
    covered_call,
    long_call_spread,
    long_put_spread,
    long_straddles,
    long_strangles,
    protective_put,
    short_call_spread,
    short_put_spread,
    short_straddles,
    short_strangles,
)

__all__ = [
    "Side",
    "default_kwargs",
    "calendar_default_kwargs",
    # Singles
    "long_calls",
    "long_puts",
    "short_calls",
    "short_puts",
    # Straddles & strangles
    "long_straddles",
    "short_straddles",
    "long_strangles",
    "short_strangles",
    # Vertical spreads
    "long_call_spread",
    "short_call_spread",
    "long_put_spread",
    "short_put_spread",
    # Covered & protective
    "covered_call",
    "protective_put",
    # Butterflies
    "long_call_butterfly",
    "short_call_butterfly",
    "long_put_butterfly",
    "short_put_butterfly",
    # Iron condor & iron butterfly
    "iron_condor",
    "reverse_iron_condor",
    "iron_butterfly",
    "reverse_iron_butterfly",
    # Calendar spreads
    "long_call_calendar",
    "short_call_calendar",
    "long_put_calendar",
    "short_put_calendar",
    # Diagonal spreads
    "long_call_diagonal",
    "short_call_diagonal",
    "long_put_diagonal",
    "short_put_diagonal",
]
