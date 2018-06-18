from .enums import FilterType
from .filters import FilterStack
import optopsy as op


class Strategy(object):

    def __init__(self, name, option_strategy, filters):

        if not isinstance(option_strategy, op.OptionStrategy):
            raise ValueError("option_strategy parameter must be of OptionStrategy type!")

        if not isinstance(filters, list):
            raise ValueError("filters must of list type")

        self.name = name
        self.option_strategy = option_strategy

        self.spread_data = None
        self.filter_stack = None
        self.filters = filters

        self.now = None
        self.bankrupt = False
        self.positions = {}

    def setup(self, data):
        # call the option object to construct the spread
        self.spread_data = self.option_strategy(data)
        self.filter_stack = FilterStack(self)

    def update(self, date):
        # current quote date
        self.now = date

        # we will slice our spread_data by today's date
        latest_quote = op.OptionQuery(self.spread_data.loc[self.now])

        # run entry filters against our current quote prices
        self.filter_stack(self, latest_quote)

    def adjust(self, amount):
        pass

    def buy(self, order):
        pass

    def sell(self, order):
        pass