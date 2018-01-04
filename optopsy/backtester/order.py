import random
from optopsy.globals import OrderStatus, OrderAction, OrderType


class Order(object):
    def __init__(self, date, strategy, action,
                 quantity, order_type, tif, limit_price
                 ):

        # Strategy specific properties
        self.date = date
        self.ticket = self.generate_ticket()
        self.symbol = strategy.get_one('symbol')
        self.underlying_symbol = strategy.get_one('underlying_symbol')
        self.underlying_price = strategy.get_one('underlying_price')
        self.name = strategy.get_one('name')
        self.strikes = strategy.get_one('strikes')
        self.exp_label = strategy.get_one('exp_label')
        self.expirations = self.exp_label.split("/")
        self.option_type = strategy.get_one('option_type').upper()

        # Order specific properties
        self.status = OrderStatus.WORKING
        self.quantity = quantity
        self.action = action
        self.order_type = order_type
        self.order_label = f"{self.name.upper()} {self.underlying_symbol} " \
                           f"{self.exp_label.upper()} {self.strikes} {self.option_type}"

        self.tif = tif

        # Pricing specific properties
        self.executed_price = None
        self.nat_price = None
        self.mid_price = None
        self.price = self.nat_price if limit_price is None else limit_price
        self.commissions = 0  # TODO: implement commission model
        self.cost_of_trade = self.total_cost_of_trade(self.price)
        self.set_prices(strategy)

    @staticmethod
    def generate_ticket():
        return random.randint(100000, 999999)

    def total_cost_of_trade(self, price):
        """
        Calculate the and set the cost of this order based on a price given by the broker
        :return: None
        """
        return (price * self.quantity * self.action.value[0] * 100) + self.commissions

    def set_prices(self, chains):
        """

        :param chains:
        :return:
        """
        # current market prices, used when order is submitted but not executed
        if self.action == OrderAction.BTO or self.action == OrderAction.BTC:
            self.nat_price = chains.get_one('order_ask')
            self.mid_price = chains.get_one('mark')
        elif self.action == OrderAction.STO or self.action == OrderAction.STC:
            self.nat_price = chains.get('order_bid')
            self.mid_price = chains.get_one('mark')

    def update_expiration(self, date):
        """
        Checks the current date against the expiration dates in this order.
        If any of the expiration dates is less than the current date, this order
        is expired
        :param date: date to check the expiration dates against
        :return: None
        """
        if any(d < date for d in self.expirations):
            self.status = OrderStatus.EXPIRED

    def update_quotes(self, quotes):
        """
        Update the order's symbols with current market values
        :params quotes: OptionQuery object of updated option symbols from broker
        """
        # update the mark value of the order
        updated_quotes = quotes.symbol(self.symbol)
        self.set_prices(updated_quotes)

    def print_status(self):
        print(f"{self.order_label} - Nat Price: {self.nat_price}, Mid Price: {self.mid_price}, Status: {self.status}")

    def __str__(self):

        if self.status == OrderStatus.WORKING or self.status == OrderStatus.REJECTED:
            if self.order_type == OrderType.LMT:
                order_price = "%s@%s" % (self.action.value[1], '{0:.2f}'.format(self.price))
            else:
                order_price = ""

            order_specs = f"{self.quantity} {order_price} {self.order_type.name} {self.tif.name}"

        elif self.status == OrderStatus.FILLED:
            order_price = "%s@%s" % (self.action.value[2], '{0:.2f}'.format(self.executed_price))
            order_specs = f"{self.quantity} {order_price}"

        return order_specs + " " + self.order_label
