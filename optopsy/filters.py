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

from .option_queries import between, nearest, eq
from datetime import datetime
import pandas as pd


def _process_tuples(data, col, groupby, value):
    if len(set(value)) == 1:
        return eq(data, col, value[1])
    else:
        return data.pipe(nearest, col, value[1], groupby=groupby).pipe(
            between, col, value[0], value[2], absolute=True
        )


def _process_values(data, col, value, groupby=None, valid_types=(int, float, tuple)):
    if not isinstance(value, valid_types):
        raise ValueError("Invalid value passed to filter")
    elif isinstance(value, tuple):
        return _process_tuples(data, col, groupby, value)
    else:
        return nearest(data, col, value, groupby=groupby)


def _calc_strike_pct(data, value, n, idx):
    if not isinstance(value, (int, float, tuple)):
        raise ValueError(f"Invalid value passed for leg {n+1} entry strike percentage")
    elif idx == n:
        return data.assign(
            strike_pct=lambda r: (r["strike"] / r["underlying_price"]).round(2)
        ).pipe(_process_values, "strike_pct", value)
    else:
        return data


def start_date(data, value, _idx):
    if isinstance(value, datetime):
        return data[data["expiration"] >= value]
    else:
        raise ValueError("Start Dates must of Date type")


def end_date(data, value, _idx):
    if isinstance(value, datetime):
        return data[data["expiration"] <= value]
    else:
        raise ValueError("End Dates must of Date type")


def std_expr(data, value, _idx):
    """
    Use all expirations, only standard or only non standard.

    For example, only using non standard would only use weekly,
    monthly and quarterly expirations.
    """
    return data


def contract_size(data, value, _idx):
    """
    Multiply the profit in the trades report by the Contract Size.

    For example, the profit is multiplied by 10 contract size.
    """
    if isinstance(value, int):
        return data.assign(contracts=value)
    else:
        raise ValueError("Contract sizes must of Int type")


def entry_dte(data, value, _idx):
    """
    Days to expiration min and max for the trade to be considered.

    For example, it will search options that have days to expiration
    between and including 20 to 55.
    """
    groupby = ["option_type", "expiration", "underlying_symbol"]
    return _process_values(data, "dte", value, groupby=groupby)


def entry_days(data, value, _idx):
    """
    Stagger trades every this many Entry Days.

    For example, there would be a new trade every 7 days from the last new trade.
    """
    pass


def leg1_delta(data, value, idx):
    """
    Absolute value of a delta of an option.
    """
    return _process_values(data, "delta", value) if idx == 0 else data


def leg2_delta(data, value, idx):
    """
    Absolute value of a delta of an option.
    """
    return _process_values(data, "delta", value) if idx == 1 else data


def leg3_delta(data, value, idx):
    """
    Absolute value of a delta of an option.
    """
    return _process_values(data, "delta", value) if idx == 2 else data


def leg4_delta(data, value, idx):
    """
    Absolute value of a delta of an option.
    """
    return _process_values(data, "delta", value) if idx == 3 else data


def leg1_strike_pct(data, value, idx):
    """
    Stock Percentage (strike / stock price).
    """
    return _calc_strike_pct(data, value, 0, idx)


def leg2_strike_pct(data, value, idx):
    """
    Stock Percentage (strike / stock price).
    """
    return _calc_strike_pct(data, value, 1, idx)


def leg3_strike_pct(data, value, idx):
    """
    Stock Percentage (strike / stock price).
    """
    return _calc_strike_pct(data, value, 2, idx)


def leg4_strike_pct(data, value, idx):
    """
    Stock Percentage (strike / stock price).
    """
    return _calc_strike_pct(data, value, 3, idx)


def entry_spread_price(data, value, _idx):
    """
    The net price of the spread.

    For example, it would set a min max of $0.10 to $0.20 and find only spreads with prices
    within that range.
    """
    pass


def entry_spread_delta(data, value, _idx):
    """
    The net delta of the spread.

    For example, it would set a min max of .30 to .40 and find only spreads with net deltas
    within that range.
    """
    pass


def entry_spread_yield(data, value, _idx):
    """
    Yield Percentage is (option entry price / stockprice).

    For example it would search options that have yldpct between
    and including .05 to .10 (5 and 10 percent).
    """
    pass


def exit_dte(data, value, _idx):
    """
    Exit the trade when the days to expiration left is equal to or below this.

    For example, it would exit a trade with 10 days to expiration.
    """
    if value is None:
        return data[data["quote_date_exit"] == data["expiration"]]
    else:
        groupby = ["option_type", "expiration", "underlying_symbol"]
        return _process_values(data, "dte_exit", value, groupby=groupby)


def exit_hold_days(data, value, _idx):
    """
    Exit the trade when the trade was held this many days.

    For example, it would exit a trade when the trade has been held for 20 days.
    """
    pass


def exit_leg_1_delta(data, value, idx):
    """
    Exit the trade when the delta of leg 1 is below the min or above the max.

    For example, it would exit when the delta of the
    first leg is below .10 or above .90 delta.
    """
    pass


def exit_leg_1_otm_pct(data, value, idx):
    """
    Exit the trade when the strike as a percent of stock price
    of leg 1 is below the min or above the max.

    For example, it would exit when the strike percentage
    of stock price is below 1.05 or above 1.20.
    """
    pass


def exit_profit_loss_pct(data, value, _idx):
    """
    Take profits and add stop loss to exit trade at these intervals.

    For example, set a stop loss of 50 (-50%) and a profit target at 200 (200%) on a long call.
    Set only a stop loss by leaving profit blank.
    """
    pass


def exit_spread_delta(data, value, _idx):
    """
    Exit and roll the trade if the spread total delta exceed the min or max value. For Example;

    spread delta = leg1ratio * leg1delta + leg2ratio * leg2delta
    """
    pass


def exit_spread_price(data, value, _idx):
    """
    Exit the trade when the trade price falls below the min or rises above the max.

    For example, it would exit if below 0.4 min or above $0.90 max price.
    """
    pass


def exit_strike_diff_pct(data, value, _idx):
    """
    Exit the trade when the trade price divided by the difference
    in strike prices falls below the min or rises above the max.

    For example, a $5 wide call spread would exit if the price of
    $1 divided by 5 is below the min of .20 or the price of 4.5
    that is above the max of .90.
    """
    pass
