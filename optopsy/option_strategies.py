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
from .checks import *
from datetime import datetime


def _process_legs(data, start, end, legs, filters, sort_by=None, asc=True):
    filters = {**filters, **{"start_date": start, "end_date": end}}
    return create_spread(data, legs, filters, sort_by=sort_by, ascending=asc)


def _filter_checks(filter, func=None):
    return True if func is None else func(filter)


def long_call(data, start_date, end_date, filters):
    legs = [(OptionType.CALL, 1)]
    if _filter_checks(filters, singles_checks):
        return _process_legs(data, start_date, end_date, legs, filters)
    else:
        raise ValueError(
            "Invalid filter values provided, please check the filters and try again."
        )


def short_call(data, start_date, end_date, filters):
    legs = [(OptionType.CALL, -1)]
    if _filter_checks(filters, singles_checks):
        return _process_legs(data, start_date, end_date, legs, filters)
    else:
        raise ValueError(
            "Invalid filterv alues provided, please check the filters and try again."
        )


def long_put(data, start_date, end_date, filters):
    legs = [(OptionType.PUT, 1)]
    if _filter_checks(filters, singles_checks):
        return _process_legs(data, start_date, end_date, legs, filters)
    else:
        raise ValueError(
            "Invalid filter values provided, please check the filters and try again."
        )


def short_put(data, start_date, end_date, filters):
    legs = [(OptionType.PUT, -1)]
    if _filter_checks(filters, singles_checks):
        return _process_legs(data, start_date, end_date, legs, filters)
    else:
        raise ValueError(
            "Invalid filter values provided, please check the filters and try again."
        )


def long_call_spread(data, start_date, end_date, filters):
    legs = [(OptionType.CALL, 1), (OptionType.CALL, -1)]
    if _filter_checks(filters, call_spread_checks):
        return _process_legs(data, start_date, end_date, legs, filters)
    else:
        raise ValueError(
            "Invalid filter values provided, please check the filters and try again."
        )


def short_call_spread(data, start_date, end_date, filters):
    legs = [(OptionType.CALL, -1), (OptionType.CALL, 1)]
    if _filter_checks(filters, call_spread_checks):
        return _process_legs(data, start_date, end_date, legs, filters)
    else:
        raise ValueError(
            "Invalid filter values provided, please check the filters and try again."
        )


def long_put_spread(data, start_date, end_date, filters):
    legs = [(OptionType.PUT, -1), (OptionType.PUT, 1)]
    if _filter_checks(filters, put_spread_checks):
        return _process_legs(data, start_date, end_date, legs, filters)
    else:
        raise ValueError(
            "Invalid filter values provided, please check the filters and try again."
        )


def short_put_spread(data, start_date, end_date, filters):
    legs = [(OptionType.PUT, 1), (OptionType.PUT, -1)]
    if _filter_checks(filters, put_spread_checks):
        return _process_legs(data, start_date, end_date, legs, filters)
    else:
        raise ValueError(
            "Invalid filter values provided, please check the filters and try again."
        )


def long_iron_condor(data, start_date, end_date, filters):
    legs = [
        (OptionType.PUT, 1),
        (OptionType.PUT, -1),
        (OptionType.CALL, -1),
        (OptionType.CALL, 1),
    ]
    if _filter_checks(filters, iron_condor_checks):
        return _iron_condor(data, start_date, end_date, legs, filters)
    else:
        raise ValueError(
            "Invalid filter values provided, please check the filters and try again."
        )


def short_iron_condor(data, start_date, end_date, filters):
    legs = [
        (OptionType.PUT, -1),
        (OptionType.PUT, 1),
        (OptionType.CALL, 1),
        (OptionType.CALL, -1),
    ]
    if _filter_checks(filters, iron_condor_checks):
        return _iron_condor(data, start_date, end_date, legs, filters)
    else:
        raise ValueError(
            "Invalid filter values provided, please check the filters and try again."
        )


def _iron_condor(data, start_date, end_date, legs, filters):
    return _process_legs(data, start_date, end_date, legs, filters).pipe(
        iron_condor_spread_check
    )
