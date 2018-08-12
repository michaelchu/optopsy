import pandas as pd

from .option_query import *

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
        .assign(
            dte=lambda r: (r['expiration'] - r['quote_date']).dt.days)
        .rename(columns={v: suffix + v for v in common_cols+leg_cols})
    )


def _apply_ratio(data, ratio):
    return pd.concat([data.loc[:, common_cols + leg_cols[:1]], data.loc[:, leg_cols[1:]] * ratio],
                     axis=1)


def create_legs(data, legs):
    def _create_leg(n, leg):
        return (data
                .pipe(opt_type, option_type=leg[0])
                .pipe(_apply_ratio, ratio=leg[1])
                .pipe(_format_leg, suffix=f"leg_{n+1}_")
                ).reset_index(drop=True)

    return [_create_leg(l, legs[l]) for l in range(0, len(legs))]
