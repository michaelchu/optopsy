import pandas as pd
from abc import ABC, abstractmethod


class AbstractDataFeed(ABC):
    # All data feeds should have a default list of data fields, with
    # position set to -1 to be defined by the feed itself
    default_params = (
        {'symbol', -1},
        {'underlying_price', -1},
        {'option_symbol', -1},
        {'option_type', -1},
        {'expiration', -1},
        {'quote_date', -1},
        {'strike', -1},
        {'bid', -1},
        {'ask', -1},
        {'volume', -1},
        {'oi', -1},
        {'iv', -1},
        {'delta', -1},
        {'gamma', -1},
        {'theta', -1},
        {'vega', -1},
        {'rho', -1}
    )

    @abstractmethod
    def start(self):
        """
        This method will be called by Optopsy at the beginning of a backtest
        to setup option strategy prices to be used during backtest
        :return:
        """
        pass

    @abstractmethod
    def next(self, data):
        """
        This method will provide a handle to retrieve the current quote date's option
        strategy prices and information.
        :param data: a dataframe containing the current quote date's option strategy price
        :return:
        """
        pass

    def fetch(self, strategy_name):
        """
        Here we fetch the option strategy data to be used by the strategy
        :param strategy_name:
        :return:
        """
        pass


class PandasFeed(AbstractDataFeed):

    def __init__(self, file_path=None, **struct):
        if file_path is None:
            raise ValueError()

        print(self.default_params)

        self.file_path = file_path
        self.data = None

    def start(self):
        """
        This method will read in the data file using pandas and assign the
        normalized dataframe to the class's data variable.

        Normalization means to map columns from data source to a standard
        column name that will be used in this program.
        """

        columns = list()
        col_names = list()

        df = pd.read_csv(self.file_path)

        for col in self.params:
            if col[1] != -1:
                columns.append(col[1])
                col_names.append(col[0])

        dataframe = df.iloc[:, columns]
        dataframe.columns = col_names

        self.data = dataframe.set_index('quote_date')


        self.fetch()

    def next(self, data):
        pass
