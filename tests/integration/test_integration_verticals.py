from optopsy.option_strategies import (
    long_call_spread,
    short_call_spread,
    long_put_spread,
    short_put_spread,
)
from optopsy.data import get
from datetime import datetime
import os
import pytest

CURRENT_FILE = os.path.abspath(os.path.dirname(__file__))
TEST_FILE_PATH_FULL = os.path.join(
    CURRENT_FILE, "../test_data/test_options_data_full.csv"
)

hod_struct = (
    ("underlying_symbol", 0),
    ("underlying_price", 1),
    ("option_type", 5),
    ("expiration", 6),
    ("quote_date", 7),
    ("strike", 8),
    ("bid", 10),
    ("ask", 11),
    ("delta", 15),
    ("gamma", 16),
    ("theta", 17),
    ("vega", 18),
)

DATA = get(TEST_FILE_PATH_FULL, hod_struct, prompt=False)


def test_long_call_spread_integration():
    filters = {
        "start_date": datetime(2018, 1, 1),
        "end_date": datetime(2018, 2, 28),
        "entry_dte": 31,
        "leg1_delta": 0.50,
        "leg2_delta": 0.30,
        "exit_dte": 7,
    }

    backtest = long_call_spread(DATA, filters, mode="midpoint")
    print(backtest)
    assert backtest["cost"].sum() == 802.5
    assert (
        backtest.iat[0, 5] == 1
        and backtest.iat[0, 8] == 2700
        and backtest.iat[0, 9] == 0.49
        and backtest.iat[0, 16] == -12100.0
    )
    assert (
        backtest.iat[1, 5] == -1
        and backtest.iat[1, 8] == 2720
        and backtest.iat[1, 9] == 0.31
        and backtest.iat[1, 16] == 11055.0
    )
    assert (
        backtest.iat[2, 5] == 1
        and backtest.iat[2, 8] == 2825
        and backtest.iat[2, 9] == 0.51
        and backtest.iat[2, 16] == 3272.5
    )
    assert (
        backtest.iat[3, 5] == -1
        and backtest.iat[3, 8] == 2865
        and backtest.iat[3, 9] == 0.30
        and backtest.iat[3, 16] == -1425.0
    )


def test_long_call_spread_market_integration():
    filters = {
        "start_date": datetime(2018, 1, 1),
        "end_date": datetime(2018, 2, 28),
        "entry_dte": 31,
        "leg1_delta": 0.50,
        "leg2_delta": 0.30,
        "exit_dte": 7,
    }

    backtest = long_call_spread(DATA, filters)
    print(backtest)
    assert backtest["cost"].sum() == 1425.0
    assert (
        backtest.iat[0, 5] == 1
        and backtest.iat[0, 8] == 2700
        and backtest.iat[0, 9] == 0.49
        and backtest.iat[0, 16] == -11810.0
    )
    assert (
        backtest.iat[1, 5] == -1
        and backtest.iat[1, 8] == 2720
        and backtest.iat[1, 9] == 0.31
        and backtest.iat[1, 16] == 11330.0
    )
    assert (
        backtest.iat[2, 5] == 1
        and backtest.iat[2, 8] == 2825
        and backtest.iat[2, 9] == 0.51
        and backtest.iat[2, 16] == 3305.0
    )
    assert (
        backtest.iat[3, 5] == -1
        and backtest.iat[3, 8] == 2865
        and backtest.iat[3, 9] == 0.30
        and backtest.iat[3, 16] == -1400.0
    )


def test_long_call_spread_no_exit_dte_integration():
    filters = {
        "start_date": datetime(2018, 1, 1),
        "end_date": datetime(2018, 2, 28),
        "entry_dte": 31,
        "leg1_delta": 0.50,
        "leg2_delta": 0.30,
    }

    backtest = long_call_spread(DATA, filters, mode="midpoint")
    print(backtest)
    assert backtest["cost"].sum() == 720.0
    assert (
        backtest.iat[0, 5] == 1
        and backtest.iat[0, 8] == 2700
        and backtest.iat[0, 9] == 0.49
        and backtest.iat[0, 16] == -10760.0
    )
    assert (
        backtest.iat[1, 5] == -1
        and backtest.iat[1, 8] == 2720
        and backtest.iat[1, 9] == 0.31
        and backtest.iat[1, 16] == 9620.0
    )
    assert (
        backtest.iat[2, 5] == 1
        and backtest.iat[2, 8] == 2825
        and backtest.iat[2, 9] == 0.51
        and backtest.iat[2, 16] == 3292.5
    )
    assert (
        backtest.iat[3, 5] == -1
        and backtest.iat[3, 8] == 2865
        and backtest.iat[3, 9] == 0.30
        and backtest.iat[3, 16] == -1432.5
    )


