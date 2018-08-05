import pandas as pd
import pytest


# Struts for testing purposes --------------------------------------------
@pytest.fixture
def valid_fields():
    return (
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


@pytest.fixture
def invalid_idx():
    return (
        ('symbol', -1),
        ('quote_date', -2)
    )


@pytest.fixture
def invalid_fields():
    return (
        ('symbol', 0),
        ('invalid', 1)
    )


@pytest.fixture
def invalid_struct():
    return (
        ('symbol', 0),
        ('option_type', 4),
        ('expiration', 5),
        ('quote_date', 5),
        ('strike', 7),
        ('bid', 9),
        ('ask', 10)
    )


@pytest.fixture
def cboe_struct():
    return (
        ('symbol', 0),
        ('quote_date', 1),
        ('root', 2),
        ('expiration', 3),
        ('strike', 4),
        ('option_type', 5),
        ('bid', 12),
        ('ask', 14)
    )


# Data to test results with ----------------------------------------------
@pytest.fixture
def one_day_data():
    return (
        pd.DataFrame([
            {
                'symbol': '.A160115C00020000',
                'option_type': 'c',
                'underlying_price': 40.55,
                'expiration': '2016-01-15',
                'quote_date': '2016-01-05',
                'strike': 20,
                'bid': 20.3,
                'ask': 21.35,
                'delta': 0.02,
                'gamma': 0.00,
                'theta': -0.05,
                'vega': 0.00,
            },
            {
                'symbol': '.A160115P00020000',
                'option_type': 'p',
                'underlying_price': 40.55,
                'expiration': '2016-01-15',
                'quote_date': '2016-01-05',
                'strike': 20,
                'bid': 0.0,
                'ask': 0.35,
                'delta': -0.02,
                'gamma': 0.00,
                'theta': -0.05,
                'vega': 0.00,
            },
            {
                'symbol': '.A160115C00021000',
                'option_type': 'c',
                'underlying_price': 40.55,
                'expiration': '2016-01-15',
                'quote_date': '2016-01-05',
                'strike': 21,
                'bid': 20.3,
                'ask': 21.35,
                'delta': 0.02,
                'gamma': 0.00,
                'theta': -0.05,
                'vega': 0.00
            },
            {
                'symbol': '.A160115P00021000',
                'option_type': 'p',
                'underlying_price': 40.55,
                'expiration': '2016-01-15',
                'quote_date': '2016-01-05',
                'strike': 21,
                'bid': 0.0,
                'ask': 0.35,
                'delta': -0.03,
                'gamma': 0.01,
                'theta': -0.03,
                'vega': 0.00
            }
        ]).assign(
            expiration=lambda r: pd.to_datetime(r['expiration'], infer_datetime_format=True,
                                                format='%Y-%m-%d'),
            quote_date=lambda r: pd.to_datetime(r['quote_date'], infer_datetime_format=True,
                                                format='%Y-%m-%d')
        )
        .set_index('quote_date', inplace=False, drop=False)
        .round(2)
    )


@pytest.fixture
def three_day_data():
    return pd.DataFrame([
        {
            'symbol': '.A160115C00020000',
            'option_type': 'c',
            'underlying_price': 40.55,
            'expiration': '2016-01-15',
            'quote_date': '2016-01-05',
            'strike': 20,
            'bid': 20.3,
            'ask': 21.35,
            'delta': 0.02,
            'gamma': 0.00,
            'theta': -0.05,
            'vega': 0.00,
        },
        {
            'symbol': '.A160115P00020000',
            'option_type': 'p',
            'underlying_price': 40.55,
            'expiration': '2016-01-15',
            'quote_date': '2016-01-05',
            'strike': 20,
            'bid': 0.0,
            'ask': 0.35,
            'delta': -0.02,
            'gamma': 0.00,
            'theta': -0.05,
            'vega': 0.00,
        },
        {
            'symbol': '.A160115C00020000',
            'option_type': 'c',
            'underlying_price': 40.55,
            'expiration': '2016-01-15',
            'quote_date': '2016-01-06',
            'strike': 20,
            'bid': 20.3,
            'ask': 21.35,
            'delta': 0.02,
            'gamma': 0.00,
            'theta': -0.05,
            'vega': 0.00,
        },
        {
            'symbol': '.A160115P00020000',
            'option_type': 'p',
            'underlying_price': 40.55,
            'expiration': '2016-01-15',
            'quote_date': '2016-01-06',
            'strike': 20,
            'bid': 0.0,
            'ask': 0.35,
            'delta': -0.02,
            'gamma': 0.00,
            'theta': -0.05,
            'vega': 0.00,
        },
        {
            'symbol': '.A160115C00020000',
            'option_type': 'c',
            'underlying_price': 40.55,
            'expiration': '2016-01-15',
            'quote_date': '2016-01-07',
            'strike': 20,
            'bid': 20.3,
            'ask': 21.35,
            'delta': 0.02,
            'gamma': 0.00,
            'theta': -0.05,
            'vega': 0.00,
        },
        {
            'symbol': '.A160115P00020000',
            'option_type': 'p',
            'underlying_price': 40.55,
            'expiration': '2016-01-15',
            'quote_date': '2016-01-07',
            'strike': 20,
            'bid': 0.0,
            'ask': 0.35,
            'delta': -0.02,
            'gamma': 0.00,
            'theta': -0.05,
            'vega': 0.00,
        }
    ]).assign(
        expiration=lambda r: pd.to_datetime(r['expiration'], infer_datetime_format=True,
                                            format='%Y-%m-%d'),
        quote_date=lambda r: pd.to_datetime(r['quote_date'], infer_datetime_format=True,
                                            format='%Y-%m-%d')
    )
