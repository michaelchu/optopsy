#     Optopsy - Python Backtesting library for options trading strategies
#     Copyright (C) 2018  Michael Chu

#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.

#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <https://www.gnu.org/licenses/>.

import logging
from functools import reduce

import pandas as pd

from .checks import singles_checks, vertical_call_checks
from .enums import OptionType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _create_strategy(legs, check_func, struct):
    for leg in legs:
        check_func(leg)

    strategy = [leg.assign(ratio=struct[idx][1]) for idx, leg in enumerate(legs)]

    return (
        pd.concat(strategy)
        .rename(columns={"bid": "bid_entry", "ask": "ask_entry"})
        .pipe(_dedup_rows_by_cols, ["delta", "strike"])
    )


def _dedup_rows_by_cols(spd, cols, groupby=None, mode="max"):
    return reduce(lambda i, c: _do_dedupe(spd, groupby, c, mode), cols, spd)


def _do_dedupe(spd, groupby, col, mode):
    # dedupe delta dist ties
    if groupby is None:
        groupby = [
            "quote_date",
            "expiration",
            "underlying_symbol",
            "ratio",
            "option_type",
        ]

    on = groupby + [col]

    if mode == "min":
        return spd.groupby(groupby)[col].min().to_frame().merge(spd, on=on)
    else:
        return spd.groupby(groupby)[col].max().to_frame().merge(spd, on=on)


def long_call(leg):
    return _create_strategy([leg], singles_checks, [(OptionType.CALL, 1)])


def short_call(leg):
    return _create_strategy([leg], singles_checks, [(OptionType.CALL, -1)])


def long_put(leg):
    return _create_strategy([leg], singles_checks, [(OptionType.PUT, 1)])


def short_put(leg):
    return _create_strategy([leg], singles_checks, [(OptionType.PUT, -1)])


def long_call_spread(leg1, leg2):
    struct = [(OptionType.CALL, 1), (OptionType.CALL, -1)]
    return _create_strategy([leg1, leg2], vertical_call_checks, struct)


def short_call_spread(leg1, leg2):
    struct = [(OptionType.CALL, -1), (OptionType.CALL, 1)]
    return _create_strategy([leg1, leg2], vertical_call_checks, struct)


def long_put_spread(leg1, leg2):
    struct = [(OptionType.PUT, -1), (OptionType.PUT, 1)]
    return _create_strategy([leg1, leg2], vertical_call_checks, struct)


def short_put_spread(leg1, leg2):
    struct = [(OptionType.PUT, 1), (OptionType.PUT, -1)]
    return _create_strategy([leg1, leg2], vertical_call_checks, struct)


def _iron_condor(leg1, leg2, leg3, leg4, struct, butterfly=False):
    spread = _create_strategy([leg1, leg2, leg3, leg4], vertical_call_checks, struct)

    if spread is None:
        return None
    elif butterfly:
        # here we filter only for condors with same strikes for legs 2 and 3
        pass
    else:
        return (
            spread.assign(
                d_strike=lambda r: spread.duplicated(subset="strike", keep=False)
            )
            .groupby(spread.index)
            .filter(lambda r: (r.d_strike == False).all())
            .drop(columns="d_strike")
        )


def long_iron_condor(leg1, leg2, leg3, leg4):
    struct = [
        (OptionType.PUT, 1),
        (OptionType.PUT, -1),
        (OptionType.CALL, -1),
        (OptionType.CALL, 1),
    ]
    return _iron_condor(leg1, leg2, leg3, leg4, struct)


def short_iron_condor(leg1, leg2, leg3, leg4):
    struct = [
        (OptionType.PUT, -1),
        (OptionType.PUT, 1),
        (OptionType.CALL, 1),
        (OptionType.CALL, -1),
    ]
    return _iron_condor(leg1, leg2, leg3, leg4, struct)

def long_iron_butterfly(leg1, leg2, leg3, leg4):
    struct = [
        (OptionType.PUT, 1),
        (OptionType.PUT, -1),
        (OptionType.CALL, -1),
        (OptionType.CALL, 1),
    ]
    return _iron_condor(leg1, leg2, leg3, leg4, struct, butterfly=True)


def short_iron_butterfly(leg1, leg2, leg3, leg4):
    struct = [
        (OptionType.PUT, -1),
        (OptionType.PUT, 1),
        (OptionType.CALL, 1),
        (OptionType.CALL, -1),
    ]
    return _iron_condor(leg1, leg2, leg3, leg4, struct, butterfly=True)