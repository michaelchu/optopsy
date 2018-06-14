import os

import pandas as pd

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

invalid_idx = (
    ('symbol', -1),
    ('quote_date', -2)
)

invalid_fields = (
    ('symbol', 0),
    ('invalid', 1)
)

invalid_struct = (
    ('symbol', 0),
    ('option_type', 4),
    ('expiration', 5),
    ('quote_date', 5),
    ('strike', 7),
    ('bid', 9),
    ('ask', 10)
)

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

dod_struct_with_opt_sym = (
    ('symbol', 0),
    ('option_symbol', 3),
    ('option_type', 4),
    ('expiration', 5),
    ('quote_date', 6),
    ('strike', 7),
    ('bid', 9),
    ('ask', 10)
)

dod_struct_with_opt_sym_greeks = (
    ('symbol', 0),
    ('option_symbol', 3),
    ('option_type', 4),
    ('expiration', 5),
    ('quote_date', 6),
    ('strike', 7),
    ('bid', 9),
    ('ask', 10),
    ('delta', 17),
    ('gamma', 18),
    ('theta', 19),
    ('vega', 20)
)

hod_struct = (
    ('symbol', 0),
    ('option_type', 5),
    ('expiration', 6),
    ('quote_date', 7),
    ('strike', 8),
    ('bid', 10),
    ('ask', 11),
)

hod_struct_with_sym = (
    ('symbol', 0),
    ('option_symbol', 3),
    ('option_type', 5),
    ('expiration', 6),
    ('quote_date', 7),
    ('strike', 8),
    ('bid', 10),
    ('ask', 11),
)

hod_struct_with_sym_greeks = (
    ('symbol', 0),
    ('option_symbol', 3),
    ('option_type', 5),
    ('expiration', 6),
    ('quote_date', 7),
    ('strike', 8),
    ('bid', 10),
    ('ask', 11),
    ('delta', 15),
    ('gamma', 16),
    ('theta', 17),
    ('vega', 18)
)

cboe_test_data = [
    {'symbol': '.SPX160108C00700000',
     'option_type': 'c',
     'root': 'SPXW',
     'expiration': '1/8/2016 0:00:00',
     'quote_date': '1/4/2016 0:00:00',
     'strike': 700.00,
     'bid': 1299.60,
     'ask': 1305.30
     },
    {'symbol': '.SPX160108P00700000',
     'option_type': 'p',
     'root': 'SPXW',
     'expiration': '1/8/2016 0:00:00',
     'quote_date': '1/4/2016 0:00:00',
     'strike': 700.00,
     'bid': 0.00,
     'ask': 0.05
     },
    {'symbol': '.SPX160108C00700000',
     'option_type': 'c',
     'root': 'SPXW',
     'expiration': '1/8/2016 0:00:00',
     'quote_date': '1/5/2016 0:00:00',
     'strike': 700.00,
     'bid': 1313.60,
     'ask': 1319.40
     },
    {'symbol': '.SPX160108P00700000',
     'option_type': 'p',
     'root': 'SPXW',
     'expiration': '1/8/2016 0:00:00',
     'quote_date': '1/5/2016 0:00:00',
     'strike': 700.00,
     'bid': 0.00,
     'ask': 0.05
     },
    {'symbol': '.SPX160108C00700000',
     'option_type': 'c',
     'root': 'SPXW',
     'expiration': '1/8/2016 0:00:00',
     'quote_date': '1/6/2016 0:00:00',
     'strike': 700.00,
     'bid': 1299.60,
     'ask': 1305.30
     },
    {'symbol': '.SPX160108P00700000',
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
    {'symbol': '.A160115C00020000',
     'option_type': 'c',
     'expiration': '2016-01-15',
     'quote_date': '2016-01-05',
     'strike': 20,
     'bid': 20.3,
     'ask': 21.35
     },
    {'symbol': '.A160115P00020000',
     'option_type': 'p',
     'expiration': '2016-01-15',
     'quote_date': '2016-01-05',
     'strike': 20,
     'bid': 0.0,
     'ask': 0.35
     },
    {'symbol': '.A160115C00020000',
     'option_type': 'c',
     'expiration': '2016-01-15',
     'quote_date': '2016-01-06',
     'strike': 20,
     'bid': 20.3,
     'ask': 21.35
     },
    {'symbol': '.A160115P00020000',
     'option_type': 'p',
     'expiration': '2016-01-15',
     'quote_date': '2016-01-06',
     'strike': 20,
     'bid': 0.0,
     'ask': 0.35
     },
    {'symbol': '.A160115C00020000',
     'option_type': 'c',
     'expiration': '2016-01-15',
     'quote_date': '2016-01-07',
     'strike': 20,
     'bid': 20.3,
     'ask': 21.35
     },
    {'symbol': '.A160115P00020000',
     'option_type': 'p',
     'expiration': '2016-01-15',
     'quote_date': '2016-01-07',
     'strike': 20,
     'bid': 0.0,
     'ask': 0.35
     }
]


def format_test_data(dataframe):
    dataframe['expiration'] = pd.to_datetime(dataframe['expiration'])
    dataframe['quote_date'] = pd.to_datetime(dataframe['quote_date'])
    dataframe = dataframe.set_index('quote_date', drop=False)
    return dataframe


def data_factory(path, struct, start, end):
    return op.get(os.path.join(os.path.dirname(__file__), 'test_data', path),
                  start=start,
                  end=end,
                  struct=struct,
                  prompt=False
                  )
