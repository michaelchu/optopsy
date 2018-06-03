from abc import ABC, abstractmethod


class AbstractDataFeed(ABC):

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def next(self):
        pass

    def fetch(self, strategy_name):
        pass
