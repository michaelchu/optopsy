import pandas.util.testing as pt
import pytest

import optopsy as op
from .base import *

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.width', None)


def test_vertical_call(data_hod):
    test_data = {
        'symbol': ['.VXX161202C00020000-.VXX161202C00022000',
                   '.VXX161202C00020500-.VXX161202C00022500',
                   '.VXX161202C00021000-.VXX161202C00023000',
                   '.VXX161202C00021500-.VXX161202C00023500',
                   '.VXX161202C00022000-.VXX161202C00024000'],
        'expiration': ['2016-12-02', '2016-12-02', '2016-12-02', '2016-12-02', '2016-12-02'],
        'quote_date': ['2016-12-01', '2016-12-01', '2016-12-01', '2016-12-01', '2016-12-01'],
        'bid': [1.8, 1.8, 1.8, 1.8, 1.8],
        'ask': [2.2, 2.2, 2.2, 2.2, 2.2],
        'mark': [2.0, 2.0, 2.0, 2.0, 2.0]
    }

    col = ['symbol', 'expiration', 'quote_date', 'bid', 'ask', 'mark']

    actual_spread = op.option_strategy.Vertical(option_type=op.OptionType.CALL, width=2)(
        data_hod).head()
    expected_spread = format_test_data(pd.DataFrame(test_data, columns=col))
    pt.assert_frame_equal(actual_spread, expected_spread)


def test_vertical_put(data_hod):
    test_data = {
        'symbol': ['.VXX161202P00056500-.VXX161202P00054500',
                   '.VXX161202P00057000-.VXX161202P00055000',
                   '.VXX161202P00057500-.VXX161202P00055500',
                   '.VXX161202P00058000-.VXX161202P00056000',
                   '.VXX161202P00060000-.VXX161202P00058000'],
        'expiration': ['2016-12-02', '2016-12-02', '2016-12-02', '2016-12-02', '2016-12-02'],
        'quote_date': ['2016-12-01', '2016-12-01', '2016-12-01', '2016-12-01', '2016-12-01'],
        'bid': [1.80, 1.80, 1.75, 1.75, 1.75],
        'ask': [2.25, 2.25, 2.25, 2.25, 2.20],
        'mark': [2.03, 2.03, 2.0, 2.0, 1.97]
    }

    col = ['symbol', 'expiration', 'quote_date', 'bid', 'ask', 'mark']

    actual_spread = op.option_strategy.Vertical(option_type=op.OptionType.PUT, width=2)(
        data_hod).tail()
    expected_spread = format_test_data(pd.DataFrame(test_data, columns=col))
    pt.assert_frame_equal(actual_spread, expected_spread)


@pytest.mark.parametrize("width", [0, -1])
def test_invalid_width(data_hod, width):
    with pytest.raises(ValueError):
        op.option_strategy.Vertical(option_type=op.OptionType.CALL, width=width)(data_hod)


def test_single_with_symbol(data_hod_sym):
    test_data = {
        'symbol': ['.VXX161202P00056500-.VXX161202P00054500',
                   '.VXX161202P00057000-.VXX161202P00055000',
                   '.VXX161202P00057500-.VXX161202P00055500',
                   '.VXX161202P00058000-.VXX161202P00056000',
                   '.VXX161202P00060000-.VXX161202P00058000'],
        'expiration': ['2016-12-02', '2016-12-02', '2016-12-02', '2016-12-02', '2016-12-02'],
        'quote_date': ['2016-12-01', '2016-12-01', '2016-12-01', '2016-12-01', '2016-12-01'],
        'bid': [1.8, 1.8, 1.75, 1.75, 1.75],
        'ask': [2.25, 2.25, 2.25, 2.25, 2.20],
        'mark': [2.03, 2.03, 2.00, 2.00, 1.97]
    }

    col = ['symbol', 'expiration', 'quote_date', 'bid', 'ask', 'mark']

    actual_spread = op.option_strategy.Vertical(option_type=op.OptionType.PUT, width=2)(
        data_hod_sym).tail()
    expected_spread = format_test_data(pd.DataFrame(test_data, columns=col))
    pt.assert_frame_equal(actual_spread, expected_spread)
