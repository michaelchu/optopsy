import os


class BaseCSVFeed(object):
    """
    Parses a CSV file according to the order and field presence defined by the parameters
    This class will take care of opening the file and reading the file into a dataframe
    """

    params = (
        ('nullvalue', float('NaN')),
        ('dtformat', '%Y-%m-%d %H:%M:%S'),
        ('tmformat', '%H:%M:%S'),

        ('symbol', 0),
        ('quote_date', 1),
        ('expiration', 2),
        ('type', 3),
        ('strike', 4),
        ('bid', 5),
        ('ask', 6),
        ('volume', 7),
        ('open_interest', 8),
        ('implied_vol', 9),
        ('delta', 10),
        ('gamma', 11),
        ('theta', 12),
        ('vega', 13),
        ('underlying_price', 14),
    )

    def __init__(self, dataname=None, fromdate=None, todate=None):
        self.dataname = dataname
        self.fromdate = fromdate
        self.todate = todate

    def _start(self, ticker):
        """
        Opens the CSV files containing the equities ticks from
        the specified CSV data directory, converting them into
        them into a pandas DataFrame, stored in a dictionary.
        """
        pass
