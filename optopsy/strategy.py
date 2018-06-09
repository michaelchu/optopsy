class Strategy(object):

    def __init__(self, name, opt_strat, *filters):

        self.name = name
        self.filters = filters
        self.opt_strat = opt_strat
        self.bankrupt = False
        self.spread_data = None
        self.now = None
        
    def setup(self, data):
        # call the option object to construct the spread
        self.opt_strat(data, self)
        print(self.spread_data.head())

    def update(self, date):
        # current quote dat
        self.now = date

    def adjust(self, amount):
        pass



