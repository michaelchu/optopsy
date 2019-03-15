from datetime import datetime
import os
import pytest
import pandas as pd
import optopsy as op

from optopsy.helpers import inspect

from optopsy.calculations import assign_trade_num


def filepath():
    curr_file = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(curr_file, "../test_data/data_full.csv")


data = pd.read_csv(
    filepath(), parse_dates=["expiration", "quote_date"], infer_datetime_format=True
)


def test_long_call_spread():
    base = (
        data.start_date(datetime(2018, 1, 1))
        .end_date(datetime(2018, 2, 28))
        .entry_dte(31)
        .calls()
    )

    leg_1 = base.delta(0.50)
    leg_2 = base.delta(0.30)

    results = (
        op.long_call_spread(leg_1, leg_2)
        .pipe(op.backtest, data, mode="midpoint")
        .exit_dte(7)
    )
    assert results.total_profit() == -802.5


def test_short_call_spread():
    base = (
        data.start_date(datetime(2018, 1, 1))
        .end_date(datetime(2018, 2, 28))
        .entry_dte(31)
        .calls()
    )

    leg_1 = base.delta(0.50)
    leg_2 = base.delta(0.30)

    results = (
        op.short_call_spread(leg_1, leg_2)
        .pipe(op.backtest, data, mode="midpoint")
        .exit_dte(7)
    )

    assert results.total_profit() == 802.5


def test_long_put_spread():
    base = (
        data.start_date(datetime(2018, 1, 1))
        .end_date(datetime(2018, 2, 28))
        .entry_dte(31)
        .puts()
    )

    leg_1 = base.delta(0.30)
    leg_2 = base.delta(0.50)

    results = (
        op.long_put_spread(leg_1, leg_2)
        .pipe(op.backtest, data, mode="midpoint")
        .exit_dte(7)
    )

    assert results.total_profit() == 2275.0


def test_short_put_spread():
    base = (
        data.start_date(datetime(2018, 1, 1))
        .end_date(datetime(2018, 2, 28))
        .entry_dte(31)
        .puts()
    )

    leg_1 = base.delta(0.30)
    leg_2 = base.delta(0.50)

    results = (
        op.short_put_spread(leg_1, leg_2)
        .pipe(op.backtest, data, mode="midpoint")
        .exit_dte(7)
    )

    assert results.total_profit() == -2275.0
