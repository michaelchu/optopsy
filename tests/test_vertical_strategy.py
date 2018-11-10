import pandas as pd
import pytest

from .support.data_fixtures import options_data
from optopsy.enums import OrderAction
from optopsy.option_strategies import long_call_spread, short_call_spread, long_put_spread, \
    short_put_spread

pd.set_option('display.expand_frame_repr', False)


params = {
    'leg1_delta': (0.25, 0.30, 0.45),
    'leg2_delta': (0.45, 0.50, 0.55),
    'entry_dte': (18, 18, 18)
}


def _test_call_results(result):
    assert all(result['option_type'] == 'c')
    assert all(v in [0.35, 0.55] for v in result['delta'].unique().tolist())
    assert result.shape == (2, 15)


def _test_put_results(result):
    assert all(result['option_type'] == 'p')
    assert all(v in [-0.31, -0.46] for v in result['delta'].unique().tolist())
    assert result.shape == (2, 15)


@pytest.mark.usefixtures("options_data")
def test_long_call_spread(options_data):
    actual_spread = long_call_spread(options_data, params)
    _test_call_results(actual_spread[1])
    assert actual_spread[0] == OrderAction.BTO


@pytest.mark.usefixtures("options_data")
def test_short_call_spread(options_data):
    actual_spread = short_call_spread(options_data, params)
    _test_call_results(actual_spread[1])
    assert actual_spread[0] == OrderAction.STO


@pytest.mark.usefixtures("options_data")
def test_long_put_spread(options_data):
    actual_spread = long_put_spread(options_data, params)
    _test_put_results(actual_spread[1])
    assert actual_spread[0] == OrderAction.BTO


@pytest.mark.usefixtures("options_data")
def test_short_put_spread(options_data):
    actual_spread = short_put_spread(options_data, params)
    _test_put_results(actual_spread[1])
    assert actual_spread[0] == OrderAction.STO
