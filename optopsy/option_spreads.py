import pandas as pd
import optopsy.filters as filters
from .option_query import *
from functools import reduce


leg_cols = [
    'strike',
    'bid',
    'ask',
    'delta',
    'gamma',
    'theta',
    'vega',
    'dte'
]

common_cols = [
    'symbol',
    'expiration',
    'quote_date',
    'underlying_price'
]


def _format_leg(data, suffix):
    return (
        data
        .assign(dte=lambda r: (r['expiration'] - r['quote_date']).dt.days)
        .rename(columns={v: suffix + v for v in common_cols+leg_cols})
    )
    

def _apply_ratio(data, ratio):
    return pd.concat([data.loc[:, common_cols + leg_cols[:1]], data.loc[:, leg_cols[1:]] * ratio], axis=1)
    
    
def _apply_filters(leg, params):
    return reduce(lambda l, f: getattr(filters, f)(l, filters[f]), params, leg)


def _create_legs(data, legs, params):
    def _create_leg(n, leg):
        return (data
                .pipe(opt_type, option_type=leg[0])
                .pipe(_apply_filters, params=params)
                .pipe(_apply_ratio, ratio=leg[1])
                .pipe(_format_leg, suffix=f"leg_{n+1}_")
                ).reset_index(drop=True)

    return [_create_leg(l, legs[l]) for l in range(0, len(legs))]


def single(data, option_type, params):
    return (
        data
        .pipe(_create_legs, [(option_type, 1)])
        )
    

def vertical(data, option_type, params):

    # if leg1_leg2_dist param is missing, join by deltas
    by = ['quote_date', 'expiration']
    
    
    # array of formatted legs to join with
    legs = _create_legs(data, [(option_type, 1), (option_type, -1)])
    
    return (
        pd.merge(legs[0], legs[1], on=common_cols)    
    )
    
    