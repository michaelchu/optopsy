import pandas.util.testing as pt

import optopsy as op
from .base import *

pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)


col = ['symbol', 'expiration', 'quote_date', 'bid', 'ask', 'mark']
col_greeks = ['symbol', 'expiration', 'quote_date', 'bid', 'ask', 'delta', 'gamma', 'theta',
              'vega', 'mark']


def test_single_call(data_dod):
    actual_spread = op.option_strategy.Single(option_type=op.OptionType.CALL)(data_dod).head()
    expected_spread = format_test_data(pd.DataFrame(test_data_call, columns=col))
    pt.assert_frame_equal(actual_spread, expected_spread)


def test_single_put(data_dod):
    actual_spread = op.option_strategy.Single(option_type=op.OptionType.PUT)(data_dod).head()
    expected_spread = format_test_data(pd.DataFrame(test_data_put, columns=col))
    pt.assert_frame_equal(actual_spread, expected_spread)


def test_single_with_symbol(data_dod):
    actual_spread = op.option_strategy.Single(option_type=op.OptionType.PUT)(data_dod).head()
    expected_spread = format_test_data(pd.DataFrame(test_data_put, columns=col))
    pt.assert_frame_equal(actual_spread, expected_spread)


def test_single_with_greeks(data_dod_greeks):
    actual_spread = op.option_strategy.Single(option_type=op.OptionType.PUT)(data_dod_greeks).head()
    expected_spread = format_test_data(pd.DataFrame(test_data_put_greek, columns=col_greeks))
    pt.assert_frame_equal(actual_spread, expected_spread)
