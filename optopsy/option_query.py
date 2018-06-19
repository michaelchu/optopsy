"""
This class takes a dataframe of option chains and
returns a subset based on convenience methods provided
by this class to filter for specific option legs.
"""
import operator

import pandas as pd

from optopsy.enums import Period, OptionType


class OptionQuery(object):
    """
    The goal of this class is to abstract away dataframe manipulation
    functions and provide an easy to use interface to query for specific
    option legs in a dataframe. All functions will return a new pandas
    dataframe to allow for method chaining
    """

    def __init__(self, option_chain, inplace=False):
        # Create a copy of the option chain dataframe to prevent modifying
        # the original dataframe and to able to reuse it for other queries

        if not isinstance(option_chain, pd.DataFrame):
            raise ValueError("Invalid dataframe used to initialize OptionQuery")

        self.oc = option_chain.copy() if not inplace else option_chain
        self.oc.reset_index(drop=True, inplace=True)

        # create dte column if not present
        if 'dte' not in self.oc.columns:
            # convert date columns to pandas datetime
            self.oc.loc[:, 'quote_date'] = pd.to_datetime(self.oc['quote_date'])
            self.oc.loc[:, 'expiration'] = pd.to_datetime(self.oc['expiration'])

            # calculate the difference between expiration date and quote date
            dte = self.oc['expiration'] - self.oc['quote_date']
            self.oc['dte'] = dte.dt.days

    # QUERY METHODS ================================================================================

    def puts(self):
        """
        Filter the class' copy of the option chain for put options
        """
        chain = self.oc
        chain = chain[chain.option_type.str.contains('p', case=False)]
        return OptionQuery(chain)

    def calls(self):
        """
        Filter the class' copy of the option chain for call options
        """
        chain = self.oc
        chain = chain[chain.option_type.str.contains('c', case=False)]
        return OptionQuery(chain)

    def option_type(self, option_type):
        """
        Filter the class' copy of the option chain for specified option type
        """

        if isinstance(option_type, OptionType):
            chain = self.oc
            chain = chain[chain.option_type.str.contains(option_type.value[0], case=False)]
            return OptionQuery(chain)
        else:
            raise ValueError("option_type must be of type OptionType")

    def underlying_price(self):
        """
        Gets the underlying price info from the option chain if available
        :return: The average of all underlying prices that may have been
                 recorded in the option chain for a given day. If no underlying
                 price column is defined, throw and error
        """
        if 'underlying_price' in self.oc.columns:
            dates = self.oc['underlying_price'].unique()
            return dates.mean()
        else:
            raise ValueError("Underlying Price column undefined!")

    def nearest(self, column, val, tie='roundup'):
        """
        Returns dataframe rows containing the column item nearest to the
        given value.

        :param column: column to look up value
        :param val: return values nearest to this param
        :param tie: round up or down when nearest to value is at the midpoint of a range
        :return: A new OptionQuery object with filtered dataframe

        """

        if self._check_inputs(column, val):
            kv = self._convert(column, val)

            self.oc['abs_dist'] = abs(self.oc[kv[0]] - kv[1])
            min_abs_dist = self.oc['abs_dist'].min()

            f_df = self._compare('abs_dist', operator.eq, min_abs_dist)
            f_df = f_df.drop(['abs_dist'], axis=1)

            if len(f_df) != 1:
                if tie == 'roundup':
                    f_df = f_df[f_df[column] == f_df[column].max()]
                elif tie == 'rounddown':
                    f_df = f_df[f_df[column] == f_df[column].min()]

            return OptionQuery(f_df)

    def lte(self, column, val):
        """
        Returns a dataframe with rows where column values are less than or
        equals to the val parameter

        :param column: column to look up value
        :param val: return values less than or equals to this param
        :return: A new OptionQuery object with filtered dataframe
        """
        if self._check_inputs(column, val):
            kv = self._convert(column, val)
            return OptionQuery(self._compare(kv[0], operator.le, kv[1]))

    def gte(self, column, val):
        """
        Returns a dataframe with rows where column values are greater than or
        equals to the val parameter

        :param column: column to look up value
        :param val: return values greater than or equals to this param
        :return: A new OptionQuery object with filtered dataframe
        """
        if self._check_inputs(column, val):
            kv = self._convert(column, val)
            return OptionQuery(self._compare(kv[0], operator.ge, kv[1]))

    def eq(self, column, val):
        """
        Returns a dataframe with rows where column values are
        equal to this param.

        :param column: column to look up value
        :param val: return values equals to this param amount
        :return: A new OptionQuery object with filtered dataframe
        """
        if self._check_inputs(column, val):
            kv = self._convert(column, val)
            return OptionQuery(self._compare(kv[0], operator.eq, kv[1]))

    def lt(self, column, val):
        """
        Returns a dataframe with rows where column values are
        equal to this param.

        :param column: column to look up value
        :param val: return values less than this param amount
        :return: A new OptionQuery object with filtered dataframe
        """
        if self._check_inputs(column, val):
            kv = self._convert(column, val)
            return OptionQuery(self._compare(kv[0], operator.lt, kv[1]))

    def gt(self, column, val):
        """
        Returns a dataframe with rows where column values are
        equal to this param.

        :param column: column to look up value
        :param val: return values greater than this param amount
        :return: A new OptionQuery object with filtered dataframe
        """
        if self._check_inputs(column, val):
            kv = self._convert(column, val)
            return OptionQuery(self._compare(kv[0], operator.gt, kv[1]))

    def ne(self, column, val):
        """
        Returns a dataframe with rows where column values are
        equal to this param.

        :param column: column to look up value
        :param val: return values not equal to this param amount
        :return: A new OptionQuery object with filtered dataframe
        """
        if self._check_inputs(column, val):
            kv = self._convert(column, val)
            return OptionQuery(self._compare(kv[0], operator.ne, kv[1]))

    def between(self, column, start, end, inclusive=True):
        """
        Returns a dataframe with rows where column values are
        equal to this param.

        :param column: column to look up value
        :param val: return values not equal to this param amount
        :return: A new OptionQuery object with filtered dataframe
        """
        return OptionQuery(self.oc[self.oc[column].between(start, end, inclusive=inclusive)])

    def min(self, column):
        """
        Return the row with the min value of the specified column
        :param column: column to look up min value
        :return: Series object containing row with min value of column
        """

        # TODO: check this works on a date field
        idx_min = self.oc[column].idxmin()
        return OptionQuery(self.oc.iloc[[idx_min]])

    def max(self, column):
        """
        Return the row with the max value of the specified column
        :param column: column to look up min value
        :return: Series object containing row with max value of column
        """

        # TODO: check this works on a date field
        idx_max = self.oc[column].idxmax()
        return OptionQuery(self.oc.iloc[[idx_max]])

    # GET METHODS ==================================================================================

    def get(self, column):
        """
        Returns the specified column's unique values in an array
        """
        return self.oc[column].unique()

    def get_one(self, column):
        """
        Returns the specified column's value, this assumes the dataframe has
        one row.
        :param column: the column to look up row value from
        """
        if self.oc.shape[0] == 1:
            return self.oc[column][0]
        else:
            raise ValueError("Cannot get value of dataframe column with more than one row.")

    def is_empty(self):
        """
        Returns true if there is at least 1 row in option chain, else false
        :return:
        """
        return True if self.oc.shape[0] == 0 else False

    # PRIVATE METHODS ==============================================================================
    def _check_inputs(self, column, val):
        """
        This method will validate the column name and values given into a function.
        Values types will be checked agains the specified column to make sure the types match.

        :param column:
        :param val:
        :return:
        """

        # check if supplied column name exists
        if not column in self.oc.columns:
            raise ValueError("Column: %s does not exist in option chain!" % column)

        # We do not allow comparisons on non date/numeric columns
        if self.oc[column].dtype == object:
            raise ValueError("Invalid column type used for comparison!")

        # TODO: Check if type of value matches the column's type

        return True

    def _convert(self, column, val):
        """
        In the use case where column and val are datetime and Period instances, respectively,
        change the column lookup to lookup 'dte' column and get the actual Period value from
        Period object.

        :param column: datetime column to lookup
        :param val: an Enum instance of Period
        :return: tuple of lookup column and val (converted if needed)
        """
        lookup_col = column

        if self.oc[column].dtype == 'datetime64[ns]':
            value = val.value if isinstance(val, Period) else val
            lookup_col = 'dte'
        else:
            value = float(val)

        return lookup_col, value

    def _strip(self):
        """
        Remove unnecessary columns, used for final output of fetch functions
        """
        return self.oc.drop(['dte'], axis=1)

    def _compare(self, column, op, val):
        """
        Compares the column value to the val param using the operator passed in op param

        :param column: column to compare with
        :param op: operator to use for comparison, this is a Python Operator object
        :param val: value to compare with
        :return: The filtered option chain that matches the comparison criteria
        """
        return self.oc[op(self.oc[column], val)]

    # OUTPUT METHODS ===============================================================================

    def fetch(self):
        """
        Return all rows of this object's option chain
        """
        return self._strip()
