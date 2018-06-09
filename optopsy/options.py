from .option_query import *


class Option(object):

    def __init__(self, name=None):
        self.name = name
        self.columns = ['symbol', 'name', 'underlying_symbol', 'underlying_price', 'quote_date', 'expiration',
                        'strikes', 'option_type', 'volume', 'mark', 'order_bid', 'order_ask']


class Single(Option):

    def __init__(self, option_type):
        super(Single, self).__init__('Single')
        self.option_type = option_type

    def __call__(self, data, target):
        # here we generate a single option strategy based on input and assign the results to the target
        target.spread_data = OptionQuery(data).option_type(self.option_type).fetch()


class Vertical(Option):

    def __init__(self, option_type, width):
        super(Vertical, self).__init__('Vertical')
        self.option_type = option_type
        self.width = width

    def __call__(self, data, target):
        # here we get all the option chains based on option type
        chains = OptionQuery(data).option_type(self.option_type).fetch()

        # shift only the strikes since this is a vertical spread, we create a join key (strike_key) to join on
        chains['strike_key'] = chains['strike'] + (self.width * self.option_type.value[1])
        left_keys = ['quote_date', 'expiration', 'root', 'option_type', 'strike_key']
        right_keys = ['quote_date', 'expiration', 'root', 'option_type', 'strike']

        # here we do a self join to the table itself joining by strike key, essentially we are
        # shifting the strikes to create the vertical spread
        chains = chains.merge(chains, left_on=left_keys, right_on=right_keys, suffixes=('', '_shifted'))

        chains['symbol'] = '.' + chains['symbol'] + '-.' + chains['symbol_shifted']
        chains['order_bid'] = chains['bid'] - chains['ask_shifted']
        chains['order_ask'] = chains['ask'] - chains['bid_shifted']
        chains['exp_label'] = chains['expiration'].dt.strftime('%d %b %y')
        chains['mark'] = round((chains['order_bid'] + chains['order_ask']) / 2, 2)
        chains['volume'] = chains['trade_volume'] + chains['trade_volume_shifted']


class IronCondor(Option):

    def __init__(self, data):
        super(IronCondor, self).__init__('Iron Condor')


class ShortPut(Option):

    def __init__(self, data):
        super(ShortPut, self).__init__(data)


class LongCallSpread(Option):

    def __init__(self, data, width):
        super(LongCallSpread, self).__init__(data)
        self.width = width


class ShortCallSpread(Option):

    def __init__(self, data, width):
        super(ShortCallSpread, self).__init__(data)
        self.width = width


class LongPutSpread(Option):

    def __init__(self, data, width):
        super(LongPutSpread, self).__init__(data)
        self.width = width


class ShortPutSpread(Option):

    def __init__(self, data, width):
        super(ShortPutSpread, self).__init__(data)
        self.width = width


class LongIronCondor(Option):

    def __init__(self, data, width, width_c, width_p):
        super(LongIronCondor, self).__init__(data)
        self.width = width
        self.width_c = width_c
        self.width_p = width_p


class ShortIronCondor(Option):

    def __init__(self, data, width, width_c, width_p):
        super(ShortIronCondor, self).__init__(data)
        self.width = width
        self.width_c = width_c
        self.width_p = width_p
