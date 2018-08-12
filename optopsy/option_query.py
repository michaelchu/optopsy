"""
The goal of this module is to abstract away dataframe manipulation
functions and provide an easy to use interface to query for specific
option legs in a dataframe. All functions will return a new pandas
dataframe to allow for method chaining
"""

import operator

from optopsy.enums import Period, OptionType


# QUERY METHODS ==========================================================
def puts(df_chain):
    """
    Filter the class' copy of the option chain for put options
    """
    return df_chain[df_chain['option_type'] == 'p']


def calls(df_chain):
    """
    Filter the class' copy of the option chain for call options
    """
    return df_chain[df_chain['option_type'] == 'c']


def opt_type(df_chain, option_type):
    """
    Filter the class' copy of the option chain for specified option type
    """

    if isinstance(option_type, OptionType):
        return df_chain[df_chain['option_type'] == option_type.value[0]]
    else:
        raise ValueError("option_type must be of type OptionType")


def underlying_price(df_chain):
    """
    Gets the underlying price info from the option chain if available
    :return: The average of all underlying prices that may have been
             recorded in the option chain for a given day. If no underlying
             price column is defined, throw and error
    """
    if 'underlying_price' in df_chain:
        dates = df_chain['underlying_price'].unique()
        return dates.mean()
    else:
        raise ValueError("Underlying Price column undefined!")


def nearest(df_chain, column, val, tie='roundup'):
    """
    Returns dataframe rows containing the column item nearest to the
    given value.
    :param df_chain: the dataframe to operate on
    :param column: column to look up value
    :param val: return values nearest to this param
    :param tie: round up or down when nearest to value is at the midpoint of a range
    :return: A new OptionQuery object with filtered dataframe

    """

    if _check_inputs(df_chain, column, val):
        kv = _convert(df_chain, column, val)

        df_chain['abs_dist'] = abs(df_chain[kv[0]] - kv[1])
        min_abs_dist = df_chain['abs_dist'].min()

        f_df = _compare(df_chain, 'abs_dist', operator.eq, min_abs_dist)
        f_df = f_df.drop(['abs_dist'], axis=1)

        if len(f_df) != 1:
            if tie == 'roundup':
                f_df = f_df[f_df[column] == f_df[column].max()]
            elif tie == 'rounddown':
                f_df = f_df[f_df[column] == f_df[column].min()]

        return f_df


def lte(df_chain, column, val):
    """
    Returns a dataframe with rows where column values are less than or
    equals to the val parameter
    :param df_chain: the dataframe to operate on
    :param column: column to look up value
    :param val: return values less than or equals to this param
    :return: A new OptionQuery object with filtered dataframe
    """
    if _check_inputs(df_chain, column, val):
        kv = _convert(df_chain, column, val)
        return _compare(df_chain, kv[0], operator.le, kv[1])
    else:
        return df_chain


def gte(df_chain, column, val):
    """
    Returns a dataframe with rows where column values are greater than or
    equals to the val parameter
    :param df_chain: the dataframe to operate on
    :param column: column to look up value
    :param val: return values greater than or equals to this param
    :return: A new OptionQuery object with filtered dataframe
    """
    if _check_inputs(df_chain, column, val):
        kv = _convert(df_chain, column, val)
        return _compare(df_chain, kv[0], operator.ge, kv[1])
    else:
        return df_chain


def eq(df_chain, column, val):
    """
    Returns a dataframe with rows where column values are
    equal to this param.
    :param df_chain: the dataframe to operate on
    :param column: column to look up value
    :param val: return values equals to this param amount
    :return: A new OptionQuery object with filtered dataframe
    """
    if _check_inputs(df_chain, column, val):
        kv = _convert(df_chain, column, val)
        return _compare(df_chain, kv[0], operator.eq, kv[1])
    else:
        return df_chain


