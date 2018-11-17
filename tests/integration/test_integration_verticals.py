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
    assert backtest[0] == -80.25
    assert (
        backtest[1].iat[0, 5] == 1
        and backtest[1].iat[0, 8] == 2700
        and backtest[1].iat[0, 9] == 0.49
    )
    assert (
        backtest[1].iat[1, 5] == -1
        and backtest[1].iat[1, 8] == 2720
        and backtest[1].iat[1, 9] == 0.31
    )
    assert (
        backtest[1].iat[2, 5] == 1
        and backtest[1].iat[2, 8] == 2825
        and backtest[1].iat[2, 9] == 0.51
    )
    assert (
        backtest[1].iat[3, 5] == -1
        and backtest[1].iat[3, 8] == 2865
        and backtest[1].iat[3, 9] == 0.30
    )


def test_long_call_spread_no_exit_dte_integration(hod_struct):
    data = get(TEST_FILE_PATH_FULL, hod_struct, prompt=False)

    filters = {"entry_dte": 31, "leg1_delta": 0.50, "leg2_delta": 0.30}

    start = datetime(2018, 1, 1)
    end = datetime(2018, 2, 28)

    trades = long_call_spread(data, start, end, filters)
    backtest = run(data, trades, filters)
    print(backtest[1])
    assert backtest[0] == -72.00
    assert (
        backtest[1].iat[0, 5] == 1
        and backtest[1].iat[0, 8] == 2700
        and backtest[1].iat[0, 9] == 0.49
    )
    assert (
        backtest[1].iat[1, 5] == -1
        and backtest[1].iat[1, 8] == 2720
        and backtest[1].iat[1, 9] == 0.31
    )
    assert (
        backtest[1].iat[2, 5] == 1
        and backtest[1].iat[2, 8] == 2825
        and backtest[1].iat[2, 9] == 0.51
    )
    assert (
        backtest[1].iat[3, 5] == -1
        and backtest[1].iat[3, 8] == 2865
        and backtest[1].iat[3, 9] == 0.30
    )


def test_short_call_spread_integration(hod_struct):
    data = get(TEST_FILE_PATH_FULL, hod_struct, prompt=False)

    filters = {"entry_dte": 31, "leg1_delta": 0.50, "leg2_delta": 0.30, "exit_dte": 7}

    start = datetime(2018, 1, 1)
    end = datetime(2018, 2, 28)

    trades = short_call_spread(data, start, end, filters)
    backtest = run(data, trades, filters)
    print(backtest[1])
    assert backtest[0] == 80.25
    assert (
        backtest[1].iat[0, 5] == -1
        and backtest[1].iat[0, 8] == 2700
        and backtest[1].iat[0, 9] == 0.49
    )
    assert (
        backtest[1].iat[1, 5] == 1
        and backtest[1].iat[1, 8] == 2720
        and backtest[1].iat[1, 9] == 0.31
    )
    assert (
        backtest[1].iat[2, 5] == -1
        and backtest[1].iat[2, 8] == 2825
        and backtest[1].iat[2, 9] == 0.51
    )
    assert (
        backtest[1].iat[3, 5] == 1
        and backtest[1].iat[3, 8] == 2865
        and backtest[1].iat[3, 9] == 0.30
    )


def test_long_put_spread_integration(hod_struct):
    data = get(TEST_FILE_PATH_FULL, hod_struct, prompt=False)

    filters = {"entry_dte": 31, "leg1_delta": 0.30, "leg2_delta": 0.50, "exit_dte": 7}

    start = datetime(2018, 1, 1)
    end = datetime(2018, 2, 28)

    trades = long_put_spread(data, start, end, filters)
    backtest = run(data, trades, filters)
    print(backtest[1])
    assert backtest[0] == 256.50
    assert (
        backtest[1].iat[0, 5] == -1
        and backtest[1].iat[0, 8] == 2665
        and backtest[1].iat[0, 9] == -0.30
    )
    assert (
        backtest[1].iat[1, 5] == 1
        and backtest[1].iat[1, 8] == 2700
        and backtest[1].iat[1, 9] == -0.51
    )
    assert (
        backtest[1].iat[2, 5] == -1
        and backtest[1].iat[2, 8] == 2775
        and backtest[1].iat[2, 9] == -0.30
    )
    assert (
        backtest[1].iat[3, 5] == 1
        and backtest[1].iat[3, 8] == 2830
        and backtest[1].iat[3, 9] == -0.51
    )


def test_short_put_spread_integration(hod_struct):
    data = get(TEST_FILE_PATH_FULL, hod_struct, prompt=False)

    filters = {"entry_dte": 31, "leg1_delta": 0.30, "leg2_delta": 0.50, "exit_dte": 7}

    start = datetime(2018, 1, 1)
    end = datetime(2018, 2, 28)

    trades = short_put_spread(data, start, end, filters)
    backtest = run(data, trades, filters)
    print(backtest[1])
    assert backtest[0] == -256.5
    assert (
        backtest[1].iat[0, 5] == 1
        and backtest[1].iat[0, 8] == 2665
        and backtest[1].iat[0, 9] == -0.30
    )
    assert (
        backtest[1].iat[1, 5] == -1
        and backtest[1].iat[1, 8] == 2700
        and backtest[1].iat[1, 9] == -0.51
    )
    assert (
        backtest[1].iat[2, 5] == 1
        and backtest[1].iat[2, 8] == 2775
        and backtest[1].iat[2, 9] == -0.30
    )
    assert (
        backtest[1].iat[3, 5] == -1
        and backtest[1].iat[3, 8] == 2830
        and backtest[1].iat[3, 9] == -0.51
    )
