import pandas as pd
from .abstract_data_feed import AbstractDataFeed


class PandasFeed(AbstractDataFeed):

    def __init__(self, file_path=None):
        if file_path is None:
            raise ValueError()

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

    def next(self):
        pass
