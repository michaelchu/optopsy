from .option_query import *


class Option(object):
    """
    This class represents a option spread object
    """

    def __init__(self, name=None):
        self.name = name
        self.cols = ['symbol',
                     'expiration',
                     'quote_date',
                     'bid',
                     'ask',
                     'mark',
                     'delta',
                     'gamma',
                     'theta',
                     'vega',
                     'rho'
                     ]


class Single(Option):
    """
    This class simulates a single option position. Either a call or put of an underlying asset
    """

    def __init__(self, **params):
        super(Single, self).__init__('Single')
        self.option_type = params.pop('option_type', 'c')

    def __call__(self, data):
        # get spread params from user or set default if not given
        chains = OptionQuery(data).option_type(self.option_type).fetch()
        chains['mark'] = (chains['bid'] + chains['ask']) / 2

        return chains.loc[:, chains.columns.isin(self.cols)]


class Vertical(Option):
    """
    The vertical spread is an option spread strategy whereby the
    option trader purchases a certain number of options and simultaneously
    sell an equal number of options of the same class, same underlying security,
    same expiration date, but at a different strike price.
    """

    def __init__(self, **params):
        super(Vertical, self).__init__('Vertical')

        # get spread params from user or set default if not given
        self.option_type = params.pop('option_type', 'c')
        self.width = params.pop('width', 2)

        if not self.width > 0:
            raise ValueError("Width cannot be less than 0")

    def __call__(self, data):
        # here we get all the option chains based on option type
        chains = OptionQuery(data).option_type(self.option_type).fetch()

        # shift only the strikes since this is a vertical spread,
        # we create a join key (strike_key) to join on
        chains['strike_key'] = chains['strike'] + (self.width * self.option_type.value[1])
        left_keys = ['quote_date', 'expiration', 'root', 'option_type', 'strike_key']
        right_keys = ['quote_date', 'expiration', 'root', 'option_type', 'strike']

        # here we do a self join to the table itself joining by strike key, essentially we are
        # shifting the strikes to create the vertical spread
        chains = chains.merge(chains, left_on=left_keys, right_on=right_keys,
                              suffixes=('', '_shifted'))

        chains['symbol'] = '.' + chains['symbol'] + '-.' + chains['symbol_shifted']
        chains['bid'] = chains['bid'] - chains['ask_shifted']
        chains['ask'] = chains['ask'] - chains['bid_shifted']
        chains['mark'] = round((chains['bid'] + chains['ask']) / 2, 2)

        return chains.loc[:, chains.columns.isin(self.cols)]


class IronCondor(Option):
    """
    The iron condor is an option trading strategy utilizing two vertical spreads
    a put spread and a call spread with the same expiration and four different strikes.
    """

    def __init__(self, option_type, width, c_width, p_width):
        super(IronCondor, self).__init__('Iron Condor')
        self.option_type = option_type
        self.width = width
        self.c_width = c_width
        self.p_width = p_width

    def __call__(self, data):

        if self.width <= 0 or self.c_width <= 0 or self.p_width <= 0:
            raise ValueError("Widths cannot be less than or equal 0")

        chains = OptionQuery(data)

        # chains = chain.lte('expiration', dte)
        call_chains = chains.calls().fetch()
        put_chains = chains.puts().fetch()

        # shift only the strikes since this is a vertical spread
        call_chains['strike_key'] = call_chains['strike'] + (
                self.c_width * OptionType.CALL.value[1])
        put_chains['strike_key'] = put_chains['strike'] + (self.p_width * OptionType.PUT.value[1])

        left_keys = ['quote_date', 'expiration', 'root', 'option_type', 'strike_key']
        right_keys = ['quote_date', 'expiration', 'root', 'option_type', 'strike']

        # CALL SIDE ================================================================================
        call_side = call_chains.merge(call_chains, left_on=left_keys, right_on=right_keys,
                                      suffixes=('', '_shifted'))

        call_side['symbol'] = '.' + call_side['symbol'] + '-.' + call_side['symbol_shifted']
        call_side['mark'] = ((call_side['bid'] - call_side['ask_shifted']) +
                             (call_side['ask'] - call_side['bid_shifted'])) / 2
        call_side['volume'] = call_side['trade_volume'] + call_side['trade_volume_shifted']

        # PUT SIDE =================================================================================
        put_side = put_chains.merge(put_chains, left_on=left_keys, right_on=right_keys,
                                    suffixes=('', '_shifted'))

        put_side['symbol'] = '.' + put_side['symbol'] + '-.' + put_side['symbol_shifted']
        put_side['mark'] = ((put_side['bid'] - put_side['ask_shifted']) +
                            (put_side['ask'] - put_side['bid_shifted'])) / 2
        put_side['volume'] = put_side['trade_volume'] + put_side['trade_volume_shifted']
        put_side['strike_key'] = put_side['strike'] + self.width

        # MERGED ===================================================================================
        call_side_keys = ['quote_date', 'underlying_symbol', 'expiration', 'root', 'strike']
        put_side_keys = ['quote_date', 'underlying_symbol', 'expiration', 'root', 'strike_key']

        chains = call_side.merge(put_side, left_on=call_side_keys, right_on=put_side_keys,
                                 suffixes=('_c', '_p'))
        chains['symbol'] = chains['symbol_c'] + '+' + chains['symbol_p']
        chains['mark'] = chains['mark_c'] + chains['mark_p']
        chains['exp_label'] = chains['expiration'].dt.strftime('%d %b %y')

        new_col = ['symbol', 'name', 'underlying_symbol', 'quote_date', 'expiration', 'exp_label',
                   'volume', 'mark']

        for greek in ['delta', 'theta', 'gamma', 'vega', 'rho']:
            if greek in chains.columns:
                chains[greek] = chains[greek] - chains[greek + "c_shifted"]
                new_col.append(greek)

        return chains[new_col]


class CoveredStock(Option):

    def __init__(self, data):
        super(CoveredStock, self).__init__(data)

    def __call__(self, data):
        pass


class Calender(Option):

    def __init__(self, data, width):
        super(Calender, self).__init__(data)
        self.width = width

    def __call__(self, data):
        pass


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
