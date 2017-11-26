import random
from optopsy.globals import OrderStatus, OrderAction, OrderType


class Order(object):
    def __init__(self, date, strategy, action,
                 quantity, order_type, tif, limit_price, margin_rules
                 ):

        # Strategy specific properties
        self.date = date
        self.ticket = self.generate_ticket()
        self.underlying_symbol = strategy.get_one('underlying_symbol')
        self.underlying_price = strategy.get_one('underlying_price')
        self.name = strategy.get_one('name')
        self.strikes = strategy.get_one('strikes')
        self.exp_label = strategy.get_one('exp_label')
        self.option_type = strategy.get_one('option_type').upper()

        # Order specific properties
        self.status = OrderStatus.WORKING
        self.quantity = quantity
        self.action = action
        self.order_type = order_type
        self.mark = strategy.get_one('mark')
        self.tif = tif

        # Pricing specific properties
        self.price = limit_price
        self.executed_price = None

        # current market prices, used when order is submitted but not executed
        if self.action == OrderAction.BTO or self.action == OrderAction.BTC:
            self.nat_price = strategy.get_one('order_ask')
            self.mid_price = self.mark
        elif self.action == OrderAction.STO or self.action == OrderAction.STC:
            self.nat_price = strategy.get('order_bid')
            self.mid_price = self.mark

        # broker specific properties
        self.commissions = 0  # TODO: implement commission model
        self.total_cost = self.cost_of_trade()

        self.margin_rules = margin_rules(self.action, self.strikes, self.exp_label, self.total_cost)

        # calculate the margin of this order
        margin_func = getattr(self.margin_rules, self.name)
        self.margin = margin_func()

    def cost_of_trade(self):
        """ Calculate the cost of this order including commissions """
        cost_of_trade = (self.price * self.quantity * self.action.value[0] * 100) + self.commissions
        return cost_of_trade

    @staticmethod
    def generate_ticket():
        return random.randint(100000, 999999)

    def update(self, quotes):
        """
        Update the order's symbols with current market values
        :params quotes: DataFrame of updated option symbols from broker
        """
        # update the mark value of the order
        pass

    def __str__(self):

        order_label = f"{self.name.upper()} {self.underlying_symbol} " \
                      f"{self.exp_label.upper()} {self.strikes} {self.option_type}"

        if self.status == OrderStatus.WORKING or self.status == OrderStatus.REJECTED:
            if self.order_type == OrderType.LMT:
                order_price = "%s@%s" % (self.action.value[1], '{0:.2f}'.format(self.price))
            else:
                order_price = ""

            order_specs = f"{self.quantity} {order_price} {self.order_type.name} {self.tif.name}"

        elif self.status == OrderStatus.FILLED:
            order_price = "%s@%s" % (self.action.value[2], '{0:.2f}'.format(self.price))
            order_specs = f"{self.quantity} {order_price}"

        return order_specs + " " + order_label
