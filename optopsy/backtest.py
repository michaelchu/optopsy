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
from .filters import filter_data
from .option_queries import opt_type
from .statistics import calc_entry_px, calc_exit_px, assign_trade_num, calc_pnl
import pandas as pd
import optopsy.filters as fil

pd.set_option("display.expand_frame_repr", False)


on = ["underlying_symbol", "option_type", "expiration", "strike"]

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
    "cost",
]


def _create_legs(data, leg):
    return data.pipe(opt_type, option_type=leg[0]).assign(ratio=leg[1])


def _do_dedupe(spread, groupby, col, mode):
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
        return spread.groupby(groupby)[col].min().to_frame().merge(spread, on=on)
    else:
        return spread.groupby(groupby)[col].max().to_frame().merge(spread, on=on)


def _dedup_rows_by_cols(spreads, cols, groupby=None, mode="max"):
    return reduce(lambda i, c: _do_dedupe(spreads, groupby, c, mode), cols, spreads)


def create_spread(data, leg_structs, entry_filters, entry_spread_filters, mode):
    legs = [_create_legs(data, leg) for leg in leg_structs]
    return (
        filter_data(legs, entry_filters)
        .rename(columns={"bid": "bid_entry", "ask": "ask_entry"})
        .pipe(calc_entry_px, mode)
        .pipe(filter_data, entry_spread_filters)
        .pipe(_dedup_rows_by_cols, ["delta", "strike"])
        .pipe(assign_trade_num, ["quote_date", "expiration", "underlying_symbol"])
    )


# this is the main function that runs the backtest engine
def simulate(spreads, data, exit_filters, exit_spread_filters, mode):
    # for each option to be traded, determine the historical price action
    res = (
        pd.merge(spreads, data, on=on, suffixes=("_entry", "_exit"))
        .pipe(filter_data, exit_filters)
        .rename(columns={"bid": "bid_exit", "ask": "ask_exit"})
        .pipe(calc_exit_px, mode)
        .pipe(calc_pnl)
        .pipe(filter_data, exit_spread_filters)
        .rename(columns=output_cols)
        .sort_values(["entry_date", "expiration", "underlying_symbol", "strike"])
        .pipe(assign_trade_num, ["entry_date", "expiration", "underlying_symbol"])
    )

    return res[output_format]
