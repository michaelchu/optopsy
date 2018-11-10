from optopsy.backtest import simulate
from tests.support.data_fixtures import options_data_full
from optopsy.option_strategies import long_call_spread
from optopsy.enums import Period
import pandas as pd

pd.set_option('display.expand_frame_repr', False)


def test_vertical_integration(options_data_full):
    filters = {
        'entry_dte': (29, 30, 31),
        'leg1_delta': 0.30,
        'leg2_delta': 0.50
    }

    trades = long_call_spread(options_data_full, filters)
    print("")
    print(trades[1])