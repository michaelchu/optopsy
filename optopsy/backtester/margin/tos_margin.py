from optopsy.backtester.margin.base import AbstractOptionMargin
from optopsy.globals import OrderAction


class TOSOptionMargin(AbstractOptionMargin):

    def single(self, action, strikes, exp_label):
        pass

    def vertical(self, cost_of_trade, action, strikes, exp_label):

        exps_strikes = AbstractOptionMargin.parse_exp_strikes(exp_label, strikes)
        strike_dist = abs(float(exps_strikes[1][0]) - float(exps_strikes[1][1]))

        if action == OrderAction.BTO or action == OrderAction.BTC:
            return cost_of_trade
        else:
            # calculate margin for sell orders
            return (strike_dist * 100) - cost_of_trade

    def iron_condor(self, cost_of_trade, action, strikes, exp_label):
        raise NotImplementedError("Should implement iron_condor()")

    def covered_stock(self, cost_of_trade, action, strikes, exp_label):
        raise NotImplementedError("Should implement covered_stock()")

    def diagonal(self, cost_of_trade, action, strikes, exp_label):
        raise NotImplementedError("Should implement diagonal()")

    def double_diagonal(self, cost_of_trade, action, strikes, exp_label):
        raise NotImplementedError("Should implement double_diagonal()")

    def calendar(self, cost_of_trade, action, strikes, exp_label):
        raise NotImplementedError("Should implement calendar()")

    def straddle(self, cost_of_trade, action, strikes, exp_label):
        raise NotImplementedError("Should implement straddle()")

    def strangle(self, cost_of_trade, action, strikes, exp_label):
        raise NotImplementedError("Should implement strangle()")

    def combo(self, cost_of_trade, action, strikes, exp_label):
        raise NotImplementedError("Should implement combo()")

    def back_ratio(self, cost_of_trade, action, strikes, exp_label):
        raise NotImplementedError("Should implement back_ratio()")

    def butterfly(self, cost_of_trade, action, strikes, exp_label):
        raise NotImplementedError("Should implement butterfly()")

    def stocks(self, cost_of_trade, action, strikes, exp_label):
        raise NotImplementedError("Should implement stocks()")