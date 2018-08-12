import pandas as pd
import pandas.util.testing as pt
import pytest

from optopsy.option_strategy import long_call_spread, short_call_spread, \
    long_put_spread, short_put_spread
from tests.data_fixtures import one_day_data
from tests.filter_fixtures import test_vertical_filters
from optopsy.enums import OrderAction

pd.set_option('display.expand_frame_repr', False)


def expected_vertical_calls_long_leg(n=1):
    df = (
        pd.DataFrame({
            f"leg_{n}_symbol": [".A160115C00020000", ".A160115C00021000"],
            f"leg_{n}_expiration": ["2016-01-15", "2016-01-15"],
            f"leg_{n}_quote_date": ["2016-01-05", "2016-01-05"],
            f"leg_{n}_underlying_price": [40.55, 40.55],
            f"leg_{n}_strike": [20, 21],
            f"leg_{n}_bid": [20.3, 20.3],
            f"leg_{n}_ask": [21.35, 21.35],
            f"leg_{n}_delta": [0.02, 0.02],
            f"leg_{n}_gamma": [0.00, 0.00],
            f"leg_{n}_theta": [-0.05, -0.05],
            f"leg_{n}_vega": [0.00, 0.00],
            f"leg_{n}_dte": [10, 10]
        }
        )
    )

    df[f"leg_{n}_expiration"] = pd.to_datetime(df[f"leg_{n}_expiration"],
                                               infer_datetime_format=True,
                                               format="%Y-%m-%d")
    df[f"leg_{n}_quote_date"] = pd.to_datetime(df[f"leg_{n}_quote_date"],
                                               infer_datetime_format=True,
                                               format="%Y-%m-%d")
    return df


def expected_vertical_calls_short_leg(n=1):
    df = (
        pd.DataFrame({
            f"leg_{n}_symbol": [".A160115C00020000", ".A160115C00021000"],
            f"leg_{n}_expiration": ["2016-01-15", "2016-01-15"],
            f"leg_{n}_quote_date": ["2016-01-05", "2016-01-05"],
            f"leg_{n}_underlying_price": [40.55, 40.55],
            f"leg_{n}_strike": [20, 21],
            f"leg_{n}_bid": [-20.3, -20.3],
            f"leg_{n}_ask": [-21.35, -21.35],
            f"leg_{n}_delta": [-0.02, -0.02],
            f"leg_{n}_gamma": [0.00, 0.00],
            f"leg_{n}_theta": [0.05, 0.05],
            f"leg_{n}_vega": [-0.00, -0.00],
            f"leg_{n}_dte": [10, 10]
        }
        )
    )

    df[f"leg_{n}_expiration"] = pd.to_datetime(df[f"leg_{n}_expiration"],
                                               infer_datetime_format=True,
                                               format="%Y-%m-%d")
    df[f"leg_{n}_quote_date"] = pd.to_datetime(df[f"leg_{n}_quote_date"],
                                               infer_datetime_format=True,
                                               format="%Y-%m-%d")
    return df


def expected_vertical_puts_long_leg(n=1):
    df = pd.DataFrame({
        f"leg_{n}_symbol": [".A160115P00020000", ".A160115P00021000"],
        f"leg_{n}_expiration": ["2016-01-15", "2016-01-15"],
        f"leg_{n}_quote_date": ["2016-01-05", "2016-01-05"],
        f"leg_{n}_underlying_price": [40.55, 40.55],
        f"leg_{n}_strike": [20, 21],
        f"leg_{n}_bid": [0.0, 0.0],
        f"leg_{n}_ask": [0.35, 0.35],
        f"leg_{n}_delta": [-0.02, -0.03],
        f"leg_{n}_gamma": [0.00, 0.01],
        f"leg_{n}_theta": [-0.05, -0.03],
        f"leg_{n}_vega": [0.00, 0.00],
        f"leg_{n}_dte": [10, 10]
    })

    df[f"leg_{n}_expiration"] = pd.to_datetime(df[f"leg_{n}_expiration"],
                                               infer_datetime_format=True,
                                               format="%Y-%m-%d")
    df[f"leg_{n}_quote_date"] = pd.to_datetime(df[f"leg_{n}_quote_date"],
                                               infer_datetime_format=True,
                                               format="%Y-%m-%d")

    return df


def expected_vertical_puts_short_leg(n=1):
    df = pd.DataFrame({
        f"leg_{n}_symbol": [".A160115P00020000", ".A160115P00021000"],
        f"leg_{n}_expiration": ["2016-01-15", "2016-01-15"],
        f"leg_{n}_quote_date": ["2016-01-05", "2016-01-05"],
        f"leg_{n}_underlying_price": [40.55, 40.55],
        f"leg_{n}_strike": [20, 21],
        f"leg_{n}_bid": [0.0, 0.0],
        f"leg_{n}_ask": [-0.35, -0.35],
        f"leg_{n}_delta": [0.02, 0.03],
        f"leg_{n}_gamma": [-0.00, -0.01],
        f"leg_{n}_theta": [0.05, 0.03],
        f"leg_{n}_vega": [-0.00, -0.00],
        f"leg_{n}_dte": [10, 10]
    })

    df[f"leg_{n}_expiration"] = pd.to_datetime(df[f"leg_{n}_expiration"],
                                               infer_datetime_format=True,
                                               format="%Y-%m-%d")
    df[f"leg_{n}_quote_date"] = pd.to_datetime(df[f"leg_{n}_quote_date"],
                                               infer_datetime_format=True,
                                               format="%Y-%m-%d")

    return df


def test_long_call_spread(one_day_data, test_vertical_filters):
    actual_spread = long_call_spread(one_day_data)
    assert actual_spread[0] == OrderAction.BTO
    assert isinstance(actual_spread[1], list)
    assert len(actual_spread[1]) == 2
    pt.assert_frame_equal(actual_spread[1][0], expected_vertical_calls_long_leg(1))
    pt.assert_frame_equal(actual_spread[1][1], expected_vertical_calls_short_leg(2))


def test_short_call_spread(one_day_data, test_vertical_filters):
    actual_spread = short_call_spread(one_day_data)
    assert actual_spread[0] == OrderAction.STO
    assert isinstance(actual_spread[1], list)
    assert len(actual_spread[1]) == 2
    pt.assert_frame_equal(actual_spread[1][0], expected_vertical_calls_short_leg(1))
    pt.assert_frame_equal(actual_spread[1][1], expected_vertical_calls_long_leg(2))


def test_long_put_spread(one_day_data, test_vertical_filters):
    actual_spread = long_put_spread(one_day_data)
    assert actual_spread[0] == OrderAction.BTO
    assert isinstance(actual_spread[1], list)
    assert len(actual_spread[1]) == 2
    pt.assert_frame_equal(actual_spread[1][0], expected_vertical_puts_long_leg(1))
    pt.assert_frame_equal(actual_spread[1][1], expected_vertical_puts_short_leg(2))


def test_short_put_spread(one_day_data, test_vertical_filters):
    actual_spread = short_put_spread(one_day_data)
    assert actual_spread[0] == OrderAction.STO
    assert isinstance(actual_spread[1], list)
    assert len(actual_spread[1]) == 2
    pt.assert_frame_equal(actual_spread[1][0], expected_vertical_puts_short_leg(1))
    pt.assert_frame_equal(actual_spread[1][1], expected_vertical_puts_long_leg(2))
