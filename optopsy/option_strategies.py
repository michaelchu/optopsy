from .enums import OrderAction, OptionType
from .option_spreads import create_spread


def long_call(data, filters):
    if _filter_check(filters):
        return OrderAction.BTO, create_spread(
            data, [(OptionType.CALL, 1)], filters)


def short_call(data, filters):
    if _filter_check(filters):
        return OrderAction.STO, create_spread(
            data, [(OptionType.CALL, 1)], filters)


def long_put(data, filters):
    if _filter_check(filters):
        return OrderAction.BTO, create_spread(
            data, [(OptionType.PUT, 1)], filters)


def short_put(data, filters):
    if _filter_check(filters):
        return OrderAction.STO, create_spread(
            data, [(OptionType.PUT, 1)], filters)


def long_call_spread(data, filters):
    if _filter_check(filters):
        legs = [(OptionType.CALL, -1), (OptionType.CALL, 1)]
        return OrderAction.BTO, create_spread(data, legs, filters)
    else:
        raise ValueError(
            "Long delta must be less than short delta for long call spreads!")


def short_call_spread(data, filters):
    if _filter_check(filters):
        legs = [(OptionType.CALL, 1), (OptionType.CALL, -1)]
        return OrderAction.STO, create_spread(data, legs, filters)
    else:
        raise ValueError(
            "Short delta must be less than long delta for short call spreads!")


def long_put_spread(data, filters):
    if _filter_check(filters):
        legs = [(OptionType.PUT, 1), (OptionType.PUT, -1)]
        return OrderAction.BTO, create_spread(data, legs, filters)
    else:
        raise ValueError(
            "Short delta must be less than long delta for long put spreads!")


def short_put_spread(data, filters):
    if _filter_check(filters):
        legs = [(OptionType.PUT, -1), (OptionType.PUT, 1)]
        return OrderAction.STO, create_spread(data, legs, filters)
    else:
        raise ValueError(
            "Long delta must be less than short delta for short put spreads!")


def _filter_check(filters):
    return True
