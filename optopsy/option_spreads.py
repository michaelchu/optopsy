from functools import reduce
from .option_queries import fields, nearest, lte, opt_type
import pandas as pd


leg_cols = [f[0] for f in fields if f[3] == 'leg']
common_cols = [f[0] for f in fields if f[3] == 'common']


def _swap_columns(data, left, right):
    cols = data.columns.tolist()

    bid_index = cols.index(left)
    ask_index = cols.index(right)
    cols[bid_index], cols[ask_index] = right, left

    data = data[cols]
    data.rename(columns={right: left, left: right}, inplace=True)
    return data


def _apply_ratio(data, ratio):
    data = _swap_columns(data, 'bid', 'ask') if ratio < 0 else data
    return pd.concat([data.loc[:, common_cols],
                      data.loc[:, leg_cols] * ratio], axis=1)


def _collapse_values(spread, legs):
    data['var_total'] = data.filter(regex='var[0-9]+').sum(axis=1)
    print(spread)
    return spread


# Merge method #1: join -> slice
def _join_legs(legs):
    on = ['quote_date', 'option_type', 'expiration']
    suffixes = [f"_{i+1}" for i in range(len(legs))]
    return (
        reduce(lambda l, r: pd.merge(l, r, on=on, suffixes=suffixes), legs)
        .pipe(_collapse_values, legs)
    )


# Merge method #2: split -> apply -> combine
def _concat_legs(legs):
    sort_by = ['quote_date', 'option_type', 'expiration', 'strike']
    return (
        pd.concat(legs)
        .sort_values(sort_by)
        .groupby(sort_by[:-1]).sum()
    )


def _create_legs(data, legs):
    def _create_leg(leg):
        return (
            data
            .pipe(opt_type, option_type=leg[0])
            .pipe(nearest, 'delta', leg[1])
            .pipe(lte, 'dte', leg[2])
            .pipe(_apply_ratio, ratio=leg[3])
        ).reset_index(drop=True)
    return [_create_leg(legs[l]) for l in range(0, len(legs))]


def singles(data, leg):
    return _create_legs(data, leg)[0]


def spreads(data, legs, method='concat'):
    spread = _create_legs(data, legs)
    if len(spread) < 2:
        raise ValueError("Invalid number of legs defined for spreads!")
    else:
        return _concat_legs(spread) if method == 'concat' else _join_legs(spread)
