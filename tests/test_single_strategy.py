import pandas as pd
from datetime import datetime
from optopsy.enums import OrderAction
from optopsy.option_strategies import long_call, short_call, long_put, short_put

pd.set_option('display.expand_frame_repr', False)

start = datetime(1990, 1, 20)
end = datetime(1990, 1, 20)


def test_long_call(options_data):
    actual_spread = long_call(
        options_data,
        start,
        end,
        {
            'leg1_delta': (0.45, 0.50, 0.55),
            'entry_dte': (18, 18, 18)
        }
    )
    results = actual_spread
    assert all(results['option_type'] == 'c')
    assert all(v in [0.55, 0.51] for v in results['delta'].unique().tolist())
    assert results.shape == (1, 15)


def test_short_call(options_data):
    actual_spread = short_call(
        options_data,
        start,
        end,
        {
            'leg1_delta': (0.45, 0.50, 0.55),
            'entry_dte': (18, 18, 18)
        }
    )
    results = actual_spread
    assert all(results['option_type'] == 'c')
    assert all(v in [0.55, 0.51] for v in results['delta'].unique().tolist())


def test_long_put(options_data):
    actual_spread = long_put(
        options_data,
        start,
        end,
        {
            'leg1_delta': (0.45, 0.50, 0.55),
            'entry_dte': (17, 17, 17)
        }
    )
    results = actual_spread
    assert all(results['option_type'] == 'p')
    assert all(v in [-0.49] for v in results['delta'].unique().tolist())


def test_short_put(options_data):
    actual_spread = short_put(
        options_data,
        start,
        end,
        {
            'leg1_delta': (0.45, 0.50, 0.55),
            'entry_dte': (17, 17, 17)
        }
    )
    results = actual_spread
    assert all(results['option_type'] == 'p')
    assert all(v in [-0.49] for v in results['delta'].unique().tolist())