def lt(df_chain, column, val):
    """
    Returns a dataframe with rows where column values are
    equal to this param.
    :param df_chain: the dataframe to operate on
    :param column: column to look up value
    :param val: return values less than this param amount
    :return: A new OptionQuery object with filtered dataframe
    """
    if _check_inputs(df_chain, column, val):
        kv = _convert(df_chain, column, val)
        return _compare(df_chain, kv[0], operator.lt, kv[1])
    else:
        return df_chain


def gt(df_chain, column, val):
    """
    Returns a dataframe with rows where column values are
    equal to this param.
    :param df_chain: the dataframe to operate on
    :param column: column to look up value
    :param val: return values greater than this param amount
    :return: A new OptionQuery object with filtered dataframe
    """
    if _check_inputs(df_chain, column, val):
        kv = _convert(df_chain, column, val)
        return _compare(df_chain, kv[0], operator.gt, kv[1])
    else:
        return df_chain


def ne(df_chain, column, val):
    """
    Returns a dataframe with rows where column values are
    equal to this param.
    :param df_chain: the dataframe to operate on
    :param column: column to look up value
    :param val: return values not equal to this param amount
    :return: A new OptionQuery object with filtered dataframe
    """
    if _check_inputs(df_chain, column, val):
        kv = _convert(df_chain, column, val)
        return _compare(df_chain, kv[0], operator.ne, kv[1])
    else:
        return df_chain


def between(df_chain, column, start, end, inclusive=True):
    """
    Returns a dataframe with rows where column values are
    equal to this param.
    :param df_chain: the dataframe to operate on
    :param column: column to look up value
    :param start: start of the range
    :param end: end of the range
    :param inclusive: include values specified in the comparison
    :return: A filtered dataframe
    """
    return df_chain[df_chain[column].between(
        start, end, inclusive=inclusive)]


def min(df_chain, column):
    """
    Return the row with the min value of the specified column
    :param df_chain: the dataframe to operate on
    :param column: column to look up min value
    :return: Series object containing row with min value of column
    """

    # TODO: check this works on a date field
    idx_min = df_chain[column].idxmin()
    return df_chain.iloc[[idx_min]]


def max(df_chain, column):
    """
    Return the row with the max value of the specified column
    :param df_chain: the dataframe to operate on
    :param column: column to look up min value
    :return: Series object containing row with max value of column
    """

    # TODO: check this works on a date field
    idx_max = df_chain[column].idxmax()
    return df_chain.iloc[[idx_max]]


# PRIVATE METHODS ========================================================
def _check_inputs(df_chain, column, val):
    """
    This method will validate the column name and values given into a function.
    Values types will be checked against the specified column to make sure the types match.
    :param df_chain: the dataframe to operate on
    :param column:
    :param val:
    :return:
    """

    # check if supplied column name exists
    if column not in df_chain.columns:
        raise ValueError(
            "Column: %s does not exist in option chain!" %
            column)

    # We do not allow comparisons on non date/numeric columns
    if df_chain[column].dtype == object:
        raise ValueError("Invalid column type used for comparison!")

    # TODO: Check if type of value matches the column's type

    return True


def _convert(df_chain, column, val):
    """
    In the use case where column and val are datetime and Period instances, respectively,
    change the column lookup to lookup 'dte' column and get the actual Period value from
    Period object.
    :param df_chain: the dataframe to operate on
    :param column: datetime column to lookup
    :param val: an Enum instance of Period
    :return: tuple of lookup column and val (converted if needed)
    """
    lookup_col = column

    if df_chain[column].dtype == 'datetime64[ns]':
        value = val.value if isinstance(val, Period) else val
        lookup_col = 'dte'
    else:
        value = float(val)

    return lookup_col, value


def _compare(df_chain, column, op, val):
    """
    Compares the column value to the val param using the operator passed in op param
    :param df_chain: the dataframe to operate on
    :param column: column to compare with
    :param op: operator to use for comparison, this is a Python Operator object
    :param val: value to compare with
    :return: The filtered option chain that matches the comparison criteria
    """
    return df_chain[op(df_chain[column], val)]
