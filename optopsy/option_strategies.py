from .enums import OrderAction, OptionType
from .option_spreads import create_legs


def long_call(data, long_delta, dte):
    return OrderAction.BTO, create_legs(
        data, [(OptionType.CALL, long_delta, dte, 1)])


def short_call(data, short_delta, dte):
    return OrderAction.STO, create_legs(
        data, [(OptionType.CALL, short_delta, dte, 1)])


def long_put(data, long_delta, dte):
    return OrderAction.BTO, create_legs(
        data, [(OptionType.PUT, long_delta, dte, 1)])


def short_put(data, short_delta, dte):
    return OrderAction.STO, create_legs(
        data, [(OptionType.PUT, short_delta, dte, 1)])


def long_call_spread(data, long_delta, short_delta, dte):
    if long_delta < short_delta:
        legs = [(OptionType.CALL, long_delta, dte, -1),
                (OptionType.CALL, short_delta, dte, 1)]
        return OrderAction.BTO, create_legs(data, legs)
    else:
        raise ValueError(
            "Long delta must be less than short delta for long call spreads!")


def short_call_spread(data, short_delta, long_delta, dte):
    if short_delta < long_delta:
        legs = [(OptionType.CALL, short_delta, dte, 1),
                (OptionType.CALL, long_delta, dte, -1)]
        return OrderAction.STO, create_legs(data, legs)
    else:
        raise ValueError(
            "Short delta must be less than long delta for short call spreads!")


def long_put_spread(data, short_delta, long_delta, dte):
    if short_delta < long_delta:
        legs = [(OptionType.PUT, short_delta, dte, 1),
                (OptionType.PUT, long_delta, dte, -1)]
        return OrderAction.BTO, create_legs(data, legs)
    else:
        raise ValueError(
            "Short delta must be less than long delta for long put spreads!")


def short_put_spread(data, long_delta, short_delta, dte):
    if long_delta < short_delta:
        legs = [(OptionType.PUT, long_delta, dte, -1),
                (OptionType.PUT, short_delta, dte, 1)]
        return OrderAction.STO, create_legs(data, legs)
    else:
        raise ValueError(
            "Long delta must be less than short delta for short put spreads!")
