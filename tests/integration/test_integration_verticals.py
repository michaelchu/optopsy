from optopsy.backtest import simulate
from optopsy.option_strategies import long_call_spread
from optopsy.data import get
from datetime import datetime
import os


CURRENT_FILE = os.path.abspath(os.path.dirname(__file__))
TEST_FILE_PATH_FULL = os.path.join(CURRENT_FILE,
                                   '../test_data/test_options_data_full.csv')


def test_vertical_integration(hod_struct):
    data = get(TEST_FILE_PATH_FULL, hod_struct, prompt=False)

    filters = {
        'entry_dte': (29, 30, 31),
        'leg1_delta': 0.30,
        'leg2_delta': 0.50
    }

    start = datetime(2018, 1, 1)
    end = datetime(2018, 1, 31)

    trades = long_call_spread(data, start, end, filters)
    backtest = simulate(data, trades, filters)
    print(trades)
    assert False
