import os
import sqlite3

import pandas as pd
import optopsy.globals as gb

from optopsy.datafeeds.base_adapter import BaseAdapter
from optopsy.core.options.option_query import OptionQuery

# pd.set_option('display.expand_frame_repr', False)
# pd.set_option('display.max_rows', None)


class SqliteAdapter(BaseAdapter):

    def __init__(self, path=None):

        self.path = path
        self.opt_params = (
            ('symbol', 0),
            ('underlying_symbol', 1),
            ('quote_date', 2),
            ('root', 1),
            ('expiration', 4),
            ('strike', 5),
            ('option_type', 6),
            ('open', -1),
            ('high', -1),
            ('low', -1),
            ('close', -1),
            ('trade_volume', 11),
            ('bid_size', -1),
            ('bid', 13),
            ('ask_size', -1),
            ('ask', 15),
            ('underlying_price', 16),
            ('iv', -1),
            ('delta', 18),
            ('gamma', 19),
            ('theta', 20),
            ('vega', 21),
            ('rho', 22),
            ('open_interest', -1)
        )

    def get(self, symbol, start=None, end=None):
        """
        Data provider wrapper around pandas read_sql_query for sqlite database.

        :param symbol: symbol to download option data for
        :param start: start date to retrieve data from
        :param end: end date to retrieve data to
        :return: Dataframe containing option chains
        """

        if self.path is None:
            # use default path if no path given
            path = os.path.join(os.sep, gb.PROJECT_DIR, gb.DATA_SUB_DIR, gb.DB_NAME + ".db")

        try:
            data_conn = sqlite3.connect(path)
            query = 'SELECT * FROM %s_option_chain WHERE "root" = "%s"' % (symbol, symbol)

            # may need to apply chunk size if loading large option chain set
            data = pd.read_sql_query(query, data_conn, parse_dates=["quote_date"])

            # normalize dataframe columns
            data = self.normalize(data, self.opt_params)

            # slice the data set by start and end dates
            if start is not None and end is not None:
                data = data[(data['expiration'] >= start) & (data['expiration'] <= end)]
            elif start is None and end is not None:
                data = data[data['expiration'] <= end]
            elif end is None and start is not None:
                data = data[data['expiration'] >= start]

            return OptionQuery(data)

        except IOError as err:
            raise IOError(err)

