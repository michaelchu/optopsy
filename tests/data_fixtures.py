import pytest
import pandas as pd
from optopsy.data import _format


# Data to test results with ----------------------------------------------
@pytest.fixture
def one_day_data():
    return (
        pd.DataFrame(
            {
                'option_symbol': ['A160115C00020000', 'A160115P00020000',
                                  'A160115C00021000', 'A160115P00021000'],
                'option_type': ['c', 'p', 'c', 'p'],
                'underlying_price': [40.55, 40.55, 40.55, 40.55],
                'expiration': ['2016-01-15', '2016-01-15', '2016-01-15', '2016-01-15'],
                'quote_date': ['2016-01-05', '2016-01-05', '2016-01-05', '2016-01-05'],
                'strike': [20, 20, 21, 21],
                'bid': [20.3, 0.0, 20.3, 0.0],
                'ask': [21.35, 0.35, 21.35, 0.35],
                'delta': [0.02, -0.02, 0.02, -0.03],
                'gamma': [0.00, 0.00, 0.00, 0.01],
                'theta': [-0.05, -0.05, -0.05, -0.03],
                'vega': [0.00, 0.00, 0.00, 0.00]
            }
        ).pipe(_format)
    )