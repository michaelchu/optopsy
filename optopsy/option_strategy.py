from optopsy.option_legs import *
from .enums import OptionType, OrderAction
from functools import reduce


def _create_spread(data, legs, **kwargs):
    """

    Args:
        data: A dataframe object containing all the option chain data to be used
        legs: A list of tuples with two values, representing the option type and ratio relative to the spread
        leg_abs_deltas: A list of n tuples, containing the min, mid and max delta values to place each leg,
                        where n is the length of legs parameter
        leg_dte: A list of n tuples, containing the min, mid and, max dte values for each leg,
                 where n is the length of the legs parameter

    Returns:

    """

    # join legs based on quote date
    return reduce(lambda l, r: pd.merge(l, r, on=['quote_date'], how='inner'), legs)


def long_call(data, leg_abs_deltas=None, leg_dte=None):
    legs = [(OptionType.CALL, 1)]

    if leg_abs_deltas is None:
        leg_abs_deltas = [(
            Period.FOUR_WEEKS.value - 3,
            Period.FOUR_WEEKS.value,
            Period.FOUR_WEEKS.value + 3
        )]

    if leg_dte is None:
        leg_dte = [(0.5, 0.6, 0.7)]

    if len(leg_abs_deltas) == len(leg_dte) == 1:
        spread = _create_spread(data, legs, leg_abs_deltas=leg_abs_deltas, leg_dte=leg_dte)
        return OrderAction.BTO, spread
    else:
        raise ValueError


def short_call(data, leg_abs_deltas=None, leg_dte=None):
    valid_filters = ['spread_abs_delta', 'spread_dte', 'spread_price']
    legs = create_legs(data, legs=[(OptionType.CALL, 1)])
    return OrderAction.STO, _create_spread(legs, valid_filters, **kwargs)


def long_put(data, **kwargs):
    valid_filters = ['spread_abs_delta', 'spread_dte', 'spread_price']
    legs = create_legs(data, legs=[(OptionType.PUT, 1)])
    return OrderAction.BTO, _create_spread(legs, valid_filters, **kwargs)


def short_put(data, **kwargs):
    valid_filters = ['spread_abs_delta', 'spread_dte', 'spread_price']
    legs = create_legs(data, legs=[(OptionType.PUT, 1)])
    return OrderAction.STO, _create_spread(legs, valid_filters, **kwargs)


# debit
def long_call_spread(data, **kwargs):
    valid_filters = ['leg_1_abs_delta', 'leg_2_abs_delta', 'spread_dte', 'spread_price']
    legs = create_legs(data, legs=[(OptionType.CALL, 1), (OptionType.CALL, -1)])
    return OrderAction.BTO, _create_spread(legs, valid_filters, **kwargs)


# credit
def short_call_spread(data, **kwargs):
    valid_filters = ['leg_1_abs_delta', 'leg_2_abs_delta', 'spread_dte', 'spread_price']
    legs = create_legs(data, legs=[(OptionType.CALL, -1), (OptionType.CALL, 1)])
    return OrderAction.STO, _create_spread(legs, valid_filters, **kwargs)


# credit
def long_put_spread(data, **kwargs):
    valid_filters = ['leg_1_abs_delta', 'leg_2_abs_delta', 'spread_dte', 'spread_price']
    legs = create_legs(data, legs=[(OptionType.PUT, 1), (OptionType.PUT, -1)])
    return OrderAction.BTO, _create_spread(legs, valid_filters, **kwargs)


# debit
def short_put_spread(data, **kwargs):
    valid_filters = ['leg_1_abs_delta', 'leg_2_abs_delta', 'spread_dte', 'spread_price']
    legs = create_legs(data, legs=[(OptionType.PUT, -1), (OptionType.PUT, 1)])
    return OrderAction.STO, _create_spread(legs, valid_filters, **kwargs)


def long_iron_condor(data, **kwargs):
    valid_filters = ['leg_1_abs_delta', 'leg_2_abs_delta', 'leg_3_abs_delta',
                     'leg_4_abs_delta', 'spread_dte', 'leg_1_leg_2_dist',
                     'leg_2_leg_3_dist', 'leg_3_leg_4_dist', 'spread_price']
    legs = create_legs(data, legs=[(OptionType.PUT, 1), (OptionType.PUT, -1),
                                   (OptionType.CALL, -1), (OptionType.CALL, 1)])
    return OrderAction.BTO, _create_spread(legs, valid_filters, **kwargs)


def short_iron_condor(data, **kwargs):
    valid_filters = ['leg_1_abs_delta', 'leg_2_abs_delta', 'leg_3_abs_delta',
                     'leg_4_abs_delta', 'spread_dte', 'spread_price', 'leg_1_leg_2_dist',
                     'leg_2_leg_3_dist', 'leg_3_leg_4_dist']
    legs = create_legs(data, legs=[(OptionType.PUT, 1), (OptionType.PUT, -1),
                                   (OptionType.CALL, -1), (OptionType.CALL, 1)])
    return OrderAction.STO, _create_spread(legs, valid_filters, **kwargs)


def long_iron_butterfly(data, **kwargs):
    valid_filters = ['leg_1_abs_delta', 'leg_2_abs_delta', 'leg_3_abs_delta',
                     'leg_4_abs_delta', 'spread_dte', 'spread_price', 'leg_1_leg_2_dist',
                     'leg_3_leg_4_dist']
    legs = create_legs(data, legs=[(OptionType.PUT, 1), (OptionType.PUT, -1),
                                   (OptionType.CALL, -1), (OptionType.CALL, 1)])
    return OrderAction.BTO, _create_spread(legs, valid_filters, **kwargs)


def short_iron_butterfly(data, **kwargs):
    valid_filters = ['leg_1_abs_delta', 'leg_2_abs_delta', 'leg_3_abs_delta',
                     'leg_4_abs_delta', 'spread_dte', 'spread_price', 'leg_1_leg_2_dist',
                     'leg_3_leg_4_dist']
    legs = create_legs(data, legs=[(OptionType.PUT, 1), (OptionType.PUT, -1),
                                   (OptionType.CALL, -1), (OptionType.CALL, 1)])
    return OrderAction.STO, _create_spread(legs, valid_filters, **kwargs)
