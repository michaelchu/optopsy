import pandas as pd
import pandas.util.testing as pt
import pytest

from .data_fixtures import one_day_data
from optopsy.enums import OptionType
from optopsy.option_strategy import OptionStrategy

pd.set_option('display.expand_frame_repr', False)


@pytest.fixture
def expected_single_calls():
    return (
            pd.DataFrame([
            {
                'symbol': '.A160115C00020000',
                'expiration': '2016-01-15',
                'quote_date': '2016-01-05',
                'strike_1': 20,
                'bid': 20.3,
                'ask': 21.35,
                'mark': 20.825,
                'delta': 0.02,
                'gamma': 0.00,
                'theta': -0.05,
                'vega': 0.00,
                'dte': 10
            },
            {
                'symbol': '.A160115C00021000',
                'expiration': '2016-01-15',
                'quote_date': '2016-01-05',
                'strike_1': 21,
                'bid': 20.3,
                'ask': 21.35,
                'mark': 20.825,
                'delta': 0.02,
                'gamma': 0.00,
                'theta': -0.05,
                'vega': 0.00,
                'dte': 10
            }
            ])
            .assign(
                expiration=lambda r: pd.to_datetime(r['expiration'], infer_datetime_format=True,
                                                    format='%Y-%m-%d'),
                quote_date=lambda r: pd.to_datetime(r['quote_date'], infer_datetime_format=True,
                                                    format='%Y-%m-%d')
            )
            .set_index('quote_date', inplace=False, drop=False)
    )


@pytest.fixture
def expected_single_puts():
    return (
        pd.DataFrame([
            {
                'symbol': '.A160115P00020000',
                'expiration': '2016-01-15',
                'quote_date': '2016-01-05',
                'strike_1': 20,
                'bid': 0.0,
                'ask': 0.35,
                'mark': 0.175,
                'delta': -0.02,
                'gamma': 0.00,
                'theta': -0.05,
                'vega': 0.00,
                'dte': 10
            },
            {
                'symbol': '.A160115P00021000',
                'expiration': '2016-01-15',
                'quote_date': '2016-01-05',
                'strike_1': 21,
                'bid': 0.0,
                'ask': 0.35,
                'mark': 0.175,
                'delta': -0.03,
                'gamma': 0.01,
                'theta': -0.03,
                'vega': 0.00,
                'dte': 10
            }
        ])
        .assign(
            expiration=lambda r: pd.to_datetime(r['expiration'], infer_datetime_format=True,
                                                format='%Y-%m-%d'),
            quote_date=lambda r: pd.to_datetime(r['quote_date'], infer_datetime_format=True,
                                                format='%Y-%m-%d')
        )
        .set_index('quote_date', inplace=False, drop=False)
    )


def test_single_call(one_day_data, expected_single_calls):
    actual_spread = OptionStrategy.single(one_day_data, OptionType.CALL)
    pt.assert_frame_equal(actual_spread, expected_single_calls)


def test_single_put(one_day_data, expected_single_puts):
    actual_spread = OptionStrategy.single(one_day_data, OptionType.PUT)
    pt.assert_frame_equal(actual_spread, expected_single_puts)
