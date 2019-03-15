import os
from datetime import datetime

import pandas as pd

import optopsy as op


def filepath():
    curr_file = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(curr_file, "../test_data/data_full.csv")


data = pd.read_csv(
    filepath(), parse_dates=["expiration", "quote_date"], infer_datetime_format=True
)


def test_long_iron_condor():
    base = (
        data.start_date(datetime(2018, 1, 1))
        .end_date(datetime(2018, 2, 28))
        .entry_dte(31)
    )

    leg1 = base.delta(0.10, 0.05, 0.15).puts()
    leg2 = base.delta(0.30, 0.25, 0.45).puts()
    leg3 = base.delta(0.30, 0.25, 0.45).calls()
    leg4 = base.delta(0.10, 0.05, 0.15).calls()

    results = (
        op.long_iron_condor(leg1, leg2, leg3, leg4)
        .pipe(op.backtest, data)
        .exit_dte(7)
        .total_profit()
    )

    assert results == -6135.0


def test_short_iron_condor_integration():
    base = (
        data.start_date(datetime(2018, 1, 1))
        .end_date(datetime(2018, 2, 28))
        .entry_dte(31)
    )

    leg1 = base.delta(0.10, 0.05, 0.15).puts()
    leg2 = base.delta(0.30, 0.25, 0.45).puts()
    leg3 = base.delta(0.30, 0.25, 0.45).calls()
    leg4 = base.delta(0.10, 0.05, 0.15).calls()

    results = (
        op.short_iron_condor(leg1, leg2, leg3, leg4)
        .pipe(op.backtest, data)
        .exit_dte(7)
        .total_profit()
    )

    assert results == 4510.0
