from .enums import OrderAction
from .option_spreads import *


def long_call(data):
    return OrderAction.BTO, single(data, OptionType.CALL)


def short_call(data):
    return OrderAction.STO, single(data, OptionType.CALL)


def long_put(data):
    return OrderAction.BTO, single(data, OptionType.PUT)


def short_put(data):
    return OrderAction.STO, single(data, OptionType.PUT)