from .broker import Broker
from .strategy import Strategy


class Optopsy(object):

    def __init__(self, strategy):
        self.broker = Broker()
        self.feed = list()
        self.strategy = strategy
        self.run_configs = list()

    def add_data(self, feed):
        self.feed.append(feed)

    def run(self):
        """
        Here we will generate a list of strategies to execute based on any optimization
        parameters given in filters.
        :return:
        """

        # Generate all run configurations based on any optimization parameters
        # configurations will be stored like so: ((Strategy,
        for config in self.run_configs:
            # initialize a strategy instance with the current combination of parameters
            strategy = Strategy(config[0], config[1])

            # For each run configuration we set our data feed to match the data requested
            self.feed.start(config[0].opt_strategy)


