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

from functools import reduce

import pandas as pd

import optopsy.filters as fil
from .option_queries import opt_type
from .statistics import *

pd.set_option("display.expand_frame_repr", False)


on = ["underlying_symbol", "option_type", "expiration", "strike"]

default_entry_filters = {
    "std_expr": False,
    "contract_size": 10,
    "entry_dte": (27, 30, 31),
    "exit_dte": None,
}

output_cols = {
    "quote_date_entry": "entry_date",
    "quote_date_exit": "exit_date",
    "delta_entry": "entry_delta",
    "underlying_price_entry": "entry_stk_price",
    "underlying_price_exit": "exit_stk_price",
    "dte_entry": "dte",
}

output_format = [
    "entry_date",
    "exit_date",
    "expiration",
    "underlying_symbol",
    "dte",
    "ratio",
    "contracts",
    "option_type",
    "strike",
    "entry_delta",
    "entry_stk_price",
    "exit_stk_price",
    "entry_opt_price",
    "exit_opt_price",
    "entry_price",
    "exit_price",
    "profit",
]


def _create_legs(data, leg):
    return data.pipe(opt_type, option_type=leg[0]).assign(ratio=leg[1])


def _apply_filters(legs, filters):
    if not filters:
        return legs
    else:
        return [
            reduce(lambda l, f: getattr(fil, f)(l, filters[f], idx), filters, leg)
            for idx, leg in enumerate(legs)
        ]


def _filter_data(data, filters):
    data = data if isinstance(data, list) else [data]
    return pd.concat(_apply_filters(data, filters))


def create_spread(data, leg_structs, filters):
    legs = [_create_legs(data, leg) for leg in leg_structs]

    # merge and apply leg filters to create spread
    filters = {**default_entry_filters, **filters}
    entry_filters = {
        f: filters[f]
        for f in filters
        if (not f.startswith("entry_spread") and not f.startswith("exit_"))
    }
    spread = _filter_data(legs, entry_filters)

    # apply spread level filters to spread
    spread_filters = {f: filters[f] for f in filters if f.startswith("entry_spread")}
    return _filter_data(spread, spread_filters)


# this is the main function that runs the backtest engine
def run(data, trades, filters, init_balance=10000, mode="midpoint"):
    # for each option to be traded, determine the historical price action
    filters = {**default_entry_filters, **filters}
    exit_filters = {f: filters[f] for f in filters if f.startswith("exit_")}
    res = (
        pd.merge(trades, data, on=on, suffixes=("_entry", "_exit"))
        .pipe(_filter_data, exit_filters)
        .pipe(calc_entry_px, mode)
        .pipe(calc_exit_px, mode)
        .pipe(calc_pnl)
        .rename(columns=output_cols)
        .sort_values(["entry_date", "expiration", "underlying_symbol", "strike"])
        .pipe(assign_trade_num)
    )

    return calc_total_profit(res), res[output_format]
