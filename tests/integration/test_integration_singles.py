from optopsy.option_strategies import long_call, short_call, long_put, short_put
from optopsy.data import get
from datetime import datetime
import os
import pytest

CURRENT_FILE = os.path.abspath(os.path.dirname(__file__))
TEST_FILE_PATH_FULL = os.path.join(
    CURRENT_FILE, "../test_data/test_options_data_full.csv"
)


def test_long_call_market_integration(hod_struct):
    data = get(TEST_FILE_PATH_FULL, hod_struct, prompt=False)

    filters = {
        "start_date": datetime(2018, 1, 1),
        "end_date": datetime(2018, 2, 28),
        "entry_dte": 31,
        "leg1_delta": 0.30,
        "exit_dte": 7,
    }

    backtest = long_call(data, filters)
    print(backtest)
    assert backtest["cost"].sum() == -93300.0
    assert (
        backtest.iat[0, 5] == 1
        and backtest.iat[0, 9] == 0.31
        and backtest.iat[0, 8] == 2720
        and backtest.iat[0, 16] == -107800.0
    )
    assert (
        backtest.iat[1, 5] == 1
        and backtest.iat[1, 9] == 0.30
        and backtest.iat[1, 8] == 2865
        and backtest.iat[1, 16] == 14500.0
    )


def test_long_call_midpoint_integration(hod_struct):
    data = get(TEST_FILE_PATH_FULL, hod_struct, prompt=False)

    filters = {
        "start_date": datetime(2018, 1, 1),
        "end_date": datetime(2018, 2, 28),
        "entry_dte": 31,
        "leg1_delta": 0.30,
        "exit_dte": 7,
    }

    backtest = long_call(data, filters, mode="midpoint")
    print(backtest)
    assert backtest["cost"].sum() == -96300.0
    assert (
        backtest.iat[0, 5] == 1
        and backtest.iat[0, 9] == 0.31
        and backtest.iat[0, 8] == 2720
        and backtest.iat[0, 16] == -110550.0
    )
    assert (
        backtest.iat[1, 5] == 1
        and backtest.iat[1, 9] == 0.30
        and backtest.iat[1, 8] == 2865
        and backtest.iat[1, 16] == 14250.0
    )


def test_long_call_no_exit_dte_integration(hod_struct):
    data = get(TEST_FILE_PATH_FULL, hod_struct, prompt=False)

    filters = {
        "start_date": datetime(2018, 1, 1),
        "end_date": datetime(2018, 2, 28),
        "entry_dte": 31,
        "leg1_delta": 0.30,
    }

    backtest = long_call(data, filters)
    print(backtest)
    assert backtest["cost"].sum() == -77100.0
    assert (
        backtest.iat[0, 5] == 1
        and backtest.iat[0, 9] == 0.31
        and backtest.iat[0, 16] == -91600.0
    )
    assert (
        backtest.iat[1, 5] == 1
        and backtest.iat[1, 9] == 0.30
        and backtest.iat[1, 16] == 14500.0
    )


def test_short_call_market_integration(hod_struct):
    data = get(TEST_FILE_PATH_FULL, hod_struct, prompt=False)

    filters = {
        "start_date": datetime(2018, 1, 1),
        "end_date": datetime(2018, 2, 28),
        "entry_dte": 31,
        "leg1_delta": 0.30,
        "exit_dte": 7,
    }

    backtest = short_call(data, filters)
    print(backtest)
    assert backtest["cost"].sum() == 99300.0
    assert (
        backtest.iat[0, 5] == -1
        and backtest.iat[0, 9] == 0.31
        and backtest.iat[0, 16] == 113300.0
    )
    assert (
        backtest.iat[1, 5] == -1
        and backtest.iat[1, 9] == 0.30
        and backtest.iat[1, 16] == -14000.0
    )


