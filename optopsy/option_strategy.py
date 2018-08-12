from optopsy.option_legs import *
from .enums import OptionType, OrderAction
from functools import reduce
import optopsy.filter as f


leg_filters = {
    'leg_1_abs_delta': (0.1, 0.2, 0.3),
    'leg_2_abs_delta': (0.3, 0.4, 0.5),
    'leg_3_abs_delta': (0.5, 0.6, 0.7),
    'leg_4_abs_delta': (0.7, 0.8, 0.9),
    'leg_1_dte': (
        Period.FOUR_WEEKS.value - 3,
        Period.FOUR_WEEKS.value,
        Period.FOUR_WEEKS.value + 3
    ),
    'leg_2_dte': (
        Period.FOUR_WEEKS.value - 3,
        Period.FOUR_WEEKS.value,
        Period.FOUR_WEEKS.value + 3
    ),
    'leg_3_dte': (
        Period.FOUR_WEEKS.value - 3,
        Period.FOUR_WEEKS.value,
        Period.FOUR_WEEKS.value + 3
    ),
    'leg_4_dte': (
        Period.FOUR_WEEKS.value - 3,
        Period.FOUR_WEEKS.value,
        Period.FOUR_WEEKS.value + 3
    )
}


spread_filters = {
    'spread_price': None,
    'spread_dte': (
        Period.FOUR_WEEKS.value - 3,
        Period.FOUR_WEEKS.value,
        Period.FOUR_WEEKS.value + 3
    ),
    'spread_abs_delta': (0.4, 0.5, 0.6),
    'leg_1_leg_2_dist': None,
    'leg_2_leg_3_dist': None,
    'leg_3_leg_4_dist': None,
    'quantity': 1,
    'day_of_week': 1
}


def _create_spread(legs, valid_filters, **kwargs):
    # apply filters to each leg
    l_filters = _process_filters(leg_filters, valid_filters, **kwargs)
    filtered_legs = [_apply_filters(l, l_filters) for l in legs]
    
	  # join the legs together to form a spread, if possible
    spread = _build_spread(filtered_legs)
    
    # apply spread level filters and return thr result
    s_filters = _process_filters(spread_filters, valid_filters, **kwargs)
    return _apply_filters(spread, s_filters)


def _process_filters(base, filters, **kwargs):
    return {k: kwargs[k] for k in kwargs if k in filters}


def _apply_filters(leg, filters):
    return reduce(lambda k, v: leg.pipe(_do_apply_filters, k=k, v=filters[k]), [*filters])


def _build_spread(legs):
    # join legs based on quote date
    return reduce(lambda l, r: pd.merge(l, r, on=['quote_date'], how='inner'), legs)
	
	
# this returns a dataframe
def _do_apply_filters(l, k, v):
    return l if v is None else getattr(f, k)(l, v)


def long_call(data, **kwargs):
    valid_filters = ['spread_abs_delta', 'spread_dte', 'spread_price']
    legs = create_legs(data, legs=[(OptionType.CALL, 1)])
    return OrderAction.BTO, _create_spread(legs, valid_filters, **kwargs)


def short_call(data, **kwargs):
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
