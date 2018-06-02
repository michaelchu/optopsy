from abc import ABC, abstractmethod


class AbstractDataFeed(ABC):

    @abstractmethod
    def _start(self):
        """
        Opens the CSV files containing the equities ticks from
        the specified CSV data directory, converting them into
        them into a pandas DataFrame, stored in a dictionary.
        :return:
        """
        pass

    @abstractmethod
    def next(self):
        pass
