from functools import reduce

import pandas as pd

import optopsy.filters as fil
from .enums import Period
from .option_queries import opt_type

pd.set_option('display.expand_frame_repr', False)

sort_by = [
    'underlying_symbol',
    'quote_date',
    'option_type',
    'expiration',
    'strike']
on = ['underlying_symbol', 'option_type', 'expiration', 'strike']

default_entry_filters = {
    "std_expr": False,
    "contract_size": 10,
    "entry_dte": Period.FOUR_WEEKS.value,
    "exit_dte": None
}


def _create_legs(data, leg):
    return (
        data
        .pipe(opt_type, option_type=leg[0])
        .assign(ratio=leg[1])
    )


def _apply_filters(legs, filters):
    if not filters:
        return legs
    else:
        return [reduce(lambda l, f: getattr(fil, f)(l, filters[f], idx), filters, leg)
                for idx, leg in enumerate(legs)]


def _filter_data(data, filters):
    data = data if isinstance(data, list) else [data]
    return pd.concat(_apply_filters(data, filters))


def create_spread(data, leg_structs, filters):
    legs = [_create_legs(data, leg) for leg in leg_structs]

    # merge and apply leg filters to create spread
    filters = {**default_entry_filters, **filters}
    entry_filters = {f: filters[f]
                     for f in filters if (not f.startswith('entry_spread') and
                                          not f.startswith('exit_'))}
    spread = _filter_data(legs, entry_filters)

    # apply spread level filters to spread
    spread_filters = {f: filters[f]
                      for f in filters if f.startswith('entry_spread')}
    return _filter_data(spread, spread_filters)


# this is the main function that runs the backtest engine
def run(data, trades, filters, mode='midpoint'):
    trades = trades if isinstance(trades, list) else [trades]

    # merge trades from multiple underlying symbols if applicable
    all_trades = pd.concat(trades).sort_values(sort_by)

    # for each option to be traded, determine the historical price action
    exit_filters = {f: filters[f] for f in filters if f.startswith('exit_')}
    res = pd.merge(all_trades, data, on=on).pipe(_filter_data, exit_filters)

    # calculate the p/l for the trades
    if mode == 'midpoint':
        res['cost'] = res[['bid_x', 'ask_x']].mean() * res['ratio'] * res['contracts']
    elif mode == 'market':
        pass

    return results
