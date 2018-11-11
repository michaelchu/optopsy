from .enums import OrderAction, OptionType
from .backtest import create_spread


def _add_date_range(s, e, f):
    f['start_date'] = s
    f['end_date'] = e
    return f


def long_call(data, start_date, end_date, filters):
    filters = _add_date_range(start_date, end_date, filters)
    if _filter_check(filters):
        return OrderAction.BTO, create_spread(
            data, [(OptionType.CALL, 1)], filters)


def short_call(data, start_date, end_date, filters):
    filters = _add_date_range(start_date, end_date, filters)
    if _filter_check(filters):
        return OrderAction.STO, create_spread(
            data, [(OptionType.CALL, 1)], filters)


def long_put(data, start_date, end_date, filters):
    filters = _add_date_range(start_date, end_date, filters)
    if _filter_check(filters):
        return OrderAction.BTO, create_spread(
            data, [(OptionType.PUT, 1)], filters)


def short_put(data, start_date, end_date, filters):
    filters = _add_date_range(start_date, end_date, filters)
    if _filter_check(filters):
        return OrderAction.STO, create_spread(
            data, [(OptionType.PUT, 1)], filters)


def long_call_spread(data, start_date, end_date, filters):
    filters = _add_date_range(start_date, end_date, filters)
    if _filter_check(filters):
        legs = [(OptionType.CALL, -1), (OptionType.CALL, 1)]
        return OrderAction.BTO, create_spread(data, legs, filters)
    else:
        raise ValueError(
            "Long delta must be less than short delta for long call spreads!")


def short_call_spread(data, start_date, end_date, filters):
    filters = _add_date_range(start_date, end_date, filters)
    if _filter_check(filters):
        legs = [(OptionType.CALL, 1), (OptionType.CALL, -1)]
        return OrderAction.STO, create_spread(data, legs, filters)
    else:
        raise ValueError(
            "Short delta must be less than long delta for short call spreads!")


def long_put_spread(data, start_date, end_date, filters):
    filters = _add_date_range(start_date, end_date, filters)
    if _filter_check(filters):
        legs = [(OptionType.PUT, 1), (OptionType.PUT, -1)]
        return OrderAction.BTO, create_spread(data, legs, filters)
    else:
        raise ValueError(
            "Short delta must be less than long delta for long put spreads!")


def short_put_spread(data, start_date, end_date, filters):
    filters = _add_date_range(start_date, end_date, filters)
    if _filter_check(filters):
        legs = [(OptionType.PUT, -1), (OptionType.PUT, 1)]
        return OrderAction.STO, create_spread(data, legs, filters)
    else:
        raise ValueError(
            "Long delta must be less than short delta for short put spreads!")


def _filter_check(filters):
    return True
