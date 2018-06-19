import optopsy as op
from .filters import FilterStack


class Strategy(object):

    def __init__(self, name, option_strategy, filters=None):

        if not isinstance(option_strategy, op.OptionStrategy):
            raise ValueError("option_strategy parameter must be of OptionStrategy type!")

        if not isinstance(filters, list):
            raise ValueError("filters must of list type")

        self.name = name
        self.option_strategy = option_strategy

        self.spread_data = None
        self.filter_stack = FilterStack(self)
        self.filters = filters

        self.now = None
        self.bankrupt = False
        self.positions = {}

    def setup(self, data):
        # call the option object to construct the spread
        self.spread_data = self.option_strategy(data)

        # call on_setup for any custom initiation steps
        self.on_setup()

    def update(self, date):
        # current quote date
        self.now = date

        # we will slice our spread_data by today's date
        latest_quote = op.OptionQuery(self.spread_data.loc[self.now])

        # run entry filters against our current quote prices if defined
        if self.filters is not None:
            self.filter_stack(self, latest_quote)
        else:
            # if no filters provided, use the logic in the overridden on_update function
            self.on_update(latest_quote)

    def on_setup(self):
        pass

    def on_update(self, quote):
        pass

    def adjust(self, amount):
        pass

    def buy(self, order):
        pass

    def sell(self, order):
        pass