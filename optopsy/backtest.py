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
import pandas as pd
import numpy as np

# import pyprind as py

from functools import reduce
from .calculations import calc_entry_px, calc_exit_px, calc_pnl, assign_trade_num
from itertools import product
from .helpers import assign_dte, inspect

pd.set_option("display.expand_frame_repr", False)

on = ["underlying_symbol", "option_type", "expiration", "strike"]

output_cols = {
    "quote_date_entry": "entry_date",
    "quote_date_exit": "exit_date",
    "delta_entry": "entry_delta",
    "underlying_price_entry": "entry_stk_price",
    "underlying_price_exit": "exit_stk_price",
    "dte_exit": "exit_dte",
}

output_format = [
    "entry_date",
    "exit_date",
    "expiration",
    "underlying_symbol",
    "exit_dte",
    "ratio",
    "contracts",
    "option_type",
    "strike",
    "entry_delta",
    "bid_entry",
    "ask_entry",
    "bid_exit",
    "ask_exit",
    "entry_stk_price",
    "exit_stk_price",
    "entry_opt_price",
    "exit_opt_price",
    "entry_price",
    "exit_price",
    "cost",
]


def backtest(strategy, data, **params):
    contracts = params.get("contracts", 1)

    mode = params.get("mode", "market")
    entry_mode = exit_mode = mode
    entry_mode = params.get("entry_mode", entry_mode)
    exit_mode = params.get("exit_mode", exit_mode)

    data = assign_dte(data)

    return (
        strategy.pipe(assign_dte)
        .pipe(calc_entry_px, entry_mode)
        .pipe(pd.merge, data, on=on, suffixes=("_entry", "_exit"))
        .rename(columns={"bid": "bid_exit", "ask": "ask_exit"})
        .assign(contracts=contracts)
        .round(2)
        .pipe(calc_exit_px, exit_mode)
        .pipe(calc_pnl)
        .rename(columns=output_cols)
        .sort_values(["entry_date", "expiration", "underlying_symbol", "strike"])
    )[output_format]
