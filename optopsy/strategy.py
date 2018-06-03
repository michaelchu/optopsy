from abc import ABC, abstractmethod


class AbstractStrategy(ABC):

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def next(self):
        pass

    @abstractmethod
    def stop(self):
        pass


class Strategy(AbstractStrategy):

    def __init__(self, name, algos, children=None):
        pass

    def start(self):
        pass

    def next(self):
        pass

    def stop(self):
        pass



