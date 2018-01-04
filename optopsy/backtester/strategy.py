import datetime

from optopsy.backtester.event import OrderEvent
from optopsy.backtester.order import Order
from optopsy.core.options.option_query import OptionQuery
from optopsy.globals import OrderAction, OrderType, OrderTIF


class Strategy(object):
    """
    This is the base class that holds various functions that implement custom trading
    logic such as entry/exit strategies and other trading mechanics
    based on option greeks and prices.
    """

    def __init__(self, broker, account, sizer, queue, **params):

        self.queue = queue
        self.broker = broker
        self.account = account
        self.sizer = sizer

        # strategy specific variables
        self.start_date = None
        self.end_date = None
        self.name = "Custom Strategy"

        self.current_date = None
        self.current_quotes = None
        self.order_list = list()
        self.__dict__.update(params)
        self.on_init(**params)

    def add_option_strategy(self, symbol, strategy, **params):
        """
        Pass the parameters and option strategy to create to the broker

        :param symbol: the symbol for the option strategy
        :param strategy: the option strategy to add
        :return: None
        """
        self.broker.source(symbol, strategy, self.start_date, self.end_date, **params)

    def set_strategy_name(self, name):
        """
        Sets the name of the strategy for presentation.
        :param name: Name of strategy
        :return: None
        """
        self.name = name

    def set_balance(self, amount):
        """
        Set the cash balance of brokerage account

        :param amount: The cash amount to set for the trading account
        :return:
        """
        self.account.set_balance(amount)

    def set_sizer(self, sizer):
        """
        Set the sizer to use for this strategy.
        :param sizer: Sizer object to use
        :return: None
        """
        pass

    def set_start_date(self, year, month, day):
        """
        Set start date of backtest applied to the option expiration date only

        :param year: year of start date
        :param month: month of start date
        :param day: day of start date
        :return:
        """
        self.start_date = datetime.date(year=year, month=month, day=day).strftime("%Y-%m-%d")

    def set_end_date(self, year, month, day):
        """
        Set end date of backtest applied to the option expiration date only

        :param year: year of end date
        :param month: month of end date
        :param day: day of end date
        :return:
        """
        self.end_date = datetime.date(year=year, month=month, day=day).strftime("%Y-%m-%d")

    def is_invested(self):
        return len(self.positions) != 0

    def on_init(self, **params):
        raise NotImplementedError

    def on_data_event(self, event):
        self.current_date = event.date
        self.on_data(event.quotes)

    def on_data(self, data):
        raise NotImplementedError

    def on_fill_event(self, event):
        self.on_fill(event)

    def on_fill(self, event):
        pass

    def on_expired_event(self, event):
        self.on_expired(event)

    def on_expired(self, event):
        pass

    def on_rejected_event(self, event):
        self.on_rejected(event)

    def on_rejected(self, event):
        pass

    def place_order(self, strategy, action, quantity, order_type, price, tif):
        """
        Create an order event and place it in the queue

        :param strategy: OptionQuery object containing one row that describes the option strategy
        :param action: The order action for this order, OrderAction.BUY or OrderAction.SELL
        :param price: The limit price for this order
        :param order_type: The action of the order, BUY or SELL
        :param quantity: The amount to transaction, > 0 for buy < 0 for sell
        :param tif: time in force for the order
        :return: None
        """

        if isinstance(strategy, OptionQuery):

            if strategy.fetch().shape[0] != 1:
                raise ValueError("Invalid strategy passed to order method!")

            # set the quantity based on user input or automatically determined using sizer
            # TODO: Make this better
            if quantity is None:
                quantity = self.sizer.fixed()

            # create an order object for tracking this order
            order = Order(self.current_date, strategy, action, quantity,
                          order_type, tif, price)

            # create an new order event and place it in the queue
            event = OrderEvent(self.current_date, order)
            self.queue.put(event)
        else:
            raise ValueError("place_order method called with invalid 'strategy' argument type!")

    def buy_to_open(self, strategy, quantity=None, order_type=OrderType.MKT, price=None, tif=OrderTIF.GTC):
        self.place_order(strategy, OrderAction.BTO, quantity, order_type, price, tif)

    def sell_to_open(self, strategy, quantity=None, order_type=OrderType.MKT, price=None, tif=OrderTIF.GTC):
        self.place_order(strategy, OrderAction.STO, quantity, order_type, price, tif)

    def sell_to_close(self, strategy, quantity=None, order_type=OrderType.MKT, price=None, tif=OrderTIF.GTC):
        self.place_order(strategy, OrderAction.STC, quantity, order_type, price, tif)

    def buy_to_close(self, strategy, quantity=None, order_type=OrderType.MKT, price=None, tif=OrderTIF.GTC):
        self.place_order(strategy, OrderAction.BTC, quantity, order_type, price, tif)

