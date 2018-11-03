import pandas as pd
import pytest
import os
from optopsy.data import format_option_df


CURRENT_FILE = os.path.abspath(os.path.dirname(__file__))
TEST_FILE_PATH = os.path.join(CURRENT_FILE,
                              '../test_data/test_options_data.csv')

TEST_STRUCT = (
    ('underlying_symbol', 0),
    ('underlying_price', 1),
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


# Data to test results with ----------------------------------------------
@pytest.fixture(scope="module")
def options_data():
    cols = list(zip(*TEST_STRUCT))
    return (
        pd.read_csv(
            TEST_FILE_PATH,
            parse_dates=True,
            names=cols[0],
            usecols=cols[1],
            skiprows=1,
            nrows=None
        ).pipe(format_option_df))
