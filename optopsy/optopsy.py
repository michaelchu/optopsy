from .broker import Broker


class Optopsy(object):

    def __init__(self):
        self.broker = Broker()
        self.feed = None

    def add_strategy(self, params):
        pass

    def add_data(self, feed):
        pass

    def run(self):
        pass

