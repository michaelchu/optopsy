from datetime import timedelta, datetime
import pandas as pd

from optopsy.core.options.option_query import OptionQuery
from optopsy.core.options.option_series import OptionSeries
from optopsy.globals import OptionType, Period, OptionStrategy

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)


class OptionStrategies(object):
    """
    Static methods to define option strategies
    """

    @staticmethod
    def check_args(params, args):
        """
        Checks the incoming params specified by the user against the
        expected arguments for the option strategy. If any arguments
        are missing, use the default values provided by args dict.

        :param params: The params provided by the user for this strategy
        :param args: The default arguments for the specified strategy
        :return: updated dict with args
        """

        diff = set(params.keys()) - set(args.keys())
        if diff:
            raise ValueError("Invalid arguments provided for option strategy!")

        args.update(params)
        return args

    @staticmethod
    def generate_name(symbol, strategy_name, options_type, expiration, strikes):
        opt_type = options_type.upper()
        exp = datetime.strptime(expiration, '%Y-%m-%d').strftime('%d %b %y')
        return f"{strategy_name} {symbol} 100 {exp} {strikes} {opt_type}"

    @staticmethod
    def single(chain, **params):
        """
        This method simulates a single option position.

        :param chain: dataframe of option chain data
        :param params: The params provided by the user for this strategy
        :return:
        """

        # check and set default params if none are specified
        args = {'option_type': OptionType.CALL, 'dte': Period.ONE_WEEK}
        option_params = OptionStrategies.check_args(params, args)

        option_type = option_params['option_type']
        dte = option_params['dte']

        # retrieve the options data and store in dataframe
        chains = chain.option_type(option_type).lte('expiration', dte).fetch()

        # calculate option attributes
        chains['symbol'] = '.' + chains['symbol']
        chains['name'] = OptionStrategy.SINGLE.value

        chains['order_bid'] = chains['bid']
        chains['order_ask'] = chains['ask']
        chains['mark'] = (chains['order_bid'] + chains['order_ask']) / 2
        chains['exp_label'] = chains['expiration'].dt.strftime('%d %b %y')
        chains['strikes'] = chains['strike'].astype(str)
        chains['volume'] = chains['trade_volume']

        new_col = ['symbol', 'name', 'underlying_symbol', 'underlying_price', 'quote_date', 'expiration',
                   'exp_label', 'strikes', 'option_type', 'volume', 'mark', 'order_bid', 'order_ask']

        # if greeks are provided in the data source, add them to the dataframe
        for greek in ['delta', 'theta', 'gamma', 'vega', 'rho']:
            if greek in chains.columns:
                new_col.append(greek)

        return OptionSeries(chains[new_col])

    @staticmethod
    def vertical(chain, **params):
        """
        The vertical spread is an option spread strategy whereby the
        option trader purchases a certain number of options and simultaneously
        sell an equal number of options of the same class, same underlying security,
        same expiration date, but at a different strike price.

        :param chain: Dataframe of option chain data
        :param params: option_type: the option type to use
                       width: Distance in value between the strikes to construct vertical spreads with.
                       dte: date to expiration
        :return: A new dataframe containing all vertical spreads created from dataframe
        """

        # check and set default params if none are specified
        args = {'option_type': OptionType.CALL, 'dte': Period.ONE_WEEK, 'width': 1}
        option_params = OptionStrategies.check_args(params, args)

        option_type = option_params['option_type']
        dte = option_params['dte']
        width = option_params['width']

        if width <= 0:
            raise ValueError("Width of vertical spreads cannot be less than or equal 0")
        else:

            chains = chain.option_type(option_type).lte('expiration', dte).fetch()

            # shift only the strikes since this is a vertical spread
            chains['strike_key'] = chains['strike'] + (width * option_type.value[1])
            left_keys = ['quote_date', 'expiration', 'root', 'option_type', 'strike_key']
            right_keys = ['quote_date', 'expiration', 'root', 'option_type', 'strike']
            chains = chains.merge(chains, left_on=left_keys, right_on=right_keys, suffixes=('', '_shifted'))

            chains['symbol'] = '.' + chains['symbol'] + '-.' + chains['symbol_shifted']
            chains['order_bid'] = chains['bid'] - chains['ask_shifted']
            chains['order_ask'] = chains['ask'] - chains['bid_shifted']
            chains['exp_label'] = chains['expiration'].dt.strftime('%d %b %y')
            chains['mark'] = round((chains['order_bid'] + chains['order_ask']) / 2, 2)
            chains['volume'] = chains['trade_volume'] + chains['trade_volume_shifted']

            if option_type == OptionType.CALL:
                chains['strikes'] = chains['strike_shifted'].astype(str) + '/' + chains['strike'].astype(str)
            elif option_type == OptionType.PUT:
                chains['strikes'] = chains['strike'].astype(str) + "/" + chains['strike_shifted'].astype(str)

            chains['name'] = OptionStrategy.VERTICAL.value

            new_col = ['symbol', 'name', 'underlying_symbol', 'underlying_price', 'quote_date', 'expiration',
                       'exp_label', 'strikes', 'option_type', 'volume', 'mark', 'order_bid', 'order_ask']

            for greek in ['delta', 'theta', 'gamma', 'vega', 'rho']:
                if greek in chains.columns:
                    chains[greek] = chains[greek] - chains[greek + "_shifted"]
                    new_col.append(greek)

            return OptionSeries(chains[new_col])

    @staticmethod
    def iron_condor(chain, **params):
        """
        The iron condor is an option trading strategy utilizing two vertical spreads
        – a put spread and a call spread with the same expiration and four different strikes.
        A long iron condor is essentially selling both sides of the underlying instrument by
        simultaneously shorting the same number of calls and puts, then covering each position
        with the purchase of further out of the money call(s) and put(s) respectively.
        The converse produces a short iron condor.

        :param chain: dataframe of option chain data
        :param params: width: Width between the middle strikes.
                       c_width: Width of the call spreads
                       p_width: Width of the put spreads
        :return: A new dataframe containing all iron condors created from dataframe
        """

        # check and set default params if none are specified
        args = {'option_type': OptionType.CALL, 'dte': Period.ONE_WEEK, 'width': 1,
                'c_width': 1, 'p_width': 1}
        option_params = OptionStrategies.check_args(params, args)

        dte = option_params['dte']
        width = option_params['width']
        c_width = option_params['c_width']
        p_width = option_params['p_width']

        if width <= 0 or c_width <= 0 or p_width <= 0:
            raise ValueError("Widths cannot be less than or equal 0")

        chains = chain.lte('expiration', dte)
        call_chains = chains.calls().fetch()
        put_chains = chains.puts().fetch()

        # shift only the strikes since this is a vertical spread
        call_chains['strike_key'] = call_chains['strike'] + (c_width * OptionType.CALL.value[1])
        put_chains['strike_key'] = put_chains['strike'] + (p_width * OptionType.PUT.value[1])

        left_keys = ['quote_date', 'expiration', 'root', 'option_type', 'strike_key']
        right_keys = ['quote_date', 'expiration', 'root', 'option_type', 'strike']

        # CALL SIDE ===================================================================================================
        call_side = call_chains.merge(call_chains, left_on=left_keys, right_on=right_keys, suffixes=('', '_shifted'))

        call_side['symbol'] = '.' + call_side['symbol'] + '-.' + call_side['symbol_shifted']
        call_side['mark'] = ((call_side['bid'] - call_side['ask_shifted']) +
                             (call_side['ask'] - call_side['bid_shifted'])) / 2
        call_side['volume'] = call_side['trade_volume'] + call_side['trade_volume_shifted']

        # PUT SIDE ====================================================================================================
        put_side = put_chains.merge(put_chains, left_on=left_keys, right_on=right_keys, suffixes=('', '_shifted'))

        put_side['symbol'] = '.' + put_side['symbol'] + '-.' + put_side['symbol_shifted']
        put_side['mark'] = ((put_side['bid'] - put_side['ask_shifted']) +
                            (put_side['ask'] - put_side['bid_shifted'])) / 2
        put_side['volume'] = put_side['trade_volume'] + put_side['trade_volume_shifted']
        put_side['strike_key'] = put_side['strike'] + width

        # MERGED ======================================================================================================
        call_side_keys = ['quote_date', 'underlying_symbol', 'expiration', 'root', 'strike']
        put_side_keys = ['quote_date', 'underlying_symbol', 'expiration', 'root', 'strike_key']

        chains = call_side.merge(put_side, left_on=call_side_keys, right_on=put_side_keys, suffixes=('_c', '_p'))
        chains['symbol'] = chains['symbol_c'] + '+' + chains['symbol_p']
        chains['mark'] = chains['mark_c'] + chains['mark_p']
        chains['exp_label'] = chains['expiration'].dt.strftime('%d %b %y')
        chains['volume'] = chains['trade_volume_c'] + chains['trade_volume_p']
        chains['name'] = OptionStrategy.IRON_CONDOR.value

        new_col = ['symbol', 'name', 'underlying_symbol', 'quote_date', 'expiration', 'exp_label', 'volume', 'mark']

        for greek in ['delta', 'theta', 'gamma', 'vega', 'rho']:
            if greek in chains.columns:
                chains[greek] = chains[greek] - chains[greek + "c_shifted"]
                new_col.append(greek)

        return OptionSeries(chains[new_col])

    @staticmethod
    def covered_stock(chain, **params):
        """
        A covered call is an options strategy whereby an investor holds a long position
        n an asset and writes (sells) call options on that same asset in an attempt to
        generate increased income from the asset.

        Writing covered puts is a bearish options trading strategy involving the
        writing of put options while shorting the obligated shares of the underlying stock.

        :param chain: dataframe of option chain data
        :param params: params used to build the covered stock strategy
        :return: A new dataframe containing all covered stock created from dataframe
        """

        if 'option_type' not in params:
            raise ValueError("Must provide option_type for covered stock")

        # set the attributes for this option strategy
        OptionStrategies.covered_stock.option_config = {'stock': 100, 'option': 1}

        out_col = OptionStrategies.base_out_col

        chains = OptionQuery(chain).option_type(params['option_type'])
        chains = chains.lte('expiration', params['DTE']).fetch() if 'DTE' in params else chains.fetch()

        side = -1 * params['option_type'].value[1]

        chains['spread_mark'] = (side * (chains['bid'] + chains['ask']) / 2) + chains['underlying_price']

        prefix = "-." if params['option_type'] == OptionType.CALL else "."
        chains['spread_symbol'] = prefix + chains['symbol'] + "+100*" + chains['underlying_symbol']

        return OptionSeries(chains[out_col + ['strike']])

    @staticmethod
    def diagonal(chain, **params):
        pass

    @staticmethod
    def double_diagonal(chain, **params):
        pass

    @staticmethod
    def calendar(chain, **params):
        """
        A calendar spread is a strategy involving buying longer term options and selling
        equal number of shorter term options of the same underlying stock or index with the
        same strike price. Calendar spreads can be done with calls or with puts,
        which are virtually equivalent if using same strikes and expirations.

        :param chain: Filtered Dataframe to vertical spreads with.
        :param option_type: The option type for this spread
        :param depth: The period to represent the difference between the expiration dates of the two options
        :return: A new dataframe containing all covered stock created from dataframe
        """
        if 'option_type' not in params:
            raise ValueError("Must provide option_type for calendar spread")
        elif 'depth' not in params:
            raise ValueError("Must provide period depth for calender spread")

        # set the attributes for this option strategy
        OptionStrategies.calendar.option_config = {'option': 2}

        out_col = OptionStrategies.base_out_col
        shift = Period.ONE_WEEK if 'depth' not in params else params['depth']

        chains = OptionQuery(chain).option_type(params['option_type'])
        chains = chains.lte('expiration', params['DTE']).fetch() if 'DTE' in params else chains.fetch()
        # create column with expiration shifted by depth
        chains['expiration_key'] = chains['expiration'] + timedelta(days=shift.value)

        left_keys = ['quote_date', 'expiration_key', 'option_type', 'strike']
        right_keys = ['quote_date', 'expiration', 'option_type', 'strike']

        chains = chains.merge(chains, left_on=left_keys, right_on=right_keys, suffixes=('', '_shifted'))

        if chains.empty:
            raise ValueError("Cannot construct calendar spreads. Check expirations exists for specified depth.")

        # calculate the spread's bid and ask prices
        for c, f in OptionStrategies.shift_col:
            # handle bid ask special case
            if c == 'bid':
                chains['spread_' + c] = f(chains[c], chains['ask_shifted'])
            elif c == 'ask':
                chains['spread_' + c] = f(chains[c], chains['bid_shifted'])
            else:
                if f is not None:
                    chains['spread_' + c] = f(chains[c], chains[c + '_shifted'])

        chains['spread_mark'] = (chains['spread_bid'] + chains['spread_ask']) / 2
        chains['spread_symbol'] = "." + chains['symbol_shifted'] + "-." + chains['symbol']

        # assign the strategy name to this dataframe's name attribute
        chains.name = OptionStrategies.single.__name__

        return OptionSeries(chains[out_col + ['strike', 'expiration_shifted']])

    @staticmethod
    def straddle(chain, **params):
        pass

    @staticmethod
    def strangle(chain, **params):
        pass

    @staticmethod
    def combo(chain, **params):
        pass

    @staticmethod
    def back_ratio(chain, **params):
        pass

    @staticmethod
    def butterfly(chain, **params):
        pass

    @staticmethod
    def condor(chain, **params):
        pass
