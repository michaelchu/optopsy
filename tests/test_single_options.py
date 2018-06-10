import os
from datetime import date

import pandas as pd
import pandas.util.testing as pt

import optopsy as op
from .base import *

pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)


def test_single_call():
    data = op.get(os.path.join(os.path.dirname(__file__), 'test_data', 'test_dod_a_daily.csv'),
                  start=date(2016, 1, 1),
                  end=date(2016, 1, 5),
                  struct=dod_struct,
                  prompt=False
                  )

    test_data = {
        'symbol': ['.A160115C00020000', '.A160115C00022500', '.A160115C00025000',
                   '.A160115C00027500',
                   '.A160115C00030000'],
        'expiration': ['2016-01-15', '2016-01-15', '2016-01-15', '2016-01-15', '2016-01-15'],
        'quote_date': ['2016-01-05', '2016-01-05', '2016-01-05', '2016-01-05', '2016-01-05'],
        'bid': [20.3, 17.8, 15.3, 12.8, 10.3],
        'ask': [21.35, 18.60, 16.10, 13.60, 11.10],
        'mark': [20.825, 18.2, 15.7, 13.2, 10.7]
    }

    col = ['symbol', 'expiration', 'quote_date', 'bid', 'ask', 'mark']

    actual_spread = op.options.Single(option_type=op.OptionType.CALL)(data).head()
    expected_spread = pd.DataFrame(test_data, columns=col)
    expected_spread['expiration'] = pd.to_datetime(expected_spread['expiration'])
    expected_spread['quote_date'] = pd.to_datetime(expected_spread['quote_date'])

    pt.assert_frame_equal(actual_spread, expected_spread)


def test_single_put():
    data = op.get(os.path.join(os.path.dirname(__file__), 'test_data', 'test_dod_a_daily.csv'),
                  start=date(2016, 1, 1),
                  end=date(2016, 1, 5),
                  struct=dod_struct,
                  prompt=False
                  )

    test_data = {
        'symbol': ['.A160115P00020000', '.A160115P00022500', '.A160115P00025000',
                   '.A160115P00027500',
                   '.A160115P00030000'],
        'expiration': ['2016-01-15', '2016-01-15', '2016-01-15', '2016-01-15', '2016-01-15'],
        'quote_date': ['2016-01-05', '2016-01-05', '2016-01-05', '2016-01-05', '2016-01-05'],
        'bid': [0.0, 0.0, 0.0, 0.0, 0.0],
        'ask': [0.35, 0.35, 0.1, 0.35, 0.35],
        'mark': [0.175, 0.175, 0.05, 0.175, 0.175]
    }

    col = ['symbol', 'expiration', 'quote_date', 'bid', 'ask', 'mark']

    actual_spread = op.options.Single(option_type=op.OptionType.PUT)(data).head()

    expected_spread = pd.DataFrame(test_data, columns=col)
    expected_spread['expiration'] = pd.to_datetime(expected_spread['expiration'])
    expected_spread['quote_date'] = pd.to_datetime(expected_spread['quote_date'])

    pt.assert_frame_equal(actual_spread, expected_spread)


def test_single_with_symbol():
    data = op.get(os.path.join(os.path.dirname(__file__), 'test_data', 'test_dod_a_daily.csv'),
                  start=date(2016, 1, 1),
                  end=date(2016, 1, 5),
                  struct=dod_struct_with_opt_sym,
                  prompt=False
                  )

    test_data = {
        'symbol': ['.A160115P00020000', '.A160115P00022500', '.A160115P00025000',
                   '.A160115P00027500',
                   '.A160115P00030000'],
        'expiration': ['2016-01-15', '2016-01-15', '2016-01-15', '2016-01-15', '2016-01-15'],
        'quote_date': ['2016-01-05', '2016-01-05', '2016-01-05', '2016-01-05', '2016-01-05'],
        'bid': [0.0, 0.0, 0.0, 0.0, 0.0],
        'ask': [0.35, 0.35, 0.1, 0.35, 0.35],
        'mark': [0.175, 0.175, 0.05, 0.175, 0.175]
    }

    col = ['symbol', 'expiration', 'quote_date', 'bid', 'ask', 'mark']

    actual_spread = op.options.Single(option_type=op.OptionType.PUT)(data).head()

    expected_spread = pd.DataFrame(test_data, columns=col)
    expected_spread['expiration'] = pd.to_datetime(expected_spread['expiration'])
    expected_spread['quote_date'] = pd.to_datetime(expected_spread['quote_date'])

    pt.assert_frame_equal(actual_spread, expected_spread)


def test_single_with_greeks():
    data = op.get(os.path.join(os.path.dirname(__file__), 'test_data', 'test_dod_a_daily.csv'),
                  start=date(2016, 1, 1),
                  end=date(2016, 1, 5),
                  struct=dod_struct_with_opt_sym_greeks,
                  prompt=False
                  )

    test_data = {
        'symbol': ['.A160115P00020000', '.A160115P00022500', '.A160115P00025000',
                   '.A160115P00027500',
                   '.A160115P00030000'],
        'expiration': ['2016-01-15', '2016-01-15', '2016-01-15', '2016-01-15', '2016-01-15'],
        'quote_date': ['2016-01-05', '2016-01-05', '2016-01-05', '2016-01-05', '2016-01-05'],
        'bid': [0.0, 0.0, 0.0, 0.0, 0.0],
        'ask': [0.35, 0.35, 0.1, 0.35, 0.35],
        'delta': [-0.02, -0.02, -0.02, -0.03, -0.04],
        'gamma': [0.00, 0.00, 0.01, 0.01, 0.01],
        'theta': [-0.05, -0.04, -0.03, -0.03, -0.03],
        'vega': [0.00, 0.00, 0.00, 0.00, 0.01],
        'mark': [0.175, 0.175, 0.05, 0.175, 0.175]
    }

    col = ['symbol', 'expiration', 'quote_date', 'bid', 'ask', 'delta', 'gamma', 'theta',
           'vega', 'mark']

    actual_spread = op.options.Single(option_type=op.OptionType.PUT)(data).head()

    expected_spread = pd.DataFrame(test_data, columns=col)
    expected_spread['expiration'] = pd.to_datetime(expected_spread['expiration'])
    expected_spread['quote_date'] = pd.to_datetime(expected_spread['quote_date'])

    pt.assert_frame_equal(actual_spread, expected_spread)
