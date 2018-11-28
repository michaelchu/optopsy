from optopsy.option_strategies import (
    long_call,
    short_call,
    long_put,
    short_put,
    long_call_spread,
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


def test_long_call_market_integration():
    filters = {
        "start_date": datetime(2018, 1, 1),
        "end_date": datetime(2018, 2, 28),
        "entry_dte": 31,
        "exit_dte": 7,
        "entry_spread_price": (13, 14, 15),
        "leg1_delta": 0.30,
    }

    backtest = long_call(DATA, filters)
    print(backtest)
    assert (
        backtest.iat[0, 5] == 1
        and backtest.iat[0, 9] == 0.3
        and backtest.iat[0, 7] == "c"
        and backtest.iat[0, 8] == 2865
        and backtest.iat[0, 12] == 14.5
    )


def test_long_call_spread_entry_spread_price_integration():
    filters = {
        "start_date": datetime(2018, 1, 1),
        "end_date": datetime(2018, 2, 28),
        "entry_dte": 31,
        "exit_dte": 7,
        "entry_spread_price": (13, 14, 15),
        "leg1_delta": 0.50,
        "leg2_delta": 0.20,
    }

    backtest = long_call_spread(DATA, filters, mode="midpoint")
    print(backtest)
    assert backtest.shape == (2, 17)
    assert (
        backtest.iat[0, 5] == 1
        and backtest.iat[0, 9] == 0.49
        and backtest.iat[0, 7] == "c"
        and backtest.iat[0, 8] == 2700
        and backtest.iat[0, 12] == 18.3
    )
    assert (
        backtest.iat[1, 5] == -1
        and backtest.iat[1, 9] == 0.19
        and backtest.iat[1, 7] == "c"
        and backtest.iat[1, 8] == 2735
        and backtest.iat[1, 12] == -4.35
    )