def test_short_call_midpoint_integration(hod_struct):
    data = get(TEST_FILE_PATH_FULL, hod_struct, prompt=False)

    filters = {
        "start_date": datetime(2018, 1, 1),
        "end_date": datetime(2018, 2, 28),
        "entry_dte": 31,
        "leg1_delta": 0.30,
        "exit_dte": 7,
    }

    backtest = short_call(data, filters, mode="midpoint")
    print(backtest)
    assert backtest["cost"].sum() == 96300.0
    assert (
        backtest.iat[0, 5] == -1
        and backtest.iat[0, 9] == 0.31
        and backtest.iat[0, 16] == 110550.0
    )
    assert (
        backtest.iat[1, 5] == -1
        and backtest.iat[1, 9] == 0.30
        and backtest.iat[1, 16] == -14250.0
    )


def test_long_put_market_integration(hod_struct):
    data = get(TEST_FILE_PATH_FULL, hod_struct, prompt=False)

    filters = {
        "start_date": datetime(2018, 1, 1),
        "end_date": datetime(2018, 2, 28),
        "entry_dte": 31,
        "leg1_delta": 0.30,
        "exit_dte": 7,
    }

    backtest = long_put(data, filters)
    print(backtest)
    assert backtest["cost"].sum() == -44700.0
    assert (
        backtest.iat[0, 5] == 1
        and backtest.iat[0, 9] == -0.3
        and backtest.iat[0, 16] == 12800.0
    )
    assert (
        backtest.iat[1, 5] == 1
        and backtest.iat[1, 9] == -0.3
        and backtest.iat[1, 16] == -57500.0
    )


def test_long_put_midpoint_integration(hod_struct):
    data = get(TEST_FILE_PATH_FULL, hod_struct, prompt=False)

    filters = {
        "start_date": datetime(2018, 1, 1),
        "end_date": datetime(2018, 2, 28),
        "entry_dte": 31,
        "leg1_delta": 0.30,
        "exit_dte": 7,
    }

    backtest = long_put(data, filters)
    print(backtest)
    assert backtest["cost"].sum() == -44700.0
    assert (
        backtest.iat[0, 5] == 1
        and backtest.iat[0, 9] == -0.3
        and backtest.iat[0, 16] == 12800.0
    )
    assert (
        backtest.iat[1, 5] == 1
        and backtest.iat[1, 9] == -0.3
        and backtest.iat[1, 16] == -57500.0
    )


def test_short_put_market_integration(hod_struct):
    data = get(TEST_FILE_PATH_FULL, hod_struct, prompt=False)

    filters = {
        "start_date": datetime(2018, 1, 1),
        "end_date": datetime(2018, 2, 28),
        "entry_dte": 31,
        "leg1_delta": 0.30,
        "exit_dte": 7,
    }

    backtest = short_put(data, filters)
    print(backtest)
    assert backtest["cost"].sum() == 50600.0
    assert (
        backtest.iat[0, 5] == -1
        and backtest.iat[0, 9] == -0.3
        and backtest.iat[0, 16] == -12300.0
    )
    assert (
        backtest.iat[1, 5] == -1
        and backtest.iat[1, 9] == -0.3
        and backtest.iat[1, 16] == 62900.0
    )


def test_short_put_midpoint_integration(hod_struct):
    data = get(TEST_FILE_PATH_FULL, hod_struct, prompt=False)

    filters = {
        "start_date": datetime(2018, 1, 1),
        "end_date": datetime(2018, 2, 28),
        "entry_dte": 31,
        "leg1_delta": 0.30,
        "exit_dte": 7,
    }

    backtest = short_put(data, filters, mode="market")
    print(backtest)
    assert backtest["cost"].sum() == 50600.0
    assert (
        backtest.iat[0, 5] == -1
        and backtest.iat[0, 9] == -0.3
        and backtest.iat[0, 16] == -12300.0
    )
    assert (
        backtest.iat[1, 5] == -1
        and backtest.iat[1, 9] == -0.3
        and backtest.iat[1, 16] == 62900.0
    )

