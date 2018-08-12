import pandas as pd
import pandas.util.testing as pt
import pytest

from optopsy.option_strategy import long_call, short_call, long_put, short_put
from tests.data_fixtures import one_day_data
from tests.filter_fixtures import test_single_filters
from optopsy.enums import OrderAction

pd.set_option('display.expand_frame_repr', False)


@pytest.fixture
def expected_single_calls():
    return (
        pd.DataFrame({
            'leg_1_symbol': ['.A160115C00020000', '.A160115C00021000'],
            'leg_1_expiration': ['2016-01-15', '2016-01-15'],
            'leg_1_quote_date': ['2016-01-05', '2016-01-05'],
            'leg_1_underlying_price': [40.55, 40.55],
            'leg_1_strike': [20, 21],
            'leg_1_bid': [20.3, 20.3],
            'leg_1_ask': [21.35, 21.35],
            'leg_1_delta': [0.02, 0.02],
            'leg_1_gamma': [0.00, 0.00],
            'leg_1_theta': [-0.05, -0.05],
            'leg_1_vega': [0.00, 0.00],
            'leg_1_dte': [10, 10]
        }
        ).assign(
            leg_1_expiration=lambda r: pd.to_datetime(
                r['leg_1_expiration'],
                infer_datetime_format=True,
                format='%Y-%m-%d'),
            leg_1_quote_date=lambda r: pd.to_datetime(
                r['leg_1_quote_date'],
                infer_datetime_format=True,
                format='%Y-%m-%d')
        )
    )


@pytest.fixture
def expected_single_puts():
    return (
        pd.DataFrame({
            'leg_1_symbol': ['.A160115P00020000', '.A160115P00021000'],
            'leg_1_expiration': ['2016-01-15', '2016-01-15'],
            'leg_1_quote_date': ['2016-01-05', '2016-01-05'],
            'leg_1_underlying_price': [40.55, 40.55],
            'leg_1_strike': [20, 21],
            'leg_1_bid': [0.0, 0.0],
            'leg_1_ask': [0.35, 0.35],
            'leg_1_delta': [-0.02, -0.03],
            'leg_1_gamma': [0.00, 0.01],
            'leg_1_theta': [-0.05, -0.03],
            'leg_1_vega': [0.00, 0.00],
            'leg_1_dte': [10, 10]
        }).assign(
            leg_1_expiration=lambda r: pd.to_datetime(
                r['leg_1_expiration'],
                infer_datetime_format=True,
                format='%Y-%m-%d'),
            leg_1_quote_date=lambda r: pd.to_datetime(
                r['leg_1_quote_date'],
                infer_datetime_format=True,
                format='%Y-%m-%d')
        )
    )


def test_long_call(one_day_data, test_single_filters, expected_single_calls):
    actual_spread = long_call(one_day_data, **test_single_filters)
    assert actual_spread[0] == OrderAction.BTO
    assert isinstance(actual_spread[1], list)
    assert len(actual_spread[1]) == 1
    pt.assert_frame_equal(actual_spread[1][0], expected_single_calls)


def test_short_call(one_day_data, test_single_filters, expected_single_calls):
    actual_spread = short_call(one_day_data, **test_single_filters)
    assert actual_spread[0] == OrderAction.STO
    assert isinstance(actual_spread[1], list)
    assert len(actual_spread[1]) == 1
    pt.assert_frame_equal(actual_spread[1][0], expected_single_calls)


def test_long_put(one_day_data, test_single_filters, expected_single_puts):
    actual_spread = long_put(one_day_data, **test_single_filters)
    assert actual_spread[0] == OrderAction.BTO
    assert isinstance(actual_spread[1], list)
    assert len(actual_spread[1]) == 1
    pt.assert_frame_equal(actual_spread[1][0], expected_single_puts)


def test_short_put(one_day_data, test_single_filters, expected_single_puts):
    actual_spread = short_put(one_day_data, **test_single_filters)
    assert actual_spread[0] == OrderAction.STO
    assert isinstance(actual_spread[1], list)
    assert len(actual_spread[1]) == 1
    pt.assert_frame_equal(actual_spread[1][0], expected_single_puts)
