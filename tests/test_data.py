import os
from datetime import date

import pandas as pd
import pandas.util.testing as pt
import pytest

import optopsy as op

fields = (
    ('symbol', True),
    ('quote_date', True),
    ('expiration', True),
    ('strike', True),
    ('option_type', True),
    ('bid', True),
    ('ask', True)
)

cboe_test_data = [
    {'symbol': '^SPX',
     'option_type': 'c',
     'root': 'SPXW',
     'expiration': '1/8/2016 0:00:00',
     'quote_date': '1/4/2016 0:00:00',
     'strike': 700.00,
     'bid': 1299.60,
     'ask': 1305.30
     },
    {'symbol': '^SPX',
     'option_type': 'p',
     'root': 'SPXW',
     'expiration': '1/8/2016 0:00:00',
     'quote_date': '1/4/2016 0:00:00',
     'strike': 700.00,
     'bid': 0.00,
     'ask': 0.05
     },
    {'symbol': '^SPX',
     'option_type': 'c',
     'root': 'SPXW',
     'expiration': '1/8/2016 0:00:00',
     'quote_date': '1/5/2016 0:00:00',
     'strike': 700.00,
     'bid': 1313.60,
     'ask': 1319.40
     },
    {'symbol': '^SPX',
     'option_type': 'p',
     'root': 'SPXW',
     'expiration': '1/8/2016 0:00:00',
     'quote_date': '1/5/2016 0:00:00',
     'strike': 700.00,
     'bid': 0.00,
     'ask': 0.05
     },
    {'symbol': '^SPX',
     'option_type': 'c',
     'root': 'SPXW',
     'expiration': '1/8/2016 0:00:00',
     'quote_date': '1/6/2016 0:00:00',
     'strike': 700.00,
     'bid': 1299.60,
     'ask': 1305.30
     },
    {'symbol': '^SPX',
     'option_type': 'p',
     'root': 'SPXW',
     'expiration': '1/8/2016 0:00:00',
     'quote_date': '1/6/2016 0:00:00',
     'strike': 700.00,
     'bid': 0.00,
     'ask': 0.05
     }
]

dod_test_data = [
    {'symbol': 'A',
     'option_type': 'c',
     'expiration': '2016-01-15',
     'quote_date': '2016-01-05',
     'strike': 20,
     'bid': 20.3,
     'ask': 21.35
     },
    {'symbol': 'A',
     'option_type': 'p',
     'expiration': '2016-01-15',
     'quote_date': '2016-01-05',
     'strike': 20,
     'bid': 0.0,
     'ask': 0.35
     },
    {'symbol': 'A',
     'option_type': 'c',
     'expiration': '2016-01-15',
     'quote_date': '2016-01-06',
     'strike': 20,
     'bid': 20.3,
     'ask': 21.35
     },
    {'symbol': 'A',
     'option_type': 'p',
     'expiration': '2016-01-15',
     'quote_date': '2016-01-06',
     'strike': 20,
     'bid': 0.0,
     'ask': 0.35
     },
    {'symbol': 'A',
     'option_type': 'c',
     'expiration': '2016-01-15',
     'quote_date': '2016-01-07',
     'strike': 20,
     'bid': 20.3,
     'ask': 21.35
     },
    {'symbol': 'A',
     'option_type': 'p',
     'expiration': '2016-01-15',
     'quote_date': '2016-01-07',
     'strike': 20,
     'bid': 0.0,
     'ask': 0.35
     }
]

cboe_struct = (
    ('symbol', 0),
    ('quote_date', 1),
    ('root', 2),
    ('expiration', 3),
    ('strike', 4),
    ('option_type', 5),
    ('bid', 12),
    ('ask', 14)
)

dod_struct = (
    ('symbol', 0),
    ('option_type', 4),
    ('expiration', 5),
    ('quote_date', 6),
    ('strike', 7),
    ('bid', 9),
    ('ask', 10)
)


def test_invalid_fields():
    invalid_fields = (
        ('symbol', -1),
        ('invalid', -1)
    )

    with pytest.raises(ValueError):
        data = op.get(os.path.join(os.path.dirname(__file__), 'test_data', 'test_dod_a.csv'),
                      start=date(2016, 1, 1),
                      end=date(2016, 12, 31),
                      struct=invalid_fields
                      )


def test_valid_fields():
    valid_fields = (
        ('symbol', 0),
        ('underlying_price', 1),
        ('option_type', 4),
        ('expiration', 5),
        ('quote_date', 6),
        ('strike', 7),
        ('bid', 9),
        ('ask', 10),
        ('volume', 11),
        ('oi', 12),
        ('iv', 14),
        ('delta', 17),
        ('gamma', 18),
        ('theta', 19),
        ('vega', 20)
    )

    try:
        data = op.get(os.path.join(os.path.dirname(__file__), 'test_data', 'test_dod_a.csv'),
                      start=date(2016, 1, 1),
                      end=date(2016, 12, 31),
                      struct=valid_fields,
                      prompt=False
                      )
    except ValueError:
        pytest.fail('ValueError raised')


