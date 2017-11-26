from abc import ABC, abstractmethod


class AbstractPositionSizer(ABC):

    def __init__(self, broker, account):
        self.broker = broker
        self.account = account

    @abstractmethod
    def size_order(self, order, account):
        raise NotImplementedError("Should implement size_order()")




