from optopsy.backtester.position import Position


class Account(object):

    def __init__(self, init_bal=10000):

        # setup a new account with a default starting balance of 10000
        self.cash_balance = init_bal
        self.option_buying_power = self.cash_balance
        self.net_liquidity = self.cash_balance

        self.hold = 0
        self.positions = list()
        self.transactions = list()

    def set_balance(self, amount):
        self.cash_balance = amount

    def process_transaction(self, order):
        """
        Processes the order and convert it into a position held in this account.
        :param order:
        :return: None
        """
        self.cash_balance -= order.cost_of_trade
        print("Cash Balance: %s, Option Buying Power: %s" % (self.cash_balance, self.option_buying_power))

        # create a new position object and store it in the positions list
        self.positions.append(Position(order))

    def get_positions(self):
        """
        Returns a list of positions that are currently held in this account
        :return: list of positions
        """
        return self.positions

    def update_positions(self, quote):
        """
        Update the prices of positions held in the account and recalculate
        open P/L amounts, net liquidation values. Also remove expired orders
        :param quote:
        :return: None
        """
        pass
