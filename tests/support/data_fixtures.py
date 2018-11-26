import pandas as pd
import pytest
import os
from optopsy.data import format_option_df


CURRENT_FILE = os.path.abspath(os.path.dirname(__file__))
TEST_FILE_PATH = os.path.join(CURRENT_FILE, "../test_data/test_options_data.csv")
TEST_FILE_PATH_FULL = os.path.join(
    CURRENT_FILE, "../test_data/test_options_data_full.csv"
)

TEST_STRUCT = (
    ("underlying_symbol", 0),
    ("underlying_price", 1),
    ("option_type", 5),
    ("expiration", 6),
    ("quote_date", 7),
    ("strike", 8),
    ("bid", 10),
    ("ask", 11),
    ("delta", 15),
    ("gamma", 16),
    ("theta", 17),
    ("vega", 18),
)


def _parse_date_cols(columns):
    quote_date_idx = columns[0].index("quote_date")
    expiration_idx = columns[0].index("expiration")
    return [quote_date_idx, expiration_idx]


# Data to test results with ----------------------------------------------
@pytest.fixture
def options_data(hod_struct):
    cols = list(zip(*hod_struct))
    date_cols = _parse_date_cols(cols)
    return pd.read_csv(
        TEST_FILE_PATH,
        parse_dates=date_cols,
        names=cols[0],
        usecols=cols[1],
        skiprows=1,
        nrows=None,
    ).pipe(format_option_df)


@pytest.fixture
def options_data_full(hod_struct):
    cols = list(zip(*hod_struct))
    date_cols = _parse_date_cols(cols)
    return pd.read_csv(
        TEST_FILE_PATH_FULL,
        parse_dates=date_cols,
        names=cols[0],
        usecols=cols[1],
        skiprows=1,
        nrows=None,
    ).pipe(format_option_df)
