import os
from datetime import datetime

import pandas as pd
import pytest

from optopsy.filters import (
    delta,
    end_date,
    entry_dte,
    expr_type,
    start_date,
    strike_pct,
)


def filepath():
    curr_file = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(curr_file, "./test_data/data.csv")


data = pd.read_csv(
    filepath(), parse_dates=["expiration", "quote_date"], infer_datetime_format=True
)


def test_start_date():
    start = datetime(1990, 1, 1)
    df = start_date(data, datetime(1990, 1, 1))
    assert not df.empty
    assert all(v >= start for v in df["expiration"])


def test_start_date_out_of_bound():
    start = datetime(2020, 1, 21)
    df = start_date(data, start)
    assert df.empty


def test_end_date():
    end = datetime(1990, 1, 21)
    df = end_date(data, end)
    assert not df.empty
    assert all(v <= end for v in df["expiration"])


def test_end_date_out_of_bound():
    start = datetime(1990, 1, 19)
    df = end_date(data, start)
    assert df.empty


def test_invalid_start_date():
    with pytest.raises(ValueError):
        start_date(data, "123")


def test_invalid_end_date():
    with pytest.raises(ValueError):
        end_date(data, "123")


@pytest.mark.parametrize(
    "value", [(["SPX"], ["SPX"]), (["SPX", "SPXW"], ["SPX", "SPXW"])]
)
def test_expr_type(value):
    df = expr_type(data, value[0])
    assert set(df["underlying_symbol"].unique()).issubset(value[1])


def test_invalid_expr_type():
    with pytest.raises(ValueError):
        expr_type(data, "INVALID")


def test_dte():
    df = entry_dte(data, 18)
    assert not df.empty
    assert "dte" in df.columns
    assert all(v in [17, 18] for v in df["dte"])


def test_dte_exact():
    df = entry_dte(data, 18, 18, 18)
    assert not df.empty
    assert "dte" in df.columns
    assert all(v in [18] for v in df["dte"])


def test_delta():
    df = delta(data, 0.50, 0.40, 0.60)
    assert not df.empty
    assert all(
        v in [0.5528, 0.5098, -0.4574, -0.4898] for v in df["delta"].unique().tolist()
    )


def test_invalid_delta():
    with pytest.raises(ValueError):
        delta(data, "invalid", 0)


def test_invalid_strike_pct():
    with pytest.raises(ValueError):
        strike_pct(data, "invalid", 0)
