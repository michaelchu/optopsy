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

import numpy as np
import pandas as pd
from pandas.core.base import PandasObject


def _agg_by(data, col):
    return data.groupby(["trade_num"])[col].sum()


def to_returns(data, init_balance=100000):
    window = np.insert(data["cost"].values, 0, init_balance, axis=0)
    return np.subtract.accumulate(window)


def calc_win_rate(data):
    grouped = _agg_by(data, "cost")
    wins = (grouped <= 0).sum()
    trades = total_trades(data)
    return wins / trades


def total_trades(data):
    return data.index.max() + 1


def total_profit(data):
    return data["cost"].multiply(-1).sum()


def expected_value(data):
    profit = avg_profit(data)
    loss = avg_loss(data)
    win_rate = calc_win_rate(data)
    loss_rate = 1 - win_rate

    return (profit * win_rate) + (loss * -1 * loss_rate)


def avg_profit(data):
    grouped = _agg_by(data, "cost")
    profits = grouped[grouped <= 0]

    if profits.empty:
        return 0
    return profits.multiply(-1).mean()


def avg_loss(data):
    grouped = _agg_by(data, "cost")
    losses = grouped[grouped > 0]

    if losses.empty:
        return 0
    return losses.mean()


def stats(data, round=2):
    output = calc_stats(data, transpose=True, round=round)
    print(output)
    return output


def trades(data, cols=None):
    if cols is None:
        cols = [
            "underlying_symbol",
            "expiration",
            "dte",
            "ratio",
            "contracts",
            "strike",
            "option_type",
            "entry_opt_price",
            "exit_opt_price",
            "cost",
        ]
    print(
        data[cols].rename(
            {
                "underlying_symbol": "symbol",
                "option_type": "type",
                "entry_opt_price": "entry_price",
                "exit_opt_price": "exit_price",
            },
            inplace=False,
            axis=1,
        )
    )


def calc_stats(data, fil=None, transpose=False, round=2):
    if data is not None:
        results = {
            "Profit": total_profit(data),
            "Win Rate": calc_win_rate(data),
            "Trades": total_trades(data),
            "Avg Profit": avg_profit(data),
            "Avg Cost": avg_loss(data),
            "Exp Val": expected_value(data),
        }
        if transpose:
            return (
                pd.DataFrame.from_records([results], index=["Results"])
                .transpose()
                .round(round)
            )
        elif fil is not None and not transpose:
            return {**results, **fil}
        else:
            return results
    else:
        print("No data was passed to results function")


def extend_pandas():
    PandasObject.to_returns = to_returns
    PandasObject.calc_win_rate = calc_win_rate
    PandasObject.stats = stats
    PandasObject.trades = trades
    PandasObject.total_trades = total_trades
    PandasObject.total_profit = total_profit
    PandasObject.avg_profit = avg_profit
    PandasObject.avg_loss = avg_loss
    PandasObject.expected_value = expected_value
