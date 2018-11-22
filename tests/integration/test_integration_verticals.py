from optopsy.backtest import run
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


def test_long_call_spread_integration(hod_struct):
    data = get(TEST_FILE_PATH_FULL, hod_struct, prompt=False)

    filters = {"entry_dte": 31, "leg1_delta": 0.50, "leg2_delta": 0.30, "exit_dte": 7}

    start = datetime(2018, 1, 1)
    end = datetime(2018, 2, 28)

    trades = long_call_spread(data, start, end, filters)
    backtest = run(data, trades, filters)
    print(backtest[1])
    assert backtest[0] == 8025
    assert (
        backtest[1].iat[0, 5] == 1
        and backtest[1].iat[0, 8] == 2700
        and backtest[1].iat[0, 9] == 0.49
        and backtest[1].iat[0, 16] == -121000.0
    )
    assert (
        backtest[1].iat[1, 5] == -1
        and backtest[1].iat[1, 8] == 2720
        and backtest[1].iat[1, 9] == 0.31
        and backtest[1].iat[1, 16] == 110550.0
    )
    assert (
        backtest[1].iat[2, 5] == 1
        and backtest[1].iat[2, 8] == 2825
        and backtest[1].iat[2, 9] == 0.51
        and backtest[1].iat[2, 16] == 32725.0
    )
    assert (
        backtest[1].iat[3, 5] == -1
        and backtest[1].iat[3, 8] == 2865
        and backtest[1].iat[3, 9] == 0.30
        and backtest[1].iat[3, 16] == -14250.0
    )


def test_long_call_spread_market_integration(hod_struct):
    data = get(TEST_FILE_PATH_FULL, hod_struct, prompt=False)

    filters = {"entry_dte": 31, "leg1_delta": 0.50, "leg2_delta": 0.30, "exit_dte": 7}

    start = datetime(2018, 1, 1)
    end = datetime(2018, 2, 28)

    trades = long_call_spread(data, start, end, filters)
    backtest = run(data, trades, filters, mode="market")
    print(backtest[1])
    assert backtest[0] == 14250.0
    assert (
        backtest[1].iat[0, 5] == 1
        and backtest[1].iat[0, 8] == 2700
        and backtest[1].iat[0, 9] == 0.49
        and backtest[1].iat[0, 16] == -118100.0
    )
    assert (
        backtest[1].iat[1, 5] == -1
        and backtest[1].iat[1, 8] == 2720
        and backtest[1].iat[1, 9] == 0.31
        and backtest[1].iat[1, 16] == 113300.0
    )
    assert (
        backtest[1].iat[2, 5] == 1
        and backtest[1].iat[2, 8] == 2825
        and backtest[1].iat[2, 9] == 0.51
        and backtest[1].iat[2, 16] == 33050.0
    )
    assert (
        backtest[1].iat[3, 5] == -1
        and backtest[1].iat[3, 8] == 2865
        and backtest[1].iat[3, 9] == 0.30
        and backtest[1].iat[3, 16] == -14000.0
    )


def test_long_call_spread_no_exit_dte_integration(hod_struct):
    data = get(TEST_FILE_PATH_FULL, hod_struct, prompt=False)

    filters = {"entry_dte": 31, "leg1_delta": 0.50, "leg2_delta": 0.30}

    start = datetime(2018, 1, 1)
    end = datetime(2018, 2, 28)

    trades = long_call_spread(data, start, end, filters)
    backtest = run(data, trades, filters)
    print(backtest[1])
    assert backtest[0] == 7200.00
    assert (
        backtest[1].iat[0, 5] == 1
        and backtest[1].iat[0, 8] == 2700
        and backtest[1].iat[0, 9] == 0.49
        and backtest[1].iat[0, 16] == -107600.0
    )
    assert (
        backtest[1].iat[1, 5] == -1
        and backtest[1].iat[1, 8] == 2720
        and backtest[1].iat[1, 9] == 0.31
        and backtest[1].iat[1, 16] == 96200.0
    )
    assert (
        backtest[1].iat[2, 5] == 1
        and backtest[1].iat[2, 8] == 2825
        and backtest[1].iat[2, 9] == 0.51
        and backtest[1].iat[2, 16] == 32925.0
    )
    assert (
        backtest[1].iat[3, 5] == -1
        and backtest[1].iat[3, 8] == 2865
        and backtest[1].iat[3, 9] == 0.30
        and backtest[1].iat[3, 16] == -14325.0
    )


