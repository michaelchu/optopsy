from optopsy.globals import OrderAction


class DefaultOptionMargin(object):
    """
    This class emulates the margin calculations as defined by TD's thinkorswim platform.

    """

    def __init__(self, action, strikes, exp_label, total_cost):
        self.action = action
        self.cost = total_cost

        # split the labels by slash as it may contain more than one item
        self.strikes = strikes.split("/")
        self.exps = exp_label.split("/")

    def single(self):
        pass

    def vertical(self):

        strike_dist = abs(float(self.strikes[1]) - float(self.strikes[0]))

        if self.action == OrderAction.BTO or self.action == OrderAction.BTC:
            return self.cost
        else:
            # calculate margin for sell orders
            return (strike_dist * 100) - self.cost

    def iron_condor(self):
        pass
