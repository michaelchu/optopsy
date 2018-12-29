from optopsy.option_strategies import long_call, short_call, long_put, short_put
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


def test_long_call_market_integration():
    filters = {
        "start_date": datetime(2018, 1, 1),
        "end_date": datetime(2018, 2, 28),
        "entry_dte": 31,
        "leg1_delta": 0.30,
        "exit_dte": 7,
    }

    backtest = long_call(DATA, filters)
    print(backtest)
    assert backtest["cost"].sum() == -9330.0
    assert (
        backtest.iat[0, 5] == 1
        and backtest.iat[0, 9] == 0.31
        and backtest.iat[0, 8] == 2720
        and backtest.iat[0, 16] == -10780.0
    )
    assert (
        backtest.iat[1, 5] == 1
        and backtest.iat[1, 9] == 0.30
        and backtest.iat[1, 8] == 2865
        and backtest.iat[1, 16] == 1450.0
    )


def test_long_call_midpoint_integration():
    filters = {
        "start_date": datetime(2018, 1, 1),
        "end_date": datetime(2018, 2, 28),
        "entry_dte": 31,
        "leg1_delta": 0.30,
        "exit_dte": 7,
    }

    backtest = long_call(DATA, filters, mode="midpoint")
    print(backtest)
    assert backtest["cost"].sum() == -9630.0
    assert (
        backtest.iat[0, 5] == 1
        and backtest.iat[0, 9] == 0.31
        and backtest.iat[0, 8] == 2720
        and backtest.iat[0, 16] == -11055.0
    )
    assert (
        backtest.iat[1, 5] == 1
        and backtest.iat[1, 9] == 0.30
        and backtest.iat[1, 8] == 2865
        and backtest.iat[1, 16] == 1425.0
    )


def test_long_call_no_exit_dte_integration():
    filters = {
        "start_date": datetime(2018, 1, 1),
        "end_date": datetime(2018, 2, 28),
        "entry_dte": 31,
        "leg1_delta": 0.30,
    }

    backtest = long_call(DATA, filters)
    print(backtest)
    assert backtest["cost"].sum() == -7710.0
    assert (
        backtest.iat[0, 5] == 1
        and backtest.iat[0, 9] == 0.31
        and backtest.iat[0, 16] == -9160.0
    )
    assert (
        backtest.iat[1, 5] == 1
        and backtest.iat[1, 9] == 0.30
        and backtest.iat[1, 16] == 1450.0
    )


def test_short_call_market_integration():
    filters = {
        "start_date": datetime(2018, 1, 1),
        "end_date": datetime(2018, 2, 28),
        "entry_dte": 31,
        "leg1_delta": 0.30,
        "exit_dte": 7,
    }

    backtest = short_call(DATA, filters)
    print(backtest)
    assert backtest["cost"].sum() == 9930.0
    assert (
        backtest.iat[0, 5] == -1
        and backtest.iat[0, 9] == 0.31
        and backtest.iat[0, 16] == 11330.0
    )
    assert (
        backtest.iat[1, 5] == -1
        and backtest.iat[1, 9] == 0.30
        and backtest.iat[1, 16] == -1400.0
    )


def test_short_call_midpoint_integration():
    filters = {
        "start_date": datetime(2018, 1, 1),
        "end_date": datetime(2018, 2, 28),
        "entry_dte": 31,
        "leg1_delta": 0.30,
        "exit_dte": 7,
    }

    backtest = short_call(DATA, filters, mode="midpoint")
    print(backtest)
    assert backtest["cost"].sum() == 9630.0
    assert (
        backtest.iat[0, 5] == -1
        and backtest.iat[0, 9] == 0.31
        and backtest.iat[0, 16] == 11055.0
    )
    assert (
        backtest.iat[1, 5] == -1
        and backtest.iat[1, 9] == 0.30
        and backtest.iat[1, 16] == -1425.0
    )


def test_long_put_market_integration():
    filters = {
        "start_date": datetime(2018, 1, 1),
        "end_date": datetime(2018, 2, 28),
        "entry_dte": 31,
        "leg1_delta": 0.30,
        "exit_dte": 7,
    }

    backtest = long_put(DATA, filters)
    print(backtest)
    assert backtest["cost"].sum() == -4470.0
    assert (
        backtest.iat[0, 5] == 1
        and backtest.iat[0, 9] == -0.3
        and backtest.iat[0, 16] == 1280.0
    )
    assert (
        backtest.iat[1, 5] == 1
        and backtest.iat[1, 9] == -0.3
        and backtest.iat[1, 16] == -5750.0
    )


def test_long_put_midpoint_integration():
    filters = {
        "start_date": datetime(2018, 1, 1),
        "end_date": datetime(2018, 2, 28),
        "entry_dte": 31,
        "leg1_delta": 0.30,
        "exit_dte": 7,
    }

    backtest = long_put(DATA, filters)
    print(backtest)
    assert backtest["cost"].sum() == -4470.0
    assert (
        backtest.iat[0, 5] == 1
        and backtest.iat[0, 9] == -0.3
        and backtest.iat[0, 16] == 1280.0
    )
    assert (
        backtest.iat[1, 5] == 1
        and backtest.iat[1, 9] == -0.3
        and backtest.iat[1, 16] == -5750.0
    )


def test_short_put_market_integration():
    filters = {
        "start_date": datetime(2018, 1, 1),
        "end_date": datetime(2018, 2, 28),
        "entry_dte": 31,
        "leg1_delta": 0.30,
        "exit_dte": 7,
    }

    backtest = short_put(DATA, filters)
    print(backtest)
    assert backtest["cost"].sum() == 5060.0
    assert (
        backtest.iat[0, 5] == -1
        and backtest.iat[0, 9] == -0.3
        and backtest.iat[0, 16] == -1230.0
    )
    assert (
        backtest.iat[1, 5] == -1
        and backtest.iat[1, 9] == -0.3
        and backtest.iat[1, 16] == 6290.0
    )


def test_short_put_midpoint_integration():
    filters = {
        "start_date": datetime(2018, 1, 1),
        "end_date": datetime(2018, 2, 28),
        "entry_dte": 31,
        "leg1_delta": 0.30,
        "exit_dte": 7,
    }

    backtest = short_put(DATA, filters, mode="market")
    print(backtest)
    assert backtest["cost"].sum() == 5060.0
    assert (
        backtest.iat[0, 5] == -1
        and backtest.iat[0, 9] == -0.3
        and backtest.iat[0, 16] == -1230.0
    )
    assert (
        backtest.iat[1, 5] == -1
        and backtest.iat[1, 9] == -0.3
        and backtest.iat[1, 16] == 6290.0
    )
