from optopsy.enums import OrderAction
from optopsy.option_strategies import long_call, short_call, long_put, short_put
from .support.data_fixtures import *

pd.set_option('display.expand_frame_repr', False)


@pytest.mark.usefixtures("options_data")
def test_long_call(options_data):
    actual_spread = long_call(options_data)
    assert actual_spread[0] == OrderAction.BTO
    assert isinstance(actual_spread[1], pd.DataFrame)
    assert not actual_spread[1].empty
    assert all(actual_spread[1]['option_type'] == 'c')


@pytest.mark.usefixtures("options_data")
def test_short_call(options_data):
    actual_spread = short_call(options_data)
    assert actual_spread[0] == OrderAction.STO
    assert isinstance(actual_spread[1], pd.DataFrame)
    assert not actual_spread[1].empty
    assert all(actual_spread[1]['option_type'] == 'c')


@pytest.mark.usefixtures("options_data")
def test_long_put(options_data):
    actual_spread = long_put(options_data)
    assert actual_spread[0] == OrderAction.BTO
    assert isinstance(actual_spread[1], pd.DataFrame)
    assert not actual_spread[1].empty
    assert all(actual_spread[1]['option_type'] == 'p')


@pytest.mark.usefixtures("options_data")
def test_short_put(options_data):
    actual_spread = short_put(options_data)
    assert actual_spread[0] == OrderAction.STO
    assert isinstance(actual_spread[1], pd.DataFrame)
    assert not actual_spread[1].empty
    assert all(actual_spread[1]['option_type'] == 'p')
