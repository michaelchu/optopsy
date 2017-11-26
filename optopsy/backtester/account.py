from optopsy.backtester.position import Position


class Account(object):

    def __init__(self, init_bal=10000):

        # setup a new account with a default starting balance of 10000
        self.cash_balance = init_bal
        self.option_buying_power = self.cash_balance
        self.net_liquidity = self.cash_balance
        self.positions = list()

    def set_balance(self, amount):
        self.cash_balance = amount

    def update(self, quote):
        """
        Update the prices of positions held in the account and recalculate
        open P/L amounts, net liquidation values
        :param quote:
        :return:
        """
        pass

    def process_order(self, order):
        self.cash_balance -= order.cost_of_trade()
        print("Cash Balance: %s, Option Buying Power: %s" % (self.cash_balance, self.option_buying_power))

        # create a new position object and store it in the positions list
        self.positions.append(Position(order))
