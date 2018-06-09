import os
from datetime import date

import pandas as pd
import pandas.util.testing as pt

import optopsy as op

dod_struct = (
    ('symbol', 0),
    ('option_type', 4),
    ('expiration', 5),
    ('quote_date', 6),
    ('strike', 7),
    ('bid', 9),
    ('ask', 10)
)


def test_single_call():
    data = op.get(os.path.join(os.path.dirname(__file__), 'test_data', 'test_dod_a_daily.csv'),
                  start=date(2016, 1, 1),
                  end=date(2016, 12, 31),
                  struct=dod_struct,
                  prompt=False
                  )

    test_data = {
        'symbol': ['A', 'A', 'A', 'A', 'A'],
        'option_type': ['c', 'c', 'c', 'c', 'c'],
        'expiration': ['2016-01-15', '2016-01-15', '2016-01-15', '2016-01-15', '2016-01-15'],
        'quote_date': ['2016-01-05', '2016-01-05', '2016-01-05', '2016-01-05', '2016-01-05'],
        'strike': [20.0, 22.5, 25.0, 27.5, 30.0],
        'bid': [20.3, 17.8, 15.3, 12.8, 10.3],
        'ask': [21.35, 18.60, 16.10, 13.60, 11.10]
    }

    actual_spread = op.options.Single(option_type=op.OptionType.CALL)(data).head()

    expected_spread = pd.DataFrame(test_data)
    expected_spread['expiration'] = pd.to_datetime(expected_spread['expiration'])
    expected_spread['quote_date'] = pd.to_datetime(expected_spread['quote_date'])

    pt.assert_frame_equal(actual_spread, expected_spread)


def test_single_put():
    data = op.get(os.path.join(os.path.dirname(__file__), 'test_data', 'test_dod_a_daily.csv'),
                  start=date(2016, 1, 1),
                  end=date(2016, 12, 31),
                  struct=dod_struct,
                  prompt=False
                  )

    test_data = {
        'symbol': ['A', 'A', 'A', 'A', 'A'],
        'option_type': ['p', 'p', 'p', 'p', 'p'],
        'expiration': ['2016-01-15', '2016-01-15', '2016-01-15', '2016-01-15', '2016-01-15'],
        'quote_date': ['2016-01-05', '2016-01-05', '2016-01-05', '2016-01-05', '2016-01-05'],
        'strike': [20.0, 22.5, 25.0, 27.5, 30.0],
        'bid': [0.0, 0.0, 0.0, 0.0, 0.0],
        'ask': [0.35, 0.35, 0.1, 0.35, 0.35],

    }

    actual_spread = op.options.Single(option_type=op.OptionType.PUT)(data).head()

    expected_spread = pd.DataFrame(test_data)
    expected_spread['expiration'] = pd.to_datetime(expected_spread['expiration'])
    expected_spread['quote_date'] = pd.to_datetime(expected_spread['quote_date'])

    pt.assert_frame_equal(actual_spread, expected_spread)
