import pytest
import pandas as pd
import datetime as datetime

from optopsy.strategies import *
from optopsy.definitions import *


describe_long_cols = [
    "long_profit_pct_count",
    "long_profit_pct_mean",
    "long_profit_pct_std",
    "long_profit_pct_min",
    "long_profit_pct_25%",
    "long_profit_pct_50%",
    "long_profit_pct_75%",
    "long_profit_pct_max",
]

describe_short_cols = [
    "short_profit_pct_count",
    "short_profit_pct_mean",
    "short_profit_pct_std",
    "short_profit_pct_min",
    "short_profit_pct_25%",
    "short_profit_pct_50%",
    "short_profit_pct_75%",
    "short_profit_pct_max",
]


@pytest.fixture(scope="module")
def data():
    exp_date = datetime.datetime(2018, 1, 31)
    quote_dates = [datetime.datetime(2018, 1, 1), datetime.datetime(2018, 1, 31)]
    cols = [
        "underlying_symbol",
        "underlying_price",
        "option_type",
        "expiration",
        "quote_date",
        "strike",
        "bid",
        "ask",
    ]
    d = [
        ["SPX", 1000, "call", exp_date, quote_dates[0], 900, 120, 121],
        ["SPX", 1000, "call", exp_date, quote_dates[0], 1000, 100, 101],
        ["SPX", 1000, "put", exp_date, quote_dates[0], 900, 80, 81],
        ["SPX", 1000, "put", exp_date, quote_dates[0], 1000, 100, 101],
        ["SPX", 1060, "call", exp_date, quote_dates[1], 900, 150, 151],
        ["SPX", 1060, "call", exp_date, quote_dates[1], 1000, 130, 131],
        ["SPX", 1060, "put", exp_date, quote_dates[1], 900, 50, 51],
        ["SPX", 1060, "put", exp_date, quote_dates[1], 1000, 70, 71],
    ]
    return pd.DataFrame(data=d, columns=cols)


def test_single_calls_raw(data):
    results = singles_calls(data, raw=True, side="long")
    assert list(results.columns) == single_strike_internal_cols
    assert results.iloc[0]["option_type"] == "call"


def test_single_puts_raw(data):
    results = singles_puts(data, raw=True, side="long")
    assert list(results.columns) == single_strike_internal_cols
    assert results.iloc[0]["option_type"] == "put"


def test_singles_long_calls(data):
    results = singles_calls(data, side="long")
    assert len(results) == 2
    assert results.iloc[0]["long_profit_pct_count"] == 1.0
    assert results.iloc[1]["long_profit_pct_count"] == 1.0
    assert results.iloc[0]["long_profit_pct_mean"] == 0.25
    assert results.iloc[1]["long_profit_pct_mean"] == 0.30
    assert list(results.columns) == single_strike_external_cols + describe_long_cols


def test_singles_long_puts(data):
    results = singles_puts(data, side="long")
    assert len(results) == 2
    assert results.iloc[0]["long_profit_pct_count"] == 1.0
    assert results.iloc[1]["long_profit_pct_count"] == 1.0
    assert results.iloc[0]["long_profit_pct_mean"] == -0.37
    assert results.iloc[1]["long_profit_pct_mean"] == -0.30
    assert list(results.columns) == single_strike_external_cols + describe_long_cols


def test_singles_short_calls(data):
    results = singles_calls(data, side="short")
    assert len(results) == 2
    assert results.iloc[0]["short_profit_pct_count"] == 1.0
    assert results.iloc[1]["short_profit_pct_count"] == 1.0
    assert results.iloc[0]["short_profit_pct_mean"] == -0.25
    assert results.iloc[1]["short_profit_pct_mean"] == -0.30
    assert list(results.columns) == single_strike_external_cols + describe_short_cols


def test_singles_short_puts(data):
    results = singles_puts(data, side="short")
    assert len(results) == 2
    assert results.iloc[0]["short_profit_pct_count"] == 1.0
    assert results.iloc[1]["short_profit_pct_count"] == 1.0
    assert results.iloc[0]["short_profit_pct_mean"] == 0.37
    assert results.iloc[1]["short_profit_pct_mean"] == 0.30
    assert list(results.columns) == single_strike_external_cols + describe_short_cols


def test_straddles_raw(data):
    results = straddles(data, raw=True, side="long")
    assert list(results.columns) == straddle_internal_cols
    assert results.iloc[0]["option_type_leg1"] == "put"
    assert results.iloc[0]["option_type_leg2"] == "call"


def test_long_straddles(data):
    results = straddles(data, side="long")
    assert len(results) == 2
    assert results.iloc[0]["long_profit_pct_count"] == 1.0
    assert results.iloc[1]["long_profit_pct_count"] == 1.0
    assert results.iloc[0]["long_profit_pct_mean"] == 0.0
    assert results.iloc[1]["long_profit_pct_mean"] == 0.0
    assert list(results.columns) == single_strike_external_cols + describe_long_cols


def test_short_straddles(data):
    results = straddles(data, side="short")
    assert len(results) == 2
    assert results.iloc[0]["short_profit_pct_count"] == 1.0
    assert results.iloc[1]["short_profit_pct_count"] == 1.0
    assert results.iloc[0]["short_profit_pct_mean"] == 0.0
    assert results.iloc[1]["short_profit_pct_mean"] == 0.0
    assert list(results.columns) == single_strike_external_cols + describe_short_cols


def test_strangles_raw(data):
    results = strangles(data, raw=True, side="long")
    assert list(results.columns) == double_strike_internal_cols
    assert results.iloc[0]["option_type_leg1"] == "put"
    assert results.iloc[0]["option_type_leg2"] == "call"


def test_long_strangles(data):
    results = strangles(data, side="long")
    assert len(results) == 1
    assert results.iloc[0]["long_profit_pct_count"] == 1.0
    assert results.iloc[0]["long_profit_pct_mean"] == 0.0
    assert list(results.columns) == double_strike_external_cols + describe_long_cols


def test_short_strangles(data):
    results = strangles(data, side="short")
    assert len(results) == 1
    assert results.iloc[0]["short_profit_pct_count"] == 1.0
    assert results.iloc[0]["short_profit_pct_mean"] == 0.0
    assert list(results.columns) == double_strike_external_cols + describe_short_cols
