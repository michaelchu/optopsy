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

from .enums import OptionType, OrderAction
from .backtest import create_spread
from .checks import (
    singles_checks,
    call_spread_checks,
    put_spread_checks,
    iron_condor_checks,
    iron_condor_spread_check,
)
from datetime import datetime


def _process_legs(data, legs, filters, check_func, sort_by=None, asc=True):
    if _filter_checks(filters, check_func):
        return create_spread(data, legs, filters, sort_by=sort_by, ascending=asc)
    else:
        raise ValueError(
            "Invalid filter values provided, please check the filters and try again."
        )


def _filter_checks(filter, func=None):
    return True if func is None else func(filter)


def _merge(filters, start, end):
    return {**filters, **{"start_date": start, "end_date": end}}


def long_call(data, start, end, filters):
    legs = [(OptionType.CALL, 1)]
    return _process_legs(data, legs, _merge(filters, start, end), singles_checks)


def short_call(data, start, end, filters):
    legs = [(OptionType.CALL, -1)]
    return _process_legs(data, legs, _merge(filters, start, end), singles_checks)


def long_put(data, start, end, filters):
    legs = [(OptionType.PUT, 1)]
    return _process_legs(data, legs, _merge(filters, start, end), singles_checks)


def short_put(data, start, end, filters):
    legs = [(OptionType.PUT, -1)]
    return _process_legs(data, legs, _merge(filters, start, end), singles_checks)


def long_call_spread(data, start, end, filters):
    legs = [(OptionType.CALL, 1), (OptionType.CALL, -1)]
    return _process_legs(data, legs, _merge(filters, start, end), call_spread_checks)


def short_call_spread(data, start, end, filters):
    legs = [(OptionType.CALL, -1), (OptionType.CALL, 1)]
    return _process_legs(data, legs, _merge(filters, start, end), call_spread_checks)


def long_put_spread(data, start, end, filters):
    legs = [(OptionType.PUT, -1), (OptionType.PUT, 1)]
    return _process_legs(data, legs, _merge(filters, start, end), put_spread_checks)


def short_put_spread(data, start, end, filters):
    legs = [(OptionType.PUT, 1), (OptionType.PUT, -1)]
    return _process_legs(data, legs, _merge(filters, start, end), put_spread_checks)


def long_iron_condor(data, start, end, filters):
    legs = [
        (OptionType.PUT, 1),
        (OptionType.PUT, -1),
        (OptionType.CALL, -1),
        (OptionType.CALL, 1),
    ]
    return _process_legs(
        data, legs, _merge(filters, start, end), iron_condor_checks
    ).pipe(iron_condor_spread_check)


def short_iron_condor(data, start, end, filters):
    legs = [
        (OptionType.PUT, -1),
        (OptionType.PUT, 1),
        (OptionType.CALL, 1),
        (OptionType.CALL, -1),
    ]
    return _process_legs(
        data, legs, _merge(filters, start, end), iron_condor_checks
    ).pipe(iron_condor_spread_check)
