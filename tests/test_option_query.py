import os

import pandas as pd
import pytest

from optopsy.enums import OptionType
from optopsy.option_queries import (between, eq, gt, gte, lt, lte, ne, nearest,
                                    opt_type, underlying_price)


def filepath():
    curr_file = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(curr_file, "./test_data/data.csv")


data = pd.read_csv(
    filepath(), parse_dates=["expiration", "quote_date"], infer_datetime_format=True
)


@pytest.mark.parametrize("option_type", [2, "x", "invalid", (3, 4)])
def test_invalid_option_type(option_type):
    with pytest.raises(ValueError):
        opt_type(data, option_type)


@pytest.mark.parametrize("option_type", [OptionType.CALL, OptionType.PUT])
def test_option_type(option_type):
    chain = opt_type(data, option_type).option_type.unique()
    assert len(chain) == 1
    assert chain[0] == option_type.value[0]


def test_underlying_price():
    chain = underlying_price(data)
    assert 359.225 == chain


@pytest.mark.parametrize(
    "value",
    [
        ("strike", 357.5, [355, 360]),
        ("delta", 0.50, [0.5528, -0.4574, 0.5098, -0.4898]),
    ],
)
def test_nearest_column(value):
    # here we test for mid-point, values returned should round up.
    chain = nearest(data, value[0], value[1])
    assert all(v in value[2] for v in chain[value[0]].unique().tolist())


@pytest.mark.parametrize(
    "value",
    [
        ("strike", 350),
        ("delta", 0.50),
        ("expiration", "1990-01-21"),
        ("quote_date", "01-01-1990"),
    ],
)
def test_lte(value):
    values = lte(data, column=value[0], val=value[1])[value[0]]
    assert all(values <= value[1])


@pytest.mark.parametrize(
    "value",
    [
        ("strike", 350),
        ("delta", 0.50),
        ("expiration", "1990-01-21"),
        ("quote_date", "01-01-1990"),
    ],
)
def test_gte(value):
    values = gte(data, column=value[0], val=value[1])[value[0]]
    assert all(values >= value[1])


@pytest.mark.parametrize(
    "value",
    [
        ("strike", 350),
        ("delta", 0.50),
        ("expiration", "1990-01-21"),
        ("quote_date", "01-01-1990"),
    ],
)
def test_ge(value):
    values = gt(data, column=value[0], val=value[1])[value[0]]
    assert all(values > value[1])


@pytest.mark.parametrize(
    "value",
    [
        ("strike", 350),
        ("delta", 0.50),
        ("expiration", "1990-01-20"),
        ("quote_date", "01-01-1990"),
    ],
)
def test_eq(value):
    values = eq(data, column=value[0], val=value[1])[value[0]]
    assert all(values == value[1])


@pytest.mark.parametrize(
    "value",
    [
        ("strike", 350),
        ("delta", 0.50),
        ("expiration", "1990-01-21"),
        ("quote_date", "01-01-1990"),
    ],
)
def test_lt(value):
    values = lt(data, column=value[0], val=value[1])[value[0]]
    assert all(values < value[1])


@pytest.mark.parametrize(
    "value",
    [
        ("strike", 350),
        ("delta", 0.50),
        ("expiration", "1990-01-21"),
        ("quote_date", "01-01-1990"),
    ],
)
def test_ne(value):
    values = ne(data, column=value[0], val=value[1])[value[0]]
    assert all(values != value[1])


@pytest.mark.parametrize(
    "value",
    [
        ("strike", 350, 370),
        ("delta", 0.5, -0.5),
        ("expiration", "1990-01-20", "1990-01-21"),
        ("quote_date", "01-01-1990", "01-04-1990"),
    ],
)
def test_between_inclusive(value):
    values = between(data, column=value[0], start=value[1], end=value[2])[value[0]]
    assert all(values.between(value[1], value[2]))


@pytest.mark.parametrize(
    "value",
    [
        ("strike", 350, 370),
        ("delta", 0.5, -0.5),
        ("expiration", "1990-01-20", "1990-01-21"),
        ("quote_date", "01-01-1990", "01-04-1990"),
    ],
)
def test_between(value):
    values = between(
        data, column=value[0], start=value[1], end=value[2], inclusive=False
    )[value[0]]
    assert all(values.between(value[1], value[2], inclusive=False))
