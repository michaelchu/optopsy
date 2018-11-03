from optopsy.enums import OrderAction
from optopsy.option_strategies import long_call, short_call, long_put, short_put
from .support.data_fixtures import *

pd.set_option('display.expand_frame_repr', False)


@pytest.mark.usefixtures("options_data")
def test_long_call(options_data):
    actual_spread = long_call(options_data, 0.5, 18)
    action = actual_spread[0]
    results = actual_spread[1]
    assert action == OrderAction.BTO
    assert all(results['option_type'] == 'c')
    assert all(v in [0.55, 0.51] for v in results['delta'].unique().tolist())


@pytest.mark.usefixtures("options_data")
def test_short_call(options_data):
    actual_spread = short_call(options_data, 0.5, 18)
    action = actual_spread[0]
    results = actual_spread[1]
    assert action == OrderAction.STO
    assert all(results['option_type'] == 'c')
    assert all(v in [0.55, 0.51] for v in results['delta'].unique().tolist())


@pytest.mark.usefixtures("options_data")
def test_long_put(options_data):
    actual_spread = long_put(options_data, 0.5, 17)
    action = actual_spread[0]
    results = actual_spread[1]
    assert action == OrderAction.BTO
    assert all(results['option_type'] == 'p')
    assert -0.49 == results.iat[0, 14]


@pytest.mark.usefixtures("options_data")
def test_short_put(options_data):
    actual_spread = short_put(options_data, 0.5, 17)
    action = actual_spread[0]
    results = actual_spread[1]
    assert action == OrderAction.STO
    assert all(results['option_type'] == 'p')
    assert -0.49 == results.iat[0, 14]
