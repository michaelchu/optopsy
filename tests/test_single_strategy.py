import pandas as pd
import pandas.util.testing as pt
import pytest
from optopsy.data import format_option_df
from optopsy.option_strategies import long_call, short_call, long_put, short_put
from optopsy.enums import OrderAction
from .data_fixtures import one_day_data
from .filter_fixtures import single_filters
from optopsy.option_spreads import leg_cols, common_cols

pd.set_option('display.expand_frame_repr', False)


@pytest.fixture
def expected_single_calls():
    data = {
        'option_symbol': 'A160115C00001000',
        'expiration': '2016-01-15',
        'quote_date': '2016-01-05',
        'underlying_price': 1.00,
        'option_type': 'c',
        'strike': 1.00,
        'bid': 0.017,
        'ask': 0.018,
        'delta': 0.519,
        'gamma': 9.63,
        'theta': -0.001,
        'vega': 0.001,
        'dte': 10
    }
    return format_option_df(pd.DataFrame([data], columns=data.keys()))


@pytest.fixture
def expected_single_puts():
    data = {
        'option_symbol': 'A160115P00001000',
        'expiration': '2016-01-15',
        'quote_date': '2016-01-05',
        'underlying_price': 1.00,
        'option_type': 'p',
        'strike': 1.00,
        'bid': 0.016,
        'ask': 0.017,
        'delta': -0.481,
        'gamma': 9.63,
        'theta': -0.001,
        'vega': 0.001,
        'dte': 10
    }
    return format_option_df(pd.DataFrame([data], columns=data.keys()))


@pytest.mark.usefixtures("one_day_data")
@pytest.mark.usefixtures("single_filters")
def test_long_call(one_day_data, single_filters, expected_single_calls):
    actual_spread = long_call(one_day_data, single_filters)
    assert actual_spread[0] == OrderAction.BTO
    assert isinstance(actual_spread[1], pd.DataFrame)
    pt.assert_frame_equal(actual_spread[1], expected_single_calls)


@pytest.mark.usefixtures("one_day_data")
@pytest.mark.usefixtures("single_filters")
def test_short_call(one_day_data, single_filters, expected_single_calls):
    actual_spread = short_call(one_day_data, single_filters)
    assert actual_spread[0] == OrderAction.STO
    assert isinstance(actual_spread[1], pd.DataFrame)
    pt.assert_frame_equal(actual_spread[1], expected_single_calls)


# @pytest.mark.usefixtures("one_day_data")
# @pytest.mark.usefixtures("single_filters")
# def test_long_put(one_day_data, single_filters, expected_single_puts):
#     actual_spread = long_put(one_day_data, single_filters)
#     assert actual_spread[0] == OrderAction.BTO
#     assert isinstance(actual_spread[1], pd.DataFrame)
#     pt.assert_frame_equal(actual_spread[1], expected_single_puts)
#
#
# @pytest.mark.usefixtures("one_day_data")
# @pytest.mark.usefixtures("single_filters")
# def test_short_put(one_day_data, single_filters, expected_single_puts):
#     actual_spread = short_put(one_day_data, single_filters)
#     assert actual_spread[0] == OrderAction.STO
#     assert isinstance(actual_spread[1], pd.DataFrame)
#     pt.assert_frame_equal(actual_spread[1], expected_single_puts)
