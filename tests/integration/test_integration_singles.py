from optopsy.backtest import run
from optopsy.option_strategies import long_call, short_call, long_put, short_put
from optopsy.data import get
from datetime import datetime
import os
import pytest

CURRENT_FILE = os.path.abspath(os.path.dirname(__file__))
TEST_FILE_PATH_FULL = os.path.join(
    CURRENT_FILE, "../test_data/test_options_data_full.csv"
)


def test_long_call_integration(hod_struct):
    data = get(TEST_FILE_PATH_FULL, hod_struct, prompt=False)

    filters = {"entry_dte": 31, "leg1_delta": 0.30, "exit_dte": 7}

    start = datetime(2018, 1, 1)
    end = datetime(2018, 2, 28)

    trades = long_call(data, start, end, filters)
    backtest = run(data, trades, filters)
    print(backtest[1])
    assert backtest[0] == -96300.0
    assert (
        backtest[1].iat[0, 5] == 1
        and backtest[1].iat[0, 9] == 0.31
        and backtest[1].iat[0, 8] == 2720
        and backtest[1].iat[0, 16] == -110550.0
    )
    assert (
        backtest[1].iat[1, 5] == 1
        and backtest[1].iat[1, 9] == 0.30
        and backtest[1].iat[1, 8] == 2865
        and backtest[1].iat[1, 16] == 14250.0
    )


def test_long_call_market_integration(hod_struct):
    data = get(TEST_FILE_PATH_FULL, hod_struct, prompt=False)

    filters = {"entry_dte": 31, "leg1_delta": 0.30, "exit_dte": 7}

    start = datetime(2018, 1, 1)
    end = datetime(2018, 2, 28)

    trades = long_call(data, start, end, filters)
    backtest = run(data, trades, filters, mode="market")
    print(backtest[1])
    assert backtest[0] == -93300.0
    assert (
        backtest[1].iat[0, 5] == 1
        and backtest[1].iat[0, 9] == 0.31
        and backtest[1].iat[0, 8] == 2720
        and backtest[1].iat[0, 16] == -107800.0
    )
    assert (
        backtest[1].iat[1, 5] == 1
        and backtest[1].iat[1, 9] == 0.30
        and backtest[1].iat[1, 8] == 2865
        and backtest[1].iat[1, 16] == 14500.0
    )


def test_long_call_no_exit_dte_integration(hod_struct):
    data = get(TEST_FILE_PATH_FULL, hod_struct, prompt=False)

    filters = {"entry_dte": 31, "leg1_delta": 0.30}

    start = datetime(2018, 1, 1)
    end = datetime(2018, 2, 28)

    trades = long_call(data, start, end, filters)
    backtest = run(data, trades, filters)
    print(backtest[1])
    assert backtest[0] == -81875
    assert (
        backtest[1].iat[0, 5] == 1
        and backtest[1].iat[0, 9] == 0.31
        and backtest[1].iat[0, 16] == -96200.0
    )
    assert (
        backtest[1].iat[1, 5] == 1
        and backtest[1].iat[1, 9] == 0.30
        and backtest[1].iat[1, 16] == 14325.0
    )


def test_short_call_integration(hod_struct):
    data = get(TEST_FILE_PATH_FULL, hod_struct, prompt=False)

    filters = {"entry_dte": 31, "leg1_delta": 0.30, "exit_dte": 7}

    start = datetime(2018, 1, 1)
    end = datetime(2018, 2, 28)

    trades = short_call(data, start, end, filters)
    backtest = run(data, trades, filters)
    assert backtest[0] == 96300.0
    assert (
        backtest[1].iat[0, 5] == -1
        and backtest[1].iat[0, 9] == 0.31
        and backtest[1].iat[0, 16] == 110550.0
    )
    assert (
        backtest[1].iat[1, 5] == -1
        and backtest[1].iat[1, 9] == 0.30
        and backtest[1].iat[1, 16] == -14250.0
    )


def test_long_put_integration(hod_struct):
    data = get(TEST_FILE_PATH_FULL, hod_struct, prompt=False)

    filters = {"entry_dte": 31, "leg1_delta": 0.30, "exit_dte": 7}

    start = datetime(2018, 1, 1)
    end = datetime(2018, 2, 28)

    trades = long_put(data, start, end, filters)
    backtest = run(data, trades, filters)
    print(backtest[1])
    assert backtest[0] == -47650
    assert (
        backtest[1].iat[0, 5] == 1
        and backtest[1].iat[0, 9] == -0.3
        and backtest[1].iat[0, 16] == 12550.0
    )
    assert (
        backtest[1].iat[1, 5] == 1
        and backtest[1].iat[1, 9] == -0.3
        and backtest[1].iat[1, 16] == -60200.0
    )


def test_short_put_integration(hod_struct):
    data = get(TEST_FILE_PATH_FULL, hod_struct, prompt=False)

    filters = {"entry_dte": 31, "leg1_delta": 0.30, "exit_dte": 7}

    start = datetime(2018, 1, 1)
    end = datetime(2018, 2, 28)

    trades = short_put(data, start, end, filters)
    backtest = run(data, trades, filters)
    assert backtest[0] == 47650
    assert (
        backtest[1].iat[0, 5] == -1
        and backtest[1].iat[0, 9] == -0.3
        and backtest[1].iat[0, 16] == -12550.0
    )
    assert (
        backtest[1].iat[1, 5] == -1
        and backtest[1].iat[1, 9] == -0.3
        and backtest[1].iat[1, 16] == 60200.0
    )