def test_short_call_spread_integration(hod_struct):
    data = get(TEST_FILE_PATH_FULL, hod_struct, prompt=False)

    filters = {"entry_dte": 31, "leg1_delta": 0.50, "leg2_delta": 0.30, "exit_dte": 7}

    start = datetime(2018, 1, 1)
    end = datetime(2018, 2, 28)

    trades = short_call_spread(data, start, end, filters)
    backtest = run(data, trades, filters)
    print(backtest[1])
    assert backtest[0] == -8025
    assert (
        backtest[1].iat[0, 5] == -1
        and backtest[1].iat[0, 8] == 2700
        and backtest[1].iat[0, 9] == 0.49
        and backtest[1].iat[0, 16] == 121000.0
    )
    assert (
        backtest[1].iat[1, 5] == 1
        and backtest[1].iat[1, 8] == 2720
        and backtest[1].iat[1, 9] == 0.31
        and backtest[1].iat[1, 16] == -110550.0
    )
    assert (
        backtest[1].iat[2, 5] == -1
        and backtest[1].iat[2, 8] == 2825
        and backtest[1].iat[2, 9] == 0.51
        and backtest[1].iat[2, 16] == -32725.0
    )
    assert (
        backtest[1].iat[3, 5] == 1
        and backtest[1].iat[3, 8] == 2865
        and backtest[1].iat[3, 9] == 0.30
        and backtest[1].iat[3, 16] == 14250.0
    )


def test_long_put_spread_integration(hod_struct):
    data = get(TEST_FILE_PATH_FULL, hod_struct, prompt=False)

    filters = {"entry_dte": 31, "leg1_delta": 0.30, "leg2_delta": 0.50, "exit_dte": 7}

    start = datetime(2018, 1, 1)
    end = datetime(2018, 2, 28)

    trades = long_put_spread(data, start, end, filters)
    backtest = run(data, trades, filters)
    print(backtest[1])
    assert backtest[0] == -25650
    assert (
        backtest[1].iat[0, 5] == -1
        and backtest[1].iat[0, 8] == 2665
        and backtest[1].iat[0, 9] == -0.30
        and backtest[1].iat[0, 16] == -12550.0
    )
    assert (
        backtest[1].iat[1, 5] == 1
        and backtest[1].iat[1, 8] == 2700
        and backtest[1].iat[1, 9] == -0.51
        and backtest[1].iat[1, 16] == 22400.0
    )
    assert (
        backtest[1].iat[2, 5] == -1
        and backtest[1].iat[2, 8] == 2775
        and backtest[1].iat[2, 9] == -0.30
        and backtest[1].iat[2, 16] == 60200.0
    )
    assert (
        backtest[1].iat[3, 5] == 1
        and backtest[1].iat[3, 8] == 2830
        and backtest[1].iat[3, 9] == -0.51
        and backtest[1].iat[3, 16] == -95700.0
    )


def test_short_put_spread_integration(hod_struct):
    data = get(TEST_FILE_PATH_FULL, hod_struct, prompt=False)

    filters = {"entry_dte": 31, "leg1_delta": 0.30, "leg2_delta": 0.50, "exit_dte": 7}

    start = datetime(2018, 1, 1)
    end = datetime(2018, 2, 28)

    trades = short_put_spread(data, start, end, filters)
    backtest = run(data, trades, filters)
    print(backtest[1])
    assert backtest[0] == 25650
    assert (
        backtest[1].iat[0, 5] == 1
        and backtest[1].iat[0, 8] == 2665
        and backtest[1].iat[0, 9] == -0.30
        and backtest[1].iat[0, 16] == 12550.0
    )
    assert (
        backtest[1].iat[1, 5] == -1
        and backtest[1].iat[1, 8] == 2700
        and backtest[1].iat[1, 9] == -0.51
        and backtest[1].iat[1, 16] == -22400.0
    )
    assert (
        backtest[1].iat[2, 5] == 1
        and backtest[1].iat[2, 8] == 2775
        and backtest[1].iat[2, 9] == -0.30
        and backtest[1].iat[2, 16] == -60200.0
    )
    assert (
        backtest[1].iat[3, 5] == -1
        and backtest[1].iat[3, 8] == 2830
        and backtest[1].iat[3, 9] == -0.51
        and backtest[1].iat[3, 16] == 95700.0
    )
