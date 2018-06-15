from datetime import date

import pandas.util.testing as pt

from .base import *

pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)

data = data_factory('test_dod_a_daily.csv',
                    dod_struct,
                    date(2016, 1, 1),
                    date(2016, 1, 5)
                    )

data_greeks = data_factory('test_dod_a_daily.csv',
                           dod_struct_with_opt_sym_greeks,
                           date(2016, 1, 1),
                           date(2016, 1, 5)
                           )

col = ['symbol', 'expiration', 'quote_date', 'bid', 'ask', 'mark']
col_greeks = ['symbol', 'expiration', 'quote_date', 'bid', 'ask', 'delta', 'gamma', 'theta',
              'vega', 'mark']


def test_single_call():
    actual_spread = op.option_strategy.Single(option_type=op.OptionType.CALL)(data).head()
    expected_spread = format_test_data(pd.DataFrame(test_data_call, columns=col))
    pt.assert_frame_equal(actual_spread, expected_spread)


def test_single_put():
    actual_spread = op.option_strategy.Single(option_type=op.OptionType.PUT)(data).head()
    expected_spread = format_test_data(pd.DataFrame(test_data_put, columns=col))
    pt.assert_frame_equal(actual_spread, expected_spread)


def test_single_with_symbol():
    actual_spread = op.option_strategy.Single(option_type=op.OptionType.PUT)(data).head()
    expected_spread = format_test_data(pd.DataFrame(test_data_put, columns=col))
    pt.assert_frame_equal(actual_spread, expected_spread)


def test_single_with_greeks():
    actual_spread = op.option_strategy.Single(option_type=op.OptionType.PUT)(data_greeks).head()
    expected_spread = format_test_data(pd.DataFrame(test_data_put_greek, columns=col_greeks))
    pt.assert_frame_equal(actual_spread, expected_spread)
