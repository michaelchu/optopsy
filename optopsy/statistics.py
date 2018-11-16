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


def _assign_opt_px(data, mode, action):
    if mode == "midpoint":
        data[f"{action}_opt_price"] = data[[f"bid_{action}", f"ask_{action}"]].mean(axis=1)
    elif mode == "market":
        data[f"{action}_opt_price"] = data[f"ask_{action}"]
    return data


def assign_trade_num(data):
    groupby = ["entry_date", "expiration", "underlying_symbol"]
    data["trade_num"] = data.groupby(groupby).ngroup()
    data.set_index("trade_num", inplace=True)
    return data
    

def calc_entry_px(data, mode="midpoint"):
    return _assign_opt_px(data, mode,'entry')


def calc_exit_px(data, mode="midpoint"):
    return _assign_opt_px(data, mode, 'exit')


def calc_pnl(data):
    # calculate the p/l for the trades
    data["entry_price"] = data["entry_opt_price"] * data["ratio"] * data["contracts"]
    data["exit_price"] = data["exit_opt_price"] * data["ratio"] * data["contracts"]
    data["profit"] = data["exit_price"] - data["entry_price"]
    return data


def calc_total_profit(data):
    return data["profit"].sum().round(2)
