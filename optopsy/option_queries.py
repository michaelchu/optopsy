"""
The goal of this module is to abstract away dataframe manipulation
functions and provide an easy to use interface to query for specific
option legs in a dataframe. All functions will return a new pandas
dataframe to allow for method chaining
"""
from optopsy.data import fields
from optopsy.enums import Period, OptionType


def _convert(val):
    return val.value if isinstance(val, Period) else val


def _calc_abs_distance(row, column, val, absolute):
    col = abs(row[column]) if absolute else row[column]
    return abs(col - _convert(val))


def calls(df):
    return df[df.option_type.str.lower().str.startswith('c')]


def puts(df):
    return df[df.option_type.str.lower().str.startswith('p')]


def opt_type(df, option_type):
    if isinstance(option_type, OptionType):
        return df[df['option_type'] == option_type.value[0]]
    else:
        raise ValueError("option_type must be of type OptionType")


def underlying_price(df):
    if 'underlying_price' in df:
        dates = df['underlying_price'].unique()
        return dates.mean()
    else:
        raise ValueError("Underlying Price column undefined!")


def nearest(df, column, val, absolute=True):
    # we need to group by unique option columns so that we are
    # getting the min abs dist over multiple sets of option groups
    # instead of the absolute min of the entire data set.
    group_by = ['quote_date', 'option_type', 'expiration']
    on = group_by + ["abs_dist"]

    data = df.assign(
        abs_dist=lambda r:
        _calc_abs_distance(r, column, val, absolute)
    )

    return (
        data
        .groupby(group_by)['abs_dist'].min()
        .to_frame()
        .merge(data, on=on)
        .drop('abs_dist', axis=1)
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
    if column in numeric_and_date_fields:
        return df[df[column] > _convert(val)]
    else:
        raise ValueError("Invalid column specified!")


def ne(df, column, val):
    return df[df[column] != _convert(val)]


def between(df, column, start, end, inclusive=True, absolute=False):
    if absolute:
        temp_col = f"{column}_temp"
        df[temp_col] = abs(df[column])
    else:
        temp_col = column

    result = df[df[temp_col].between(
        _convert(start), _convert(end), inclusive=inclusive)]
    return result.drop(temp_col, axis=1) if absolute else result
