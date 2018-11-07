"""
The goal of this module is to abstract away dataframe manipulation
functions and provide an easy to use interface to query for specific
option legs in a dataframe. All functions will return a new pandas
dataframe to allow for method chaining
"""
from optopsy.enums import Period, OptionType
from optopsy.data import fields


calculated_fields = ['abs_dist', 'dte']
all_fields = [f[0] for f in fields] + calculated_fields
numeric_and_date_fields = [f[0] for f in fields if (f[2] == 'numeric' or f[2] == 'date')] \
    + calculated_fields


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
    if column not in numeric_and_date_fields:
        raise ValueError("Invalid column specified!")
    else:

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
    if column in numeric_and_date_fields:
        return df[df[column] <= _convert(val)]
    else:
        raise ValueError("Invalid column specified!")


def gte(df, column, val):
    if column in numeric_and_date_fields:
        return df[df[column] >= _convert(val)]
    else:
        raise ValueError("Invalid column specified!")


def eq(df, column, val):
    if column in all_fields:
        return df[df[column] == _convert(val)]
    else:
        raise ValueError("Invalid column specified!")


def lt(df, column, val):
    if column in numeric_and_date_fields:
        return df[df[column] < _convert(val)]
    else:
        raise ValueError("Invalid column specified!")


def gt(df, column, val):
    if column in numeric_and_date_fields:
        return df[df[column] > _convert(val)]
    else:
        raise ValueError("Invalid column specified!")


def ne(df, column, val):
    if column in numeric_and_date_fields:
        return df[df[column] != _convert(val)]
    else:
        raise ValueError("Invalid column specified!")


def between(df, column, start, end, inclusive=True):
    if column in numeric_and_date_fields:
        return df[df[column].between(
            _convert(start), _convert(end), inclusive=inclusive)]
    else:
        raise ValueError("Invalid column specified!")
