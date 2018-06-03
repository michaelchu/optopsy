from .broker import Broker


class Optopsy(object):

    def __init__(self):
        self.broker = Broker()
        self.feed = None
        self.strategy = None

    def add_strategy(self, filters):
        self.strategy = filters

    def add_data(self, feed):
        self.feed = feed

    def run(self):
        """
        Here we will generate a list of strategies to execute based on any optimization
        parameters given in filters.
        :return:
        """

        # first we set our data feed
        self.feed.start()
        print(self.feed.data.head())

