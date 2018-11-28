from pandas.util.testing import assert_frame_equal
from optopsy.filters import *
from optopsy.enums import OptionType
from optopsy.option_strategies import create_spread
from datetime import datetime
from optopsy.data import get
import pytest
import os

CURRENT_FILE = os.path.abspath(os.path.dirname(__file__))
TEST_FILE_PATH_FULL = os.path.join(
    CURRENT_FILE, "./test_data/test_options_data_full.csv"
)

hod_struct = (
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

DATA = get(TEST_FILE_PATH_FULL, hod_struct, prompt=False)


def test_start_date(options_data):
    start = datetime(1990, 1, 1)
    df = start_date(options_data, start, 0)
    assert not df.empty
    assert all(v >= start for v in df["expiration"])


def test_start_date_ouf_of_bound(options_data):
    start = datetime(1990, 1, 21)
    df = start_date(options_data, start, 0)
    assert df.empty


def test_end_date(options_data):
    end = datetime(1990, 1, 21)
    df = end_date(options_data, end, 0)
    assert not df.empty
    assert all(v <= end for v in df["expiration"])


def test_end_date_ouf_of_bound(options_data):
    start = datetime(1990, 1, 19)
    df = end_date(options_data, start, 0)
    assert df.empty


def test_invalid_start_date(options_data):
    with pytest.raises(ValueError):
        start_date(options_data, "123", 0)


def test_invalid_end_date(options_data):
    with pytest.raises(ValueError):
        end_date(options_data, "123", 0)


@pytest.mark.parametrize(
    "value", [(["SPX"], ["SPX"]), (["SPX", "SPXW"], ["SPX", "SPXW"])]
)
def test_expr_type(value):
    df = expr_type(DATA, value[0], 0)
    assert set(df["underlying_symbol"].unique()).issubset(value[1])


@pytest.mark.parametrize(
    "value", [(["INVALID"], ["SPX", "SPXW"]), (None, ["SPX", "SPXW"])]
)
def test_invalid_expr_type(value):
    df = expr_type(DATA, value[0], 0)
    result = df["underlying_symbol"].unique()
    assert result != []
    assert set(result).issubset(value[1])


def test_contract_size(options_data):
    df = contract_size(options_data, 10, 0)
    assert not df.empty
    assert "contracts" in df.columns
    assert all(v == 10 for v in df["contracts"])


def test_invalid_contract_size(options_data):
    with pytest.raises(ValueError):
        contract_size(options_data, 10.25, 0)


def test_dte(options_data):
    df = entry_dte(options_data, 18, 0)
    assert not df.empty
    assert "dte" in df.columns
    assert all(v in [17, 18] for v in df["dte"])


def test_dte_exact(options_data):
    df = entry_dte(options_data, (18, 18, 18), 0)
    assert not df.empty
    assert "dte" in df.columns
    assert all(v in [18] for v in df["dte"])


def test_dte_tuple(options_data):
    df = entry_dte(options_data, (17, 18, 19), 0)
    assert not df.empty
    assert "dte" in df.columns
    assert all(v in [17, 18] for v in df["dte"])


def test_dte_float(options_data):
    df = entry_dte(options_data, 18.25, 0)
    assert not df.empty
    assert "dte" in df.columns
    assert all(v in [17, 18] for v in df["dte"])


def test_dte_float_tuple(options_data):
    df = entry_dte(options_data, (17.05, 18.05, 190.5), 0)
    assert not df.empty
    assert "dte" in df.columns
    assert all(v in [17, 18] for v in df["dte"])


def test_dte_float_value(options_data):
    df = entry_dte(options_data, (18, 18, 18), 0)
    assert not df.empty
    assert "dte" in df.columns
    assert all(v in [18] for v in df["dte"])


def test_leg1_delta_tuple(options_data):
    df = leg1_delta(options_data, (0.45, 0.50, 0.55), 0)
    assert not df.empty
    assert all(v in [0.55, 0.51, -0.46, -0.49] for v in df["delta"].unique().tolist())


def test_leg1_delta_value(options_data):
    df = leg1_delta(options_data, 0.50, 0)
    assert not df.empty
    assert all(v in [0.55, 0.51, -0.46, -0.49] for v in df["delta"].unique().tolist())


def test_leg2_delta_tuple(options_data):
    df = leg2_delta(options_data, (0.45, 0.50, 0.55), 1)
    assert not df.empty
    assert all(v in [0.55, 0.51, -0.46, -0.49] for v in df["delta"].unique().tolist())


def test_leg2_delta_value(options_data):
    df = leg2_delta(options_data, 0.50, 1)
    assert not df.empty
    assert all(v in [0.55, 0.51, -0.46, -0.49] for v in df["delta"].unique().tolist())


def test_leg3_delta_tuple(options_data):
    df = leg3_delta(options_data, (0.45, 0.50, 0.55), 2)
    assert not df.empty
    assert all(v in [0.55, 0.51, -0.46, -0.49] for v in df["delta"].unique().tolist())


def test_leg3_delta_value(options_data):
    df = leg3_delta(options_data, 0.50, 2)
    assert not df.empty
    assert all(v in [0.55, 0.51, -0.46, -0.49] for v in df["delta"].unique().tolist())


def test_leg4_delta_tuple(options_data):
    df = leg4_delta(options_data, (0.45, 0.50, 0.55), 3)
    assert not df.empty
    assert all(v in [0.55, 0.51, -0.46, -0.49] for v in df["delta"].unique().tolist())


def test_leg4_delta_value(options_data):
    df = leg4_delta(options_data, 0.50, 3)
    assert not df.empty
    assert all(v in [0.55, 0.51, -0.46, -0.49] for v in df["delta"].unique().tolist())


def test_invalid_leg1_delta(options_data):
    with pytest.raises(ValueError):
        leg1_delta(options_data, "invalid", 0)


def test_wrong_leg_leg1_delta(options_data):
    df = leg1_delta(options_data, 0.50, 1)
    assert not df.empty
    assert_frame_equal(df, options_data)


def test_wrong_leg_leg2_delta(options_data):
    df = leg2_delta(options_data, 0.50, 2)
    assert not df.empty
    assert_frame_equal(df, options_data)


def test_wrong_leg_leg3_delta(options_data):
    df = leg2_delta(options_data, 0.50, 3)
    assert not df.empty
    assert_frame_equal(df, options_data)


def test_wrong_leg_leg4_delta(options_data):
    df = leg2_delta(options_data, 0.50, 4)
    assert not df.empty
    assert_frame_equal(df, options_data)


def test_leg1_strike_pct_tuple(options_data):
    df = leg1_strike_pct(options_data, (0.75, 0.80, 0.90), 0)
    assert not df.empty
    assert all(v in [0.89] for v in df["strike_pct"].unique().tolist())


def test_leg1_strike_pct_value(options_data):
    df = leg1_strike_pct(options_data, 0.80, 0)
    assert not df.empty
    assert all(v in [0.89] for v in df["strike_pct"].unique().tolist())


def test_leg2_strike_pct_tuple(options_data):
    df = leg2_strike_pct(options_data, (0.75, 0.80, 0.90), 1)
    assert not df.empty
    assert all(v in [0.89] for v in df["strike_pct"].unique().tolist())


def test_leg2_strike_pct_value(options_data):
    df = leg2_strike_pct(options_data, 0.80, 1)
    assert not df.empty
    assert all(v in [0.89] for v in df["strike_pct"].unique().tolist())


def test_leg3_strike_pct_tuple(options_data):
    df = leg3_strike_pct(options_data, (0.75, 0.80, 0.90), 2)
    assert not df.empty
    assert all(v in [0.89] for v in df["strike_pct"].unique().tolist())


def test_leg3_strike_pct_value(options_data):
    df = leg3_strike_pct(options_data, 0.80, 2)
    assert not df.empty
    assert all(v in [0.89] for v in df["strike_pct"].unique().tolist())


def test_leg4_strike_pct_tuple(options_data):
    df = leg4_strike_pct(options_data, (0.75, 0.80, 0.90), 3)
    assert not df.empty
    assert all(v in [0.89] for v in df["strike_pct"].unique().tolist())


def test_leg4_strike_pct_value(options_data):
    df = leg4_strike_pct(options_data, 0.80, 3)
    assert not df.empty
    assert all(v in [0.89] for v in df["strike_pct"].unique().tolist())


def test_invalid_leg1_strike_pct(options_data):
    with pytest.raises(ValueError):
        leg1_strike_pct(options_data, "invalid", 0)


def test_wrong_leg_leg1_strike_pct(options_data):
    df = leg1_strike_pct(options_data, 0.50, 1)
    assert not df.empty
    assert_frame_equal(df, options_data)


def test_wrong_leg_leg2_strike_pct(options_data):
    df = leg1_strike_pct(options_data, 0.50, 2)
    assert not df.empty
    assert_frame_equal(df, options_data)
