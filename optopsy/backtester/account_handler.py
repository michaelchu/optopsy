from optopsy.backtester.account import Account


class AccountHandler(object):

    def __init__(self):
        """
        The AccountHandler holds the account objects created for
        each scenarios for the backtest. This collection of accounts
        will form the basis for creating the result set for the backtest.
        """
        self.account_list = list()
        self.account = Account()

    def set_account_balance(self, amount):
        """
        Sets the account cash balance to the specified amount
        :param amount: amount to set cash balance to
        :return: None
        """
        self.account.cash_balance = amount

    def update_portfolio_value(self):
        """
        Update the portfolio to reflect current market value as
        based on last bid/ask of each ticker.
        """
        self.account.update_positions()



