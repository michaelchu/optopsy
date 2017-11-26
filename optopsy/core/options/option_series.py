import numpy as np
import pandas as pd
# from mpl_toolkits.mplot3d import axes3d
# import matplotlib.pyplot as plt

pd.set_option('display.expand_frame_repr', False)
pd.set_option('display.max_rows', None)


class OptionSeries(object):
    """
    This class contains the time series data for an option strategy.
    """

    def __init__(self, data):
        """
        Initialize this class with a dataframe of option strategy prices by
        symbol, quote date, expiration, mark, other metrics, etc

        This class will then store the data in a dictionary by expiration dates
        and provide methods that will act on this data.

        :param data: option chain data for the constructed option strategy
        """
        if not isinstance(data, pd.DataFrame):
            raise ValueError('data param must be of pandas type DataFrame')

        self.data = data

    def scatter_plot(self, exp=None):
        """
        Create a scatter plot that compares time and price points during the life of the option spread.
        :param exp: Expiration of spreads to plot for, if None, aggregates all expiration dates into one plot
        :return: None
        """
        pass

    def surface_plot(self, exp_date):
        """
        Plot this OptionSeries with a surface plot for an expiration cycle.
        :param exp_date: The expiration to plot for
        :return:
        """

        data = self.pivot()[exp_date]
        x = data.columns
        y = data.index
        X, Y = np.meshgrid(x, y)
        Z = data

        fig = plt.figure()
        ax = fig.gca(projection='3d')
        ax.plot_surface(X, Y, Z, linewidth=0)

        plt.show()

    def pivot(self, dropna=True):
        """
        Return a dict with expiration as keys and pivoted option chain data as values
        :return: Dict with pivoted data by expiration dates
        """
        chains = {}
        # group data by expiration date into a dictionary of pivoted option prices
        for exp in self.data['expiration'].unique():
            data_slice = self.data.loc[self.data['expiration'] == exp]
            data_pivot = data_slice.pivot(index='symbol', columns='quote_date', values='mark')

            # reset dataframe labels and column names to be numeric
            data_pivot.columns = [i for i in range(data_pivot.shape[1])]
            data_pivot.reset_index(inplace=True)
            if dropna:
                data_pivot.dropna(inplace=True)

            # drop either symbol or spread_symbol columns depending on strategy
            data_pivot.drop('symbol', axis=1, inplace=True)
            chains[str(exp)[:10]] = data_pivot

        return chains

    def slice(self, date):
        """
        Return a slice of the data where quote date is the specified date
        :param date: Date to return data for
        :return: Dataframe of option chains where trade date equals date params
        """

        return self.data.loc[self.data['quote_date'] == date]

    def get_quote_dates(self):
        """
        Returns a list of unique quote dates for this option series, we convert the dates
        from Numpy.datetime64 to string date in the format: 'Y%-m%-d%'
        :return: Array of unique quote dates
        """
        return [str(t)[:10] for t in self.data['quote_date'].unique()]

