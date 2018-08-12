from .option_query import *


class OptionStrategy:

    cols = ['symbol',
            'expiration',
            'quote_date',
            'strike_1',
            'strike_2',
            'strike_3',
            'strike_4',
            'bid',
            'ask',
            'mark',
            'delta',
            'gamma',
            'theta',
            'vega',
            'rho',
            'dte'
            ]

    @staticmethod
    def single(data, option_type):
        """
        This class simulates a single option position. Either a call or put of an underlying asset
        """
        chains = (
            OptionQuery.opt_type(data, option_type)
            .assign(mark=lambda r: r[['bid', 'ask']].mean(axis=1),
                    dte=lambda r: (r['expiration'] - r['quote_date']).dt.days,
                    strike_1=lambda r: r['strike'])
            .set_index('quote_date', drop=False, inplace=False)
        )

        chains = chains.loc[:, chains.columns.isin(OptionStrategy.cols)]
        chains = chains.reindex_axis(sorted(chains.columns), axis=1)

        return chains

    @staticmethod
    def vertical(data, option_type, width):
        """
        The vertical spread is an option spread strategy whereby the
        option trader purchases a certain number of options and simultaneously
        sell an equal number of options of the same class, same underlying security,
        same expiration date, but at a different strike price.
        """

        if width <= 0:
            return {False, "Width cannot be less than or equal 0"}

        # we create a join key (strike_key) to join on
        left_keys = ['quote_date', 'expiration', 'option_type', 'strike_key']
        right_keys = ['quote_date', 'expiration', 'option_type', 'strike']

        # here we get all the option chains based on option type
        chains = (
            data
            .pipe(OptionQuery.opt_type, option_type)
            .assign(strike_key=lambda r: r['strike'] + (width * option_type.value[1]))
            .merge(data, left_on=left_keys, right_on=right_keys,suffixes=('', '_shifted'))
            .assign(symbol=lambda r: r['symbol'] + '-' + r['symbol_shifted'],
                    bid=lambda r: r['bid'] - r['ask_shifted'],
                    ask=lambda r: r['ask'] - r['bid_shifted'],
                    mark=lambda r: round((r['bid'] + r['ask']) / 2, 2),
                    dte=lambda r: (r['expiration'] - r['quote_date']).dt.days
                    )
            .set_index('quote_date', inplace=False, drop=False)
        )

        for greek in ['delta', 'theta', 'gamma', 'vega', 'rho']:
            if greek in chains.columns:
                chains[greek] = chains[greek] - chains[greek + "_shifted"]

        return chains.loc[:, chains.columns.isin(OptionStrategy.cols)]

    @staticmethod
    def iron_condor(data, width, c_width, p_width):
        """
        The iron condor is an option trading strategy utilizing two vertical spreads
        a put spread and a call spread with the same expiration and four different strikes.
        """

        if width <= 0 or c_width <= 0 or p_width <= 0:
            raise ValueError("Widths cannot be less than or equal 0")

    @staticmethod
    def covered_stock(data):
        pass

    @staticmethod
    def calender(data):
        pass

    @staticmethod
    def butterfly(data):
        pass

    @staticmethod
    def diagonal(data):
        pass
