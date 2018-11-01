import pytest
import pandas as pd
from optopsy.data import format_option_df


# Data to test results with ----------------------------------------------
@pytest.fixture(scope="module")
def one_day_data():
    return (
        pd.DataFrame(
            {
                'option_symbol': ['A160115C00001000', 'A160115P00001000',
                                  'A160115C00002000', 'A160115P00002000'],
                'option_type': ['c', 'p', 'c', 'p'],
                'underlying_price': [1.00, 1.00, 1.00, 1.00],
                'expiration': ['2016-01-15', '2016-01-15', '2016-01-15', '2016-01-15'],
                'quote_date': ['2016-01-05', '2016-01-05', '2016-01-05', '2016-01-05'],
                'strike': [1.0, 1.0, 2.0, 2.0],
                'bid': [0.017, 0.016, 0.0, 0.998],
                'ask': [0.018, 0.017, 0.0, 0.999],
                'delta': [0.519, -0.481, 0.0, -1],
                'gamma': [9.63, 9.63, 0.0, 0.0],
                'theta': [-0.001, -0.001, 0.0, 0.0],
                'vega': [0.001, 0.001, 0.00, 0.00]
            }
        ).pipe(format_option_df)
    )
