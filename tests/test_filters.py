from .support.data_fixtures import options_data
from pandas.util.testing import assert_frame_equal
from optopsy.filters import *
import pandas as pd
import pytest


pd.set_option('display.expand_frame_repr', False)


@pytest.mark.usefixtures("options_data")
def test_contract_size(options_data):
    df = contract_size(options_data, 10, 0)
    assert 'contracts' in df.columns
    assert all(v == 10 for v in df['contracts'])


def test_invalid_contract_size(options_data):
    with pytest.raises(ValueError):
        contract_size(options_data, 10.25, 0)


def test_dte(options_data):
    df = entry_dte(options_data, 18, 0)
    assert 'dte' in df.columns
    assert all(v in [17, 18] for v in df['dte'])


def test_dte_exact(options_data):
    df = entry_dte(options_data, (18, 18, 18), 0)
    assert 'dte' in df.columns
    assert all(v in [18] for v in df['dte'])


def test_dte_tuple(options_data):
    df = entry_dte(options_data, (17, 18, 19), 0)
    assert 'dte' in df.columns
    assert all(v in [17, 18] for v in df['dte'])


def test_dte_float(options_data):
    df = entry_dte(options_data, 18.25, 0)
    assert 'dte' in df.columns
    assert all(v in [17, 18] for v in df['dte'])


def test_dte_float_tuple(options_data):
    df = entry_dte(options_data, (17.05, 18.05, 190.5), 0)
    assert 'dte' in df.columns
    assert all(v in [17, 18] for v in df['dte'])


def test_dte_float_value(options_data):
    df = entry_dte(options_data, (18, 18, 18), 0)
    assert 'dte' in df.columns
    assert all(v in [18] for v in df['dte'])


def test_leg1_delta_tuple(options_data):
    df = leg1_delta(options_data, (0.45, 0.50, 0.55), 0)
    assert all(v in [0.55, 0.51, -0.46, -0.49] for v in df['delta'].unique().tolist())


def test_leg1_delta_value(options_data):
    df = leg1_delta(options_data, 0.50, 0)
    assert all(v in [0.55, 0.51, -0.46, -0.49] for v in df['delta'].unique().tolist())


def test_leg2_delta_tuple(options_data):
    df = leg2_delta(options_data, (0.45, 0.50, 0.55), 1)
    assert all(v in [0.55, 0.51, -0.46, -0.49] for v in df['delta'].unique().tolist())


def test_leg2_delta_value(options_data):
    df = leg2_delta(options_data, 0.50, 1)
    assert all(v in [0.55, 0.51, -0.46, -0.49] for v in df['delta'].unique().tolist())


def test_leg3_delta_tuple(options_data):
    df = leg3_delta(options_data, (0.45, 0.50, 0.55), 2)
    assert all(v in [0.55, 0.51, -0.46, -0.49] for v in df['delta'].unique().tolist())


def test_leg3_delta_value(options_data):
    df = leg3_delta(options_data, 0.50, 2)
    assert all(v in [0.55, 0.51, -0.46, -0.49] for v in df['delta'].unique().tolist())


def test_leg4_delta_tuple(options_data):
    df = leg4_delta(options_data, (0.45, 0.50, 0.55), 3)
    assert all(v in [0.55, 0.51, -0.46, -0.49] for v in df['delta'].unique().tolist())


def test_leg4_delta_value(options_data):
    df = leg4_delta(options_data, 0.50, 3)
    assert all(v in [0.55, 0.51, -0.46, -0.49] for v in df['delta'].unique().tolist())


def test_invalid_leg1_delta(options_data):
    with pytest.raises(ValueError):
        leg1_delta(options_data, 'invalid', 0)


def test_wrong_leg_leg1_delta(options_data):
    df = leg1_delta(options_data, 0.50, 1)
    assert_frame_equal(df, options_data)


def test_wrong_leg_leg2_delta(options_data):
    df = leg2_delta(options_data, 0.50, 2)
    assert_frame_equal(df, options_data)


def test_wrong_leg_leg3_delta(options_data):
    df = leg2_delta(options_data, 0.50, 3)
    assert_frame_equal(df, options_data)


def test_wrong_leg_leg4_delta(options_data):
    df = leg2_delta(options_data, 0.50, 4)
    assert_frame_equal(df, options_data)


def test_leg1_strike_pct_tuple(options_data):
    df = leg1_strike_pct(options_data, (0.75, 0.80, 0.90), 0)
    assert all(v in [0.89] for v in df['strike_pct'].unique().tolist())


def test_leg1_strike_pct_value(options_data):
    df = leg1_strike_pct(options_data, 0.80, 0)
    assert all(v in [0.89] for v in df['strike_pct'].unique().tolist())


def test_leg2_strike_pct_tuple(options_data):
    df = leg2_strike_pct(options_data, (0.75, 0.80, 0.90), 1)
    assert all(v in [0.89] for v in df['strike_pct'].unique().tolist())


def test_leg2_strike_pct_value(options_data):
    df = leg2_strike_pct(options_data, 0.80, 1)
    assert all(v in [0.89] for v in df['strike_pct'].unique().tolist())


def test_leg3_strike_pct_tuple(options_data):
    df = leg3_strike_pct(options_data, (0.75, 0.80, 0.90), 2)
    assert all(v in [0.89] for v in df['strike_pct'].unique().tolist())


def test_leg3_strike_pct_value(options_data):
    df = leg3_strike_pct(options_data, 0.80, 2)
    assert all(v in [0.89] for v in df['strike_pct'].unique().tolist())


def test_leg4_strike_pct_tuple(options_data):
    df = leg4_strike_pct(options_data, (0.75, 0.80, 0.90), 3)
    assert all(v in [0.89] for v in df['strike_pct'].unique().tolist())


def test_leg4_strike_pct_value(options_data):
    df = leg4_strike_pct(options_data, 0.80, 3)
    assert all(v in [0.89] for v in df['strike_pct'].unique().tolist())


def test_invalid_leg1_strike_pct(options_data):
    with pytest.raises(ValueError):
        leg1_strike_pct(options_data, 'invalid', 0)


def test_wrong_leg_leg1_strike_pct(options_data):
    df = leg1_strike_pct(options_data, 0.50, 1)
    assert_frame_equal(df, options_data)


def test_wrong_leg_leg2_strike_pct(options_data):
    df = leg1_strike_pct(options_data, 0.50, 2)
    assert_frame_equal(df, options_data)

