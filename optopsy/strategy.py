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
        self.spread_data = self.opt_strat(data)

    def update(self, date):
        # current quote date
        self.now = date
        print(self.now)

        # we will slice our spread_data by today's date

        # run entry filters against our current quote prices

        # if we have positions, run exit filters against our current positions

    def adjust(self, amount):
        pass



