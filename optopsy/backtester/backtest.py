import collections
import itertools
import queue
import time

from optopsy.backtester.account_handler import AccountHandler
from optopsy.backtester.broker import BaseBroker
from optopsy.backtester.event import EventType
from optopsy.backtester.margin.option_margin import TOSOptionMargin
from optopsy.backtester.sizer.fixed import FixedPositionSizer
from optopsy.datafeeds.sqlite_adapter import SqliteAdapter


class Backtest(object):
    def __init__(self, strategy, datafeed=None, path=None,
                 margin_rules=None, sizer=None, **params):

        # initialize backtest components
        self.queue = queue.Queue()
        self.account_handler = AccountHandler()
        self.datafeed = datafeed
        self.path = path

        # initialize strategy components
        self.margin_rules = margin_rules
        self.sizer = sizer
        self.strategy = strategy
        self.params = params
        self.strategies = list()

        self._set_default_configs()
        self._generate_scenarios()

    def _set_default_configs(self):

        if self.datafeed is None:
            self.datafeed = SqliteAdapter(self.path)

        if self.sizer is None:
            self.sizer = FixedPositionSizer()

        if self.margin_rules is None:
            self.margin_rules = TOSOptionMargin()

        self.broker = BaseBroker(self.queue, self.datafeed, self.margin_rules)

    def _generate_scenarios(self):
        # apply cartesian product of all params to generate all
        # combinations of strategies to test for
        opt_keys = list(self.params)

        vals = self._iterize(self.params.values())
        opt_vals = itertools.product(*vals)
        o_kwargs1 = map(zip, itertools.repeat(opt_keys), opt_vals)
        opt_kwargs = map(dict, o_kwargs1)

        it = itertools.product([self.strategy], opt_kwargs)
        for strat in it:
            self.strategies.append(strat)

    def _iterize(self, iterable):
        """
        Handy function which turns things into things that can be iterated upon
        including iterables
        :param iterable:
        """
        niterable = list()
        for elem in iterable:
            if isinstance(elem, str):
                elem = (elem,)
            elif not isinstance(elem, collections.Iterable):
                elem = (elem,)
            niterable.append(elem)

        return niterable

    def run(self):

        # program timer
        program_starts = time.time()

        for scenario in self.strats:
            # initialize a new instance strategy from the strategy list
            # initialize an account instance for each scenario to keep track of results
            account = self.account_handler.create_account()
            strategy = scenario[0](self.broker, self.queue, **scenario[1])

            while self.broker.continue_backtest:
                # run backtesting loop
                try:
                    event = self.queue.get(False)
                except queue.Empty:
                    self.broker.stream_next()
                else:
                    if event is not None:
                        if event.event_type == EventType.DATA:
                            # update account holding's open P/L
                            account.update_positions(event)
                            # update broker's working order with current prices
                            self.broker.update_orders(event)
                            # update strategy instance with current data
                            strategy.on_data_event(event)
                        elif event.event_type == EventType.ORDER:
                            # send the order to the broker for processing
                            self.broker.process_order(event)
                        elif event.event_type == EventType.FILL:
                            # notify the strategy that we have a fill on one of its orders
                            strategy.on_fill_event(event)
                        elif event.event_type == EventType.REJECTED:
                            strategy.on_rejected_event(event)
                        else:
                            raise NotImplementedError("Unsupported event.type '%s'" % event.type)

            # Clear broker orders for next scenario
            self.broker.reset()

        program_ends = time.time()
        print("The simulation ran for {0} seconds.".format(round(program_ends - program_starts, 2)))
