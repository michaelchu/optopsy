from optopsy.backtester.event import DataEvent
from optopsy.core.options.option_query import OptionQuery


class OptionChainIterator(object):
    def __init__(self, dates, data):
        """
        Create an iterator with optionSeries data to be fed to the strategy.
        :param dates: An array of merged quote dates for all symbols added
        :param data: A dictionary of symbols with their OptionSeries object
        """
        # data is a dict with symbol as key, OptionSeries object as value
        self.data = data
        self.dates = iter(dates)

    def __iter__(self):
        return self

    def __next__(self):
        try:
            data_slice = {}
            quote_date = next(self.dates)
            # return a data event containing the daily quote for option chains
            for sym in self.data:
                data_slice[sym] = OptionQuery(self.data[sym].slice(quote_date))
            # create the data event and return it
            return DataEvent(quote_date, data_slice)
        except StopIteration:
            raise
