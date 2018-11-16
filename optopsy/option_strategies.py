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
from datetime import datetime


def _add_date_range(s, e, f):
    f["start_date"] = s
    f["end_date"] = e
    return f


def _dedup_legs(spreads):
    sort_by = ["quote_date", "expiration", "underlying_symbol", "strike"]
    groupby = ["quote_date", "expiration", "underlying_symbol", "ratio", "option_type"]
    on = groupby + ["delta"]

    return (
        spreads.groupby(groupby)["delta"]
        .max()
        .to_frame()
        .merge(spreads, on=on)
        .sort_values(sort_by)
    )


def _date_checks(start, end):
    return isinstance(start, datetime) and isinstance(end, datetime)


def _process_legs(data, start, end, legs, filters, check_func):
    filters = _add_date_range(start, end, filters)
    if check_func(filters) and _date_checks(start, end):
        return _dedup_legs(create_spread(data, legs, filters))
    else:
        raise ValueError("Invalid filters, or date types provided!")


def long_call(data, start_date, end_date, filters):
    legs = [(OptionType.CALL, 1)]
    return _process_legs(data, start_date, end_date, legs, filters, _singles_checks)


def short_call(data, start_date, end_date, filters):
    legs = [(OptionType.CALL, -1)]
    return _process_legs(data, start_date, end_date, legs, filters, _singles_checks)


def long_put(data, start_date, end_date, filters):
    legs = [(OptionType.PUT, 1)]
    return _process_legs(data, start_date, end_date, legs, filters, _singles_checks)


def short_put(data, start_date, end_date, filters):
    legs = [(OptionType.PUT, -1)]
    return _process_legs(data, start_date, end_date, legs, filters, _singles_checks)


def long_call_spread(data, start_date, end_date, filters):
    legs = [(OptionType.CALL, 1), (OptionType.CALL, -1)]
    return _process_legs(data, start_date, end_date, legs, filters, _call_spread_checks)


def short_call_spread(data, start_date, end_date, filters):
    legs = [(OptionType.CALL, -1), (OptionType.CALL, 1)]
    return _process_legs(data, start_date, end_date, legs, filters, _call_spread_checks)


def long_put_spread(data, start_date, end_date, filters):
    legs = [(OptionType.PUT, -1), (OptionType.PUT, 1)]
    return _process_legs(data, start_date, end_date, legs, filters, _put_spread_checks)


def short_put_spread(data, start_date, end_date, filters):
    legs = [(OptionType.PUT, 1), (OptionType.PUT, -1)]
    return _process_legs(data, start_date, end_date, legs, filters, _put_spread_checks)


def long_iron_condor(data, start_date, end_date, filters):
    legs = [
        (OptionType.CALL, 1),
        (OptionType.CALL, -1),
        (OptionType.PUT, 1),
        (OptionType.PUT, -1),
    ]
    return _process_legs(data, start_date, end_date, legs, filters, _iron_condor_checks)


def _singles_checks(filter):
    return "leg1_delta" in filter


def _call_spread_checks(filter):
    return (
        "leg1_delta" in filter
        and "leg2_delta" in filter
        and filter["leg1_delta"] > filter["leg2_delta"]
    )


def _put_spread_checks(filter):
    return (
        "leg1_delta" in filter
        and "leg2_delta" in filter
        and filter["leg1_delta"] < filter["leg2_delta"]
    )


def _iron_condor_checks(filter):
    return (
        "leg1_delta" in filter
        and "leg2_delta" in filter
        and "leg3_delta" in filter
        and "leg4_delta" in filter
        and filter["leg1_delta"] > filter["leg2_delta"]
        and filter["leg3_delta"] < filter["leg4_delta"]
    )
