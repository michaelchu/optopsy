"""
This module will provide public functions to generate option spreads
based on a list of tuples describing each leg and the filters to be
applied on each leg during creation time.

Filters that do not start with 'exit' or 'entry_spread' are applied
first for each leg.
"""


from .enums import Period
from .option_queries import opt_type
from functools import reduce
import optopsy.filters as fil
import pandas as pd


default_entry_filters = {
    "std_expr": False,
    "contract_size": 10,
    "entry_dte": Period.FOUR_WEEKS.value,
}


def _create_legs(data, leg):
    return (
        data
        .pipe(opt_type, option_type=leg[0])
        .assign(ratio=leg[1])
    )


def _apply_filters(legs, filters):
    if not filters:
        return legs
    else:
        return [reduce(lambda l, f: getattr(fil, f)(l, filters[f], idx), filters, leg)
                for idx, leg in enumerate(legs)]


def create_spread(data, leg_structs, filters):
    sort_by = ['quote_date', 'option_type', 'expiration', 'strike']
    legs = [_create_legs(data, leg) for leg in leg_structs]

    # merge and apply leg filters to create spread
    filters = {**default_entry_filters, **filters}
    entry_filters = {f: filters[f]
                     for f in filters if (not f.startswith('entry_spread') and
                                          not f.startswith('exit_'))}
    spread = pd.concat(_apply_filters(legs, entry_filters)).sort_values(sort_by)

    # apply spread level filters to spread
    spread_filters = {f: filters[f]
                      for f in filters if f.startswith('entry_spread')}
    return pd.concat(_apply_filters(
        [spread], spread_filters)).sort_values(sort_by)
