from functools import reduce

import pandas as pd

import optopsy.filters as fil
from .option_queries import opt_type
from .statistics import *

pd.set_option('display.expand_frame_repr', False)

sort_by = [
    'underlying_symbol',
    'quote_date',
    'option_type',
    'expiration',
    'strike'
]

on = [
    'underlying_symbol',
    'option_type',
    'expiration',
    'strike'
]

default_entry_filters = {
    "std_expr": False,
    "contract_size": 10,
    "entry_dte": (27, 30, 31),
    "exit_dte": None
}

output_cols = {
    'quote_date_entry': 'entry_date',
    'quote_date_exit': 'exit_date',
    'delta_entry': 'entry_delta',
    'underlying_price_entry': 'entry_stk_price',
    'underlying_price_exit': 'exit_stk_price',
    'dte_entry': 'DTE'
}

output_format = [
    'entry_date',
    'exit_date',
    'expiration',
    'DTE',
    'ratio',
    'contracts',
    'option_type',
    'strike',
    'entry_delta',
    'entry_stk_price',
    'exit_stk_price',
    'entry_opt_price',
    'exit_opt_price',
    'entry_price',
    'exit_price',
    'profit'
]


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
    return _filter_data(spread, spread_filters).sort_values(sort_by)


# this is the main function that runs the backtest engine
def run(data, trades, filters, init_balance=10000, mode='midpoint'):
    trades = trades if isinstance(trades, list) else [trades]

    # merge trades from multiple underlying symbols if applicable
    all_trades = pd.concat(trades).sort_values(sort_by)

    # for each option to be traded, determine the historical price action
    filters = {**default_entry_filters, **filters}
    exit_filters = {f: filters[f] for f in filters if f.startswith('exit_')}
    res = (
        pd
        .merge(all_trades, data, on=on, suffixes=('_entry', '_exit'))
        .pipe(_filter_data, exit_filters)
        .pipe(calc_entry_px, mode)
        .pipe(calc_exit_px, mode)
        .pipe(calc_pnl)
        # .pipe(calc_running_balance, init_balance)
        .rename(columns=output_cols)
        .sort_values(['entry_date', 'expiration', 'underlying_symbol', 'strike'])
    )

    return calc_total_profit(res), res[output_format]
