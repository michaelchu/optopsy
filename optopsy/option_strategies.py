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


def _add_date_range(s, e, f):
    f['start_date'] = s
    f['end_date'] = e
    return f


def _dedup_legs(spreads):
    groupby = ['quote_date', 'option_type',
               'expiration', 'underlying_symbol', 'ratio']
    on = groupby + ['delta']

    return (
        spreads
        .groupby(groupby)['delta']
        .max()
        .to_frame()
        .merge(spreads, on=on)
    )


def long_call(data, start_date, end_date, filters):
    filters = _add_date_range(start_date, end_date, filters)
    if _filter_check(filters):
        return _dedup_legs(create_spread(
            data, [(OptionType.CALL, 1)], filters))


def short_call(data, start_date, end_date, filters):
    filters = _add_date_range(start_date, end_date, filters)
    if _filter_check(filters):
        return _dedup_legs(create_spread(
            data, [(OptionType.CALL, 1)], filters))


def long_put(data, start_date, end_date, filters):
    filters = _add_date_range(start_date, end_date, filters)
    if _filter_check(filters):
        return _dedup_legs(create_spread(data, [(OptionType.PUT, 1)], filters))


def short_put(data, start_date, end_date, filters):
    filters = _add_date_range(start_date, end_date, filters)
    if _filter_check(filters):
        return _dedup_legs(create_spread(data, [(OptionType.PUT, 1)], filters))


def long_call_spread(data, start_date, end_date, filters):
    filters = _add_date_range(start_date, end_date, filters)
    if _filter_check(filters):
        legs = [(OptionType.CALL, -1), (OptionType.CALL, 1)]
        return _dedup_legs(create_spread(data, legs, filters))
    else:
        raise ValueError(
            "Long delta must be less than short delta for long call spreads!")


def short_call_spread(data, start_date, end_date, filters):
    filters = _add_date_range(start_date, end_date, filters)
    if _filter_check(filters):
        legs = [(OptionType.CALL, 1), (OptionType.CALL, -1)]
        return _dedup_legs(create_spread(data, legs, filters))
    else:
        raise ValueError(
            "Short delta must be less than long delta for short call spreads!")


def long_put_spread(data, start_date, end_date, filters):
    filters = _add_date_range(start_date, end_date, filters)
    if _filter_check(filters):
        legs = [(OptionType.PUT, 1), (OptionType.PUT, -1)]
        return _dedup_legs(create_spread(data, legs, filters))
    else:
        raise ValueError(
            "Short delta must be less than long delta for long put spreads!")


def short_put_spread(data, start_date, end_date, filters):
    filters = _add_date_range(start_date, end_date, filters)
    if _filter_check(filters):
        legs = [(OptionType.PUT, -1), (OptionType.PUT, 1)]
        return _dedup_legs(create_spread(data, legs, filters))
    else:
        raise ValueError(
            "Long delta must be less than short delta for short put spreads!")


def _filter_check(filters):
    return True