def test_short_call_spread_integration():
    filters = {
        "start_date": datetime(2018, 1, 1),
        "end_date": datetime(2018, 2, 28),
        "entry_dte": 31,
        "leg1_delta": 0.50,
        "leg2_delta": 0.30,
        "exit_dte": 7,
    }

    backtest = short_call_spread(DATA, filters, mode="midpoint")
    print(backtest)
    assert backtest["cost"].sum() == -802.5
    assert (
        backtest.iat[0, 5] == -1
        and backtest.iat[0, 8] == 2700
        and backtest.iat[0, 9] == 0.49
        and backtest.iat[0, 16] == 12100.0
    )
    assert (
        backtest.iat[1, 5] == 1
        and backtest.iat[1, 8] == 2720
        and backtest.iat[1, 9] == 0.31
        and backtest.iat[1, 16] == -11055.0
    )
    assert (
        backtest.iat[2, 5] == -1
        and backtest.iat[2, 8] == 2825
        and backtest.iat[2, 9] == 0.51
        and backtest.iat[2, 16] == -3272.5
    )
    assert (
        backtest.iat[3, 5] == 1
        and backtest.iat[3, 8] == 2865
        and backtest.iat[3, 9] == 0.30
        and backtest.iat[3, 16] == 1425.0
    )


def test_long_put_spread_integration():
    filters = {
        "start_date": datetime(2018, 1, 1),
        "end_date": datetime(2018, 2, 28),
        "entry_dte": 31,
        "leg1_delta": 0.30,
        "leg2_delta": 0.50,
        "exit_dte": 7,
    }

    backtest = long_put_spread(DATA, filters, mode="midpoint")
    print(backtest)
    assert backtest["cost"].sum() == -2565.0
    assert (
        backtest.iat[0, 5] == -1
        and backtest.iat[0, 8] == 2665
        and backtest.iat[0, 9] == -0.30
        and backtest.iat[0, 16] == -1255.0
    )
    assert (
        backtest.iat[1, 5] == 1
        and backtest.iat[1, 8] == 2700
        and backtest.iat[1, 9] == -0.51
        and backtest.iat[1, 16] == 2240.0
    )
    assert (
        backtest.iat[2, 5] == -1
        and backtest.iat[2, 8] == 2775
        and backtest.iat[2, 9] == -0.30
        and backtest.iat[2, 16] == 6020.0
    )
    assert (
        backtest.iat[3, 5] == 1
        and backtest.iat[3, 8] == 2830
        and backtest.iat[3, 9] == -0.51
        and backtest.iat[3, 16] == -9570.0
    )


def test_short_put_spread_integration():
    filters = {
        "start_date": datetime(2018, 1, 1),
        "end_date": datetime(2018, 2, 28),
        "entry_dte": 31,
        "leg1_delta": 0.30,
        "leg2_delta": 0.50,
        "exit_dte": 7,
    }

    backtest = short_put_spread(DATA, filters, mode="midpoint")
    print(backtest)
    assert backtest["cost"].sum() == 2565.0
    assert (
        backtest.iat[0, 5] == 1
        and backtest.iat[0, 8] == 2665
        and backtest.iat[0, 9] == -0.30
        and backtest.iat[0, 16] == 1255.0
    )
    assert (
        backtest.iat[1, 5] == -1
        and backtest.iat[1, 8] == 2700
        and backtest.iat[1, 9] == -0.51
        and backtest.iat[1, 16] == -2240.0
    )
    assert (
        backtest.iat[2, 5] == 1
        and backtest.iat[2, 8] == 2775
        and backtest.iat[2, 9] == -0.30
        and backtest.iat[2, 16] == -6020.0
    )
    assert (
        backtest.iat[3, 5] == -1
        and backtest.iat[3, 8] == 2830
        and backtest.iat[3, 9] == -0.51
        and backtest.iat[3, 16] == 9570.0
    )
