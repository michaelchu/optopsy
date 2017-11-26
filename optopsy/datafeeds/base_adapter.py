class BaseAdapter(object):

    def __init__(self, path):

        self.path = path

    def get(self, symbol, start=None, end=None):
        raise NotImplementedError

    def normalize(self, dataframe, params):
        """
        Normalize column names using opt_params defined in this class. Normalization
        means to map columns from data source that may have different names for the same
        columns to a standard column name that will be used in this program.

        :param dataframe: the pandas dataframe containing data from the data source
        :param params: the list of option attributes to map with
        :return: dataframe with the columns renamed with standard column names and unnecessary
                 (mapped with -1) columns dropped
        """
        columns = list()
        col_names = list()

        for col in params:
            if col[1] != -1:
                columns.append(col[1])
                col_names.append(col[0])

        dataframe = dataframe.iloc[:, columns]
        dataframe.columns = col_names

        return dataframe
