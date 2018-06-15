from .enums import FilterType
from .filters import FilterStack
import optopsy as op

class Strategy(object):

    def __init__(self, name, opt_strat, filters):

        if not isinstance(opt_strat, op.OptionStrategy):
            raise ValueError("opt_strat parameter must be of OptionStrategy type!")

        if not isinstance(filters, list):
            raise ValueError("filters must of list type")

        self.name = name

        self.entry_filters = [f for f in filters if f.type == op.FilterType.ENTRY]
        self.exit_filters = [f for f in filters if f.type == op.FilterType.EXIT]

        self.opt_strat = opt_strat

        self.spread_data = None
        self.latest_quote = None

        self.entry_stack = FilterStack(self.entry_filters)
        self.exit_stack = FilterStack(self.exit_filters)

        self.now = None
        self.bankrupt = False
        self.positions = {}

    def setup(self, data):
        # call the option object to construct the spread
        self.spread_data = self.opt_strat(data)

    def update(self, date):
        # current quote date
        self.now = date

        # we will slice our spread_data by today's date
        self.latest_quote = op.OptionQuery(self.spread_data.loc[self.now])

        # run entry filters against our current quote prices
        self.entry_stack(self)

        # if we have positions, run exit filters against our current positions
        if not self.positions:
            self.exit_stack(self)

    def adjust(self, amount):
        pass

    def buy(self, order):
        pass

    def sell(self, order):
        pass