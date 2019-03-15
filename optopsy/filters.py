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
from datetime import datetime

import numpy as np
from pandas.core.base import PandasObject

from .helpers import assign_dte, inspect
from .option_queries import between, eq, nearest


def _process_range(data, col, groupby, value, min, max):
    if value == min == max:
        return eq(data, col, value)
    return (
        data.pipe(nearest, col, value, groupby=groupby)
        .pipe(inspect)
        .pipe(between, col, min, max, absolute=True)
    )


def _process_values(data, col, value, min, max, groupby=None):
    if min is not None and max is not None:
        return _process_range(data, col, groupby, value, min, max)
    else:
        return nearest(data, col, value, groupby=groupby)


def calls(df):
    return df[df.option_type.str.lower().str.startswith("c")]


def puts(df):
    return df[df.option_type.str.lower().str.startswith("p")]


def start_date(data, value):
    if isinstance(value, datetime):
        return data[data["expiration"] >= value]
    else:
        raise ValueError("Start Dates must of Date type")


def end_date(data, value):
    if isinstance(value, datetime):
        return data[data["expiration"] <= value]
    else:
        raise ValueError("End Dates must of Date type")


def expr_type(data, value):
    """
    Use all expirations, only standard or only non standard.
    Takes a list of expiration symbol types to include in the dataset.
    If none, includes all expiration types.

    For example:
    value = ["SPX", "SPXW"]
    """
    value = [value] if isinstance(value, str) else value

    mask = np.in1d(data["underlying_symbol"].values, value)
    filtered = data[mask]

    if filtered.empty:
        raise ValueError("No matching expiration types in dataset")

    return filtered


def entry_dte(data, value, min=None, max=None):
    """
    Days to expiration min and max for the trade to be considered.

    For example, it will search options that have days to expiration
    between and including 20 to 55.
    """
    groupby = ["option_type", "expiration", "underlying_symbol"]
    filtered = data.pipe(assign_dte).pipe(
        _process_values, "dte", value, min, max, groupby=groupby
    )

    if filtered.empty:
        logging.info(f"Nothing returned from filtering by entry_dte")
    return filtered


def entry_days(data, value, min=None, max=None):
    """
    Stagger trades every this many Entry Days.

    For example, there would be a new trade every 7 days from the last new trade.
    """
    pass


def delta(data, value, min=None, max=None):
    """
    Absolute value of a delta of an option.
    """
    if not isinstance(value, (int, float)):
        raise ValueError("Invalid value passed for delta")

    filtered = _process_values(data, "delta", value, min, max)
    if filtered.empty:
        logging.info(f"Nothing returned from filtering by delta")
    return filtered


def strike_pct(data, value, min=None, max=None):
    """
    Stock Percentage (strike / stock price).
    """
    if not isinstance(value, (int, float, tuple)):
        raise ValueError(f"Invalid value passed for entry strike percentage")
    return data.assign(
        strike_pct=lambda r: (r["strike"] / r["underlying_price"]).round(2)
    ).pipe(_process_values, "strike_pct", value, min, max)


def entry_spread_price(data, value, min=None, max=None):
    """
    The net price of the spread.

    For example, it would set a min max of $0.10 to $0.20 and find only spreads with prices
    within that range.
    """
    # TODO: Make this delta independant, may need to self join on legs to get every
    # possible combination of strike prices and filter on spread prices.
    return (
        data.groupby(["trade_num"])["entry_opt_price"]
        .sum()
        .to_frame(name="entry_opt_price")
        .pipe(
            _process_values, "entry_opt_price", value, min, max, groupby=["trade_num"]
        )
        .merge(data, left_index=True, right_index=True)
        .drop(["entry_opt_price_x"], axis=1)
        .rename(columns={"entry_opt_price_y": "entry_opt_price"})
    )


def entry_spread_delta(data, value, min=None, max=None):
    """
    The net delta of the spread.

    For example, it would set a min max of .30 to .40 and find only spreads with net deltas
    within that range.
    """
    pass


def entry_spread_yield(data, value, min=None, max=None):
    """
    Yield Percentage is (option max profit / option max loss).
    """
    pass


def exit_dte(data, value, min=None, max=None):
    """
    Exit the trade when the days to expiration left is equal to or below this.

    For example, it would exit a trade with 10 days to expiration.
    """

    exit_dte = 0 if value is "expire" else value

    if (value == min == max) or exit_dte == 0:
        return data[data["exit_dte"] == exit_dte]
    else:
        groupby = ["option_type", "expiration", "underlying_symbol"]
        return _process_values(data, "exit_dte", exit_dte, min, max, groupby=groupby)


def exit_hold_days(data, value, min=None, max=None):
    """
    Exit the trade when the trade was held this many days.

    For example, it would exit a trade when the trade has been held for 20 days.
    """
    pass


def exit_profit_loss_pct(data, value, min=None, max=None):
    """
    Take profits and add stop loss to exit trade at these intervals.

    For example, set a stop loss of 50 (-50%) and a profit target at 200 (200%) on a long call.
    Set only a stop loss by leaving profit blank.
    """
    pass


def exit_spread_delta(data, value, min=None, max=None):
    """
    Exit and roll the trade if the spread total delta exceed the min or max value. For Example;

    spread delta = leg1ratio * leg1delta + leg2ratio * leg2delta
    """
    pass


def exit_spread_price(data, value, min=None, max=None):
    """
    Exit the trade when the trade price falls below the min or rises above the max.

    For example, it would exit if below 0.4 min or above $0.90 max price.
    """
    pass


def extend_pandas_filters():
    PandasObject.calls = calls
    PandasObject.puts = puts
    PandasObject.start_date = start_date
    PandasObject.end_date = end_date
    PandasObject.expr_type = expr_type
    PandasObject.entry_dte = entry_dte
    PandasObject.entry_days = entry_days
    PandasObject.delta = delta
    PandasObject.strike_pct = strike_pct
    PandasObject.entry_spread_price = entry_spread_price
    PandasObject.entry_spread_delta = entry_spread_delta
    PandasObject.entry_spread_yield = entry_spread_yield
    PandasObject.exit_dte = exit_dte
    PandasObject.exit_hold_days = exit_hold_days
    PandasObject.exit_profit_loss_pct = exit_profit_loss_pct
    PandasObject.exit_spread_delta = exit_spread_delta
    PandasObject.exit_spread_price = exit_spread_price
