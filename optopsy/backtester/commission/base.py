from abc import ABC, abstractmethod


class AbstractCommissions(ABC):

    def __init__(self, comm_type):
        self.comm_type = comm_type

    @abstractmethod
    def options(self):
        raise NotImplementedError("Should implement options()")

    @abstractmethod
    def stocks(self):
        raise NotImplementedError("Should implement stocks()")