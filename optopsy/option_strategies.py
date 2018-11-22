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
from .backtest import create_spread, simulate
from .filters import filter_data
from .checks import (
    singles_checks,
    call_spread_checks,
    put_spread_checks,
    iron_condor_checks,
    iron_condor_spread_check,
)

default_entry_filters = {
    "std_expr": False,
    "contract_size": 10,
    "entry_dte": (27, 30, 31),
    "exit_dte": None,
}


def _process_legs(data, legs, fil, check_func, mode):
    if _filter_checks(fil, check_func):
        # first pass, filter date in one go
        date_fil = {
            "start_date": fil.pop("start_date"),
            "end_date": fil.pop("end_date"),
        }

        filters = {**default_entry_filters, **fil}

        entry_spread_fil = {k: v for (k, v) in filters.items() if "entry_spread" in k}
        exit_spread_fil = {k: v for (k, v) in filters.items() if "exit_spread" in k}

        entry_fil = {
            k: v
            for (k, v) in filters.items()
            if not k.startswith("exit_") and "spread" not in k
        }
        exit_fil = {
            k: v
            for (k, v) in filters.items()
            if k.startswith("exit_") and "spread" not in k
        }

        return (
            filter_data(data, date_fil)
            .pipe(create_spread, legs, entry_fil, entry_spread_fil, mode)
            .pipe(simulate, data, exit_fil, exit_spread_fil, mode)
        )
    else:
        raise ValueError(
            "Invalid filter values provided, please check the filters and try again."
        )


def _filter_checks(filter, func=None):
    return True if func is None else func(filter)


def long_call(data, filters, mode="market"):
    legs = [(OptionType.CALL, 1)]
    return _process_legs(data, legs, filters, singles_checks, mode)


def short_call(data, filters, mode="market"):
    legs = [(OptionType.CALL, -1)]
    return _process_legs(data, legs, filters, singles_checks, mode)


def long_put(data, filters, mode="market"):
    legs = [(OptionType.PUT, 1)]
    return _process_legs(data, legs, filters, singles_checks, mode)


def short_put(data, filters, mode="market"):
    legs = [(OptionType.PUT, -1)]
    return _process_legs(data, legs, filters, singles_checks, mode)


def long_call_spread(data, filters, mode="market"):
    legs = [(OptionType.CALL, 1), (OptionType.CALL, -1)]
    return _process_legs(data, legs, filters, call_spread_checks, mode)


def short_call_spread(data, filters, mode="market"):
    legs = [(OptionType.CALL, -1), (OptionType.CALL, 1)]
    return _process_legs(data, legs, filters, call_spread_checks, mode)


def long_put_spread(data, filters, mode="market"):
    legs = [(OptionType.PUT, -1), (OptionType.PUT, 1)]
    return _process_legs(data, legs, filters, put_spread_checks, mode)


def short_put_spread(data, filters, mode="market"):
    legs = [(OptionType.PUT, 1), (OptionType.PUT, -1)]
    return _process_legs(data, legs, filters, put_spread_checks, mode)


def long_iron_condor(data, filters, mode="market"):
    legs = [
        (OptionType.PUT, 1),
        (OptionType.PUT, -1),
        (OptionType.CALL, -1),
        (OptionType.CALL, 1),
    ]
    return _process_legs(data, legs, filters, iron_condor_checks, mode).pipe(
        iron_condor_spread_check
    )


def short_iron_condor(data, filters, mode="market"):
    legs = [
        (OptionType.PUT, -1),
        (OptionType.PUT, 1),
        (OptionType.CALL, 1),
        (OptionType.CALL, -1),
    ]
    return _process_legs(data, legs, filters, iron_condor_checks, mode).pipe(
        iron_condor_spread_check
    )
