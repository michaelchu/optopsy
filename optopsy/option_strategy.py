from .option_query import *
from .enums import OptionType, OrderAction
from .option_spread import *
import pandas as pd


default_params = {
    'leg_1_delta': (0.1, 0.2, 0.3),
    'leg_2_delta': (0.3, 0.4, 0.5),
    'leg_3_delta': (0.5, 0.6, 0.7),
    'leg_4_delta': (0.7, 0.8, 0.9),
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


def _merge_params(params):
    pass
    

def long_call(data, **kwargs):
    return OrderAction.BTO, single(data, OptionType.CALL, _merge_params(kwargs))


def short_call(data, **kwargs):
    return OrderAction.STO, single(data, OptionType.CALL, _merge_params(kwargs))


def long_put(data, **kwargs):
    return OrderAction.BTO, single(data, OptionType.PUT, _merge_params(kwargs))


def short_put(data, **kwargs):
    return OrderAction.STO, single(data, OptionType.PUT, _merge_params(kwargs))


# debit
def long_call_spread(data, **kwargs):
    return OrderAction.BTO, vertical(data, OptionType.CALL, _merge_params(kwargs))


# credit
def short_call_spread(data, **kwargs):
     return OrderAction.STO, vertical(data, OptionType.CALL, _merge_params(kwargs))    


# credit
def long_put_spread(data, **kwargs):
     return OrderAction.BTO, vertical(data, OptionType.PUT, _merge_params(kwargs))


# debit
def short_put_spread(data, **kwargs):
     return OrderAction.STO, vertical(data, OptionType.PUT, _merge_params(kwargs))


def long_iron_condor(data, **kwargs):
     return OrderAction.BTO, iron_condor(data, _merge_params(kwargs))


def short_iron_condor(data, **kwargs):
     return OrderAction.STO, iron_condor(data, _merge_params(kwargs))


def long_iron_butterfly(data, **kwargs):
     return OrderAction.BTO, iron_butterfly(data, _merge_params(kwargs))


def short_iron_butterfly(data, **kwargs):
     return OrderAction.STO, iron_butterfly(data, _merge_params(kwargs))
