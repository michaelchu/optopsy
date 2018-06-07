class Strategy(object):

    def __init__(self, name, opt_strat, *filters):

        self.name = name
        self.filters = filters
        self.opt_strat = opt_strat
        self.bankrupt = False

    def update(self, date):
        print(date)

    def adjust(self, amount):
        pass



