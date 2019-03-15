from datetime import datetime
import os
import pytest
import pandas as pd
import optopsy as op
from optopsy.helpers import inspect


def filepath():
    curr_file = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(curr_file, "../test_data/data_full.csv")


data = pd.read_csv(
    filepath(), parse_dates=["expiration", "quote_date"], infer_datetime_format=True
)


def test_long_call():
    results = (
        data.start_date(datetime(2018, 1, 1))
        .end_date(datetime(2018, 2, 28))
        .entry_dte(31)
        .delta(0.30)
        .calls()
        .pipe(op.long_call)
        .pipe(op.backtest, data)
        .exit_dte(7)
        .total_profit()
    )
    assert results == 9330.0


def test_long_call_midpoint():
    results = (
        data.start_date(datetime(2018, 1, 1))
        .end_date(datetime(2018, 2, 28))
        .entry_dte(31)
        .delta(0.30)
        .calls()
        .pipe(op.long_call)
        .pipe(op.backtest, data, mode="midpoint")
        .exit_dte(7)
        .total_profit()
    )
    assert results == 9630.0


def test_long_call_expire():
    results = (
        data.start_date(datetime(2018, 1, 1))
        .end_date(datetime(2018, 2, 28))
        .entry_dte(31)
        .delta(0.30)
        .calls()
        .pipe(op.long_call)
        .pipe(op.backtest, data)
        .exit_dte("expire")
        .total_profit()
    )
    assert results == 7710.0


def test_short_call():
    results = (
        data.start_date(datetime(2018, 1, 1))
        .end_date(datetime(2018, 2, 28))
        .entry_dte(31)
        .delta(0.30)
        .calls()
        .pipe(op.short_call)
        .pipe(op.backtest, data)
        .exit_dte(7)
        .total_profit()
    )

    assert results == -9930.0


def test_long_put():
    results = (
        data.start_date(datetime(2018, 1, 1))
        .end_date(datetime(2018, 2, 28))
        .entry_dte(31)
        .delta(0.30)
        .puts()
        .pipe(op.long_put)
        .pipe(op.backtest, data)
        .exit_dte(7)
        .total_profit()
    )
    assert results == 4470.0


def test_short_put():
    results = (
        data.start_date(datetime(2018, 1, 1))
        .end_date(datetime(2018, 2, 28))
        .entry_dte(31)
        .delta(0.30)
        .puts()
        .pipe(op.short_put)
        .pipe(op.backtest, data)
        .exit_dte(7)
        .total_profit()
    )

    assert results == -5060.0
