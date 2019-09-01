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
    filtered_opt_chains = (
        data.start_date(datetime(2018, 1, 1))
        .end_date(datetime(2018, 2, 28))
        .entry_dte(31)
        .delta(0.30)
        .calls()
    )

    results = (
        op.long_call(filtered_opt_chains)
        .pipe(op.backtest, data)
        .exit_dte(7)
    )

    assert results.total_profit() == 9330.0


def test_long_call_midpoint():
    filtered_opt_chains  = (
        data.start_date(datetime(2018, 1, 1))
        .end_date(datetime(2018, 2, 28))
        .entry_dte(31)
        .delta(0.30)
        .calls()
    )

    results = (
        op.long_call(filtered_opt_chains)
        .pipe(op.backtest, data, mode="midpoint")
        .exit_dte(7)
    )
    assert results.total_profit() == 9630.0


def test_long_call_expire():
    filtered_opt_chains = (
        data.start_date(datetime(2018, 1, 1))
        .end_date(datetime(2018, 2, 28))
        .entry_dte(31)
        .delta(0.30)
        .calls()
    )

    results = (
        op.long_call(filtered_opt_chains)
        .pipe(op.backtest, data)
        .exit_dte("expire")
    )
    assert results.total_profit() == 7710.0


def test_short_call():
    filtered_opt_chains = (
        data.start_date(datetime(2018, 1, 1))
        .end_date(datetime(2018, 2, 28))
        .entry_dte(31)
        .delta(0.30)
        .calls()
    )

    results = (
        op.short_call(filtered_opt_chains)
        .pipe(op.backtest, data)
        .exit_dte(7)
    )

    assert results.total_profit() == -9930.0


def test_long_put():
    filtered_opt_chains = (
        data.start_date(datetime(2018, 1, 1))
        .end_date(datetime(2018, 2, 28))
        .entry_dte(31)
        .delta(0.30)
        .puts()
    )

    results = (
        op.long_put(filtered_opt_chains)
        .pipe(op.backtest, data)
        .exit_dte(7)
    )
    assert results.total_profit() == 4470.0


def test_short_put():
    filtered_opt_chains = (
        data.start_date(datetime(2018, 1, 1))
        .end_date(datetime(2018, 2, 28))
        .entry_dte(31)
        .delta(0.30)
        .puts()
    )

    results = (
        op.short_put(filtered_opt_chains)
        .pipe(op.backtest, data)
        .exit_dte(7)
    )

    assert results.total_profit() == -5060.0
