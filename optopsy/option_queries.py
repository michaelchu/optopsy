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

from optopsy.data import fields
from optopsy.enums import Period, OptionType


def _convert(val):
    return val.value if isinstance(val, Period) else val


def _calc_abs_distance(row, column, val, absolute):
    col = abs(row[column]) if absolute else row[column]
    return abs(col - _convert(val))


def calls(df):
    return df[df.option_type.str.lower().str.startswith("c")]


def puts(df):
    return df[df.option_type.str.lower().str.startswith("p")]


def opt_type(df, option_type):
    if isinstance(option_type, OptionType):
        return df[df["option_type"] == option_type.value[0]]
    else:
        raise ValueError("option_type must be of type OptionType")


def underlying_price(df):
    if "underlying_price" in df:
        dates = df["underlying_price"].unique()
        return dates.mean()
    else:
        raise ValueError("Underlying Price column undefined!")


def nearest(df, column, val, groupby=None, absolute=True, tie="roundup"):
    # we need to group by unique option columns so that we are
    # getting the min abs dist over multiple sets of option groups
    # instead of the absolute min of the entire data set.
    if groupby is None:
        groupby = ["quote_date", "option_type", "expiration", "underlying_symbol"]

    on = groupby + ["abs_dist"]

    data = df.assign(abs_dist=lambda r: _calc_abs_distance(r, column, val, absolute))

    return (
        data.groupby(groupby)["abs_dist"]
        .min()
        .to_frame()
        .merge(data, on=on)
        .drop("abs_dist", axis=1)
    )


def lte(df, column, val):
    return df[df[column] <= _convert(val)]


def gte(df, column, val):
    return df[df[column] >= _convert(val)]


def eq(df, column, val):
    return df[df[column] == _convert(val)]


def lt(df, column, val):
    return df[df[column] < _convert(val)]


def gt(df, column, val):
    return df[df[column] > _convert(val)]


def ne(df, column, val):
    return df[df[column] != _convert(val)]


def between(df, column, start, end, inclusive=True, absolute=False):
    if absolute:
        temp_col = f"{column}_temp"
        df[temp_col] = abs(df[column])
    else:
        temp_col = column

    result = df[
        df[temp_col].between(_convert(start), _convert(end), inclusive=inclusive)
    ]
    return result.drop(temp_col, axis=1) if absolute else result
