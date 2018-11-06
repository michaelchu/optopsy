from optopsy.option_strategies import *
from .support.data_fixtures import *
pd.set_option('display.expand_frame_repr', False)


@pytest.mark.usefixtures("options_data")
def test_long_call_spread(options_data):
    actual_spread = long_call_spread(
        options_data,
        long_delta=0.3,
        short_delta=0.5,
        dte=18
    )
    result = actual_spread[1]
    assert actual_spread[0] == OrderAction.BTO
    assert all(result['option_type'] == 'c')
    assert all(v in [0.35, 0.55] for v in result['delta'].unique().tolist())
    assert result.shape == (2, 14)


@pytest.mark.usefixtures("options_data")
def test_short_call_spread(options_data):
    actual_spread = short_call_spread(
        options_data,
        long_delta=0.5,
        short_delta=0.3,
        dte=18
    )
    result = actual_spread[1]
    assert actual_spread[0] == OrderAction.STO
    assert all(result['option_type'] == 'c')
    assert all(v in [0.35, 0.55] for v in result['delta'].unique().tolist())
    assert result.shape == (2, 14)


@pytest.mark.usefixtures("options_data")
def test_long_put_spread(options_data):
    actual_spread = long_put_spread(
        options_data,
        long_delta=0.5,
        short_delta=0.3,
        dte=18
    )
    result = actual_spread[1]
    assert actual_spread[0] == OrderAction.BTO
    assert all(result['option_type'] == 'p')
    assert all(v in [-0.31, -0.46] for v in result['delta'].unique().tolist())
    assert result.shape == (2, 14)


@pytest.mark.usefixtures("options_data")
def test_short_put_spread(options_data):
    actual_spread = short_put_spread(
        options_data,
        long_delta=0.3,
        short_delta=0.5,
        dte=18
    )
    result = actual_spread[1]
    assert actual_spread[0] == OrderAction.STO
    assert all(result['option_type'] == 'p')
    assert all(v in [-0.31, -0.46] for v in result['delta'].unique().tolist())
    assert result.shape == (2, 14)
