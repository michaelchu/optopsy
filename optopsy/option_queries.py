"""
The goal of this module is to abstract away dataframe manipulation
functions and provide an easy to use interface to query for specific
option legs in a dataframe. All functions will return a new pandas
dataframe to allow for method chaining
"""
from optopsy.enums import Period, OptionType
from optopsy.data import fields

CALCULATED_FIELDS = ['abs_dist', 'dte']
ALL_FIELDS = [f[0] for f in fields] + CALCULATED_FIELDS
NUMERIC_AND_DATE_FIELDS = [
    f[0] for f in fields if (f[2] == 'numeric' or f[2] == 'date')
] + CALCULATED_FIELDS


# PRIVATE METHODS ========================================================
def _convert(val):
    return val.value if isinstance(val, Period) else val


# QUERY METHODS ==========================================================
def calls(df):
    """
    Filter the class' copy of the option chain for call options
    """
    return df[df.option_type.str.lower().str.startswith('c')]


def puts(df):
    """
    Filter the class' copy of the option chain for put options
    """
    return df[df.option_type.str.lower().str.startswith('p')]


def opt_type(df, option_type):
    """
    Filter the class' copy of the option chain for specified option type
    """
    if isinstance(option_type, OptionType):
        return df[df['option_type'] == option_type.value[0]]
    else:
        raise ValueError("option_type must be of type OptionType")


def underlying_price(df):
    """
    Gets the underlying price info from the option chain if available
    :return: The average of all underlying prices that may have been
             recorded in the option chain for a given day. If no underlying
             price column is defined, throw and error
    """
    if 'underlying_price' in df:
        dates = df['underlying_price'].unique()
        return dates.mean()
    else:
        raise ValueError("Underlying Price column undefined!")


def nearest(df, column, val, tie='roundup', absolute=False):
    """
    Returns dataframe rows containing the column item nearest to the
    given value.
    :param df: the dataframe to operate on
    :param column: column to look up value
    :param val: return values nearest to this param
    :param tie: round up or down when nearest to value is at the midpoint of a range
    :return: A new OptionQuery object with filtered dataframe
    """
    if column in NUMERIC_AND_DATE_FIELDS:

        if absolute:
            data = df.assign(abs_dist=lambda r: abs(abs(r[column]) - _convert(val)))
        else:
            data = df.assign(abs_dist=lambda r: abs(r[column] - _convert(val)))

        results = (
            df
            .assign(abs_dist=lambda r: abs(r[column] - _convert(val)))
            .pipe(eq, 'abs_dist', data['abs_dist'].min())
            .drop(['abs_dist'], axis=1)
        )

        if tie == 'roundup' and len(results) != 1:
            return results[results[column] == results[column].max()]
        elif tie == 'rounddown' and len(results) != 1:
            return results[results[column] == results[column].min()]
        else:
            return results
    else:
        raise ValueError("Invalid column specified!")


def lte(df, column, val):
    """
    Returns a dataframe with rows where column values are less than or
    equals to the val parameter
    :param df: the dataframe to operate on
    :param column: column to look up value
    :param val: return values less than or equals to this param
    :return: A new OptionQuery object with filtered dataframe
    """
    if column in NUMERIC_AND_DATE_FIELDS:
        return df[df[column] <= _convert(val)]
    else:
        raise ValueError("Invalid column specified!")


def gte(df, column, val):
    """
    Returns a dataframe with rows where column values are greater than or
    equals to the val parameter
    :param df: the dataframe to operate on
    :param column: column to look up value
    :param val: return values greater than or equals to this param
    :return: A new OptionQuery object with filtered dataframe
    """
    if column in NUMERIC_AND_DATE_FIELDS:
        return df[df[column] >= _convert(val)]
    else:
        raise ValueError("Invalid column specified!")


def eq(df, column, val):
    """
    Returns a dataframe with rows where column values are
    equal to this param.
    :param df: the dataframe to operate on
    :param column: column to look up value
    :param val: return values equals to this param amount
    :return: A new OptionQuery object with filtered dataframe
    """
    if column in ALL_FIELDS:
        return df[df[column] == _convert(val)]
    else:
        raise ValueError("Invalid column specified!")


def lt(df, column, val):
    """
    Returns a dataframe with rows where column values are
    equal to this param.
    :param df: the dataframe to operate on
    :param column: column to look up value
    :param val: return values less than this param amount
    :return: A new OptionQuery object with filtered dataframe
    """
    if column in NUMERIC_AND_DATE_FIELDS:
        return df[df[column] < _convert(val)]
    else:
        raise ValueError("Invalid column specified!")


def gt(df, column, val):
    """
    Returns a dataframe with rows where column values are
    equal to this param.
    :param df: the dataframe to operate on
    :param column: column to look up value
    :param val: return values greater than this param amount
    :return: A new OptionQuery object with filtered dataframe
    """
    if column in NUMERIC_AND_DATE_FIELDS:
        return df[df[column] > _convert(val)]
    else:
        raise ValueError("Invalid column specified!")


def ne(df, column, val):
    """
    Returns a dataframe with rows where column values are
    equal to this param.
    :param df: the dataframe to operate on
    :param column: column to look up value
    :param val: return values not equal to this param amount
    :return: A new OptionQuery object with filtered dataframe
    """
    if column in NUMERIC_AND_DATE_FIELDS:
        return df[df[column] != _convert(val)]
    else:
        raise ValueError("Invalid column specified!")


def between(df, column, start, end, inclusive=True):
    """
    Returns a dataframe with rows where column values are
    equal to this param.
    :param df: the dataframe to operate on
    :param column: column to look up value
    :param start: start of the range
    :param end: end of the range
    :param inclusive: include values specified in the comparison
    :return: A filtered dataframe
    """
    if column in NUMERIC_AND_DATE_FIELDS:
        return df[df[column].between(
            _convert(start), _convert(end), inclusive=inclusive)]
    else:
        raise ValueError("Invalid column specified!")