def test_invalid_idx():
    invalid_idx = (
        ('symbol', -1),
        ('quote_date', -2)
    )

    with pytest.raises(ValueError):
        data = op.get(os.path.join(os.path.dirname(__file__), 'test_data', 'test_dod_a.csv'),
                      start=date(2016, 1, 1),
                      end=date(2016, 12, 31),
                      struct=invalid_idx,
                      prompt=False
                      )


def test_invalid_start_end():
    valid_fields = (
        ('symbol', 0),
        ('quote_date', 1)
    )

    start = date(2016, 1, 1)
    end = date(2015, 1, 1)

    with pytest.raises(ValueError):
        data = op.get(os.path.join(os.path.dirname(__file__), 'test_data', 'test_dod_a.csv'),
                      start=start,
                      end=end,
                      struct=valid_fields,
                      prompt=False
                      )


def test_invalid_start_end_fields():
    start = date(2016, 1, 1)
    end = date(2015, 1, 1)

    invalid_fields = (
        ('symbol', -1),
        ('invalid', -1)
    )

    with pytest.raises(ValueError):
        data = op.get(os.path.join(os.path.dirname(__file__), 'test_data', 'test_dod_a.csv'),
                      start=start,
                      end=end,
                      struct=invalid_fields,
                      prompt=False
                      )


def test_data_cboe_import():
    cols = list(zip(*cboe_struct))[0]
    test_df = pd.DataFrame(cboe_test_data, columns=cols)
    test_df['expiration'] = pd.to_datetime(test_df.expiration, infer_datetime_format=True, format='%Y-%m-%d')
    test_df['quote_date'] = pd.to_datetime(test_df.quote_date, infer_datetime_format=True, format='%Y-%m-%d')
    test_df.set_index('quote_date', inplace=True, drop=False)

    data = op.get(os.path.join(os.path.dirname(__file__), 'test_data', 'test_cboe_spx.csv'),
                  start=date(2016, 1, 1),
                  end=date(2016, 12, 31),
                  struct=cboe_struct,
                  prompt=False
                  )

    pt.assert_frame_equal(test_df, data)


def test_data_dod_import():
    cols = list(zip(*dod_struct))[0]
    test_df = pd.DataFrame(dod_test_data, columns=cols)
    test_df['expiration'] = pd.to_datetime(test_df.expiration, format='%Y-%m-%d')
    test_df['quote_date'] = pd.to_datetime(test_df.quote_date, format='%Y-%m-%d')
    test_df.set_index(['quote_date'], inplace=True, drop=False)

    data = op.get(os.path.join(os.path.dirname(__file__), 'test_data', 'test_dod_a.csv'),
                  start=date(2016, 1, 1),
                  end=date(2016, 12, 31),
                  struct=dod_struct,
                  prompt=False
                  )

    pt.assert_frame_equal(test_df, data)


def test_data_cboe_import_bulk():
    cols = list(zip(*cboe_struct))[0]
    test_df = pd.DataFrame(cboe_test_data, columns=cols)
    test_df['expiration'] = pd.to_datetime(test_df.expiration, infer_datetime_format=True, format='%Y-%m-%d')
    test_df['quote_date'] = pd.to_datetime(test_df.quote_date, infer_datetime_format=True, format='%Y-%m-%d')
    test_df.set_index(['quote_date'], inplace=True, drop=False)

    data = op.gets(os.path.join(os.path.dirname(__file__), 'test_data', 'daily'),
                   start=date(2016, 1, 4),
                   end=date(2016, 1, 6),
                   struct=cboe_struct,
                   prompt=False
                   )

    pt.assert_frame_equal(test_df, data)


def test_data_cboe_date_range():
    cols = list(zip(*cboe_struct))[0]
    test_df = pd.DataFrame(cboe_test_data[2:], columns=cols)
    test_df['expiration'] = pd.to_datetime(test_df.expiration, infer_datetime_format=True, format='%Y-%m-%d')
    test_df['quote_date'] = pd.to_datetime(test_df.quote_date, infer_datetime_format=True, format='%Y-%m-%d')
    test_df.set_index(['quote_date'], inplace=True, drop=False)

    data = op.gets(os.path.join(os.path.dirname(__file__), 'test_data', 'daily'),
                   start=date(2016, 1, 5),
                   end=date(2016, 1, 6),
                   struct=cboe_struct,
                   prompt=False
                   )

    pt.assert_frame_equal(test_df, data)


def test_duplicate_idx_in_struct():
    invalid_struct = (
        ('symbol', 0),
        ('option_type', 4),
        ('expiration', 5),
        ('quote_date', 5),
        ('strike', 7),
        ('bid', 9),
        ('ask', 10)
    )

    with pytest.raises(ValueError):
        data = op.get(os.path.join(os.path.dirname(__file__), 'test_data', 'daily'),
                      start=date(2016, 1, 5),
                      end=date(2016, 1, 6),
                      struct=invalid_struct,
                      prompt=False
                      )
