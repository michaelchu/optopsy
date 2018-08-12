import pytest
import pandas as pd
from optopsy.option_query import *
from optopsy.option_strategy import long_call
from .data_fixtures import one_day_data


@pytest.fixture
def sample_chain():
    return (
        pd.DataFrame({
            'leg_1_quote_date': ['2016-01-05', '2016-01-06', '2016-01-07'],
            'leg_1_underlying_price': [40.55, 41.55, 42.00],
            'leg_1_strike': [20, 21, 23.50],
            'leg_1_delta': [0.02, 0.02, 0.02],
            'leg_1_dte': [10, 9, 8]
        }
        ).assign(
            leg_1_quote_date=lambda r: pd.to_datetime(
                r['leg_1_quote_date'],
                infer_datetime_format=True,
                format='%Y-%m-%d')
        )
    )


def test_calls(one_day_data):
    c = calls(one_day_data).option_type.unique()
    assert len(c) == 1
    assert c[0] == 'c'


def test_puts(one_day_data):
    p = puts(one_day_data).option_type.unique()
    assert len(p) == 1
    assert p[0] == 'p'


@pytest.mark.parametrize('option_type', [2, 'x', 'invalid', (3, 4)])
def test_invalid_option_type(one_day_data, option_type):
    with pytest.raises(ValueError):
        opt_type(one_day_data, option_type)


@pytest.mark.parametrize("option_type", [OptionType.CALL, OptionType.PUT])
def test_option_type(one_day_data, option_type):
    chain = opt_type(one_day_data, option_type).option_type.unique()
    assert len(chain) == 1
    assert chain[0] == option_type.value[0]


def test_underlying_price(one_day_data):
    chain = underlying_price(one_day_data)
    assert chain == 40.55


@pytest.mark.parametrize("value", [('strike', 20.5, 21), ('delta', 0.0, 0.02)])
def test_nearest_column_round_up(one_day_data, value):
    # here we test for mid-point, values returned should round up.
    chain = nearest(one_day_data, value[0], value[1])
    values = chain[value[0]].unique()

    assert len(values) == 1
    assert values[0] == value[2]


@pytest.mark.parametrize("value", [('strike', 20.5, 20), ('delta', 0.0, -0.02)])
def test_nearest_column_round_down(one_day_data, value):
    # here we test for mid-point, values returned should round down.
    chain = nearest(one_day_data, value[0], value[1], 'rounddown')
    values = chain[value[0]].unique()

    assert len(values) == 1
    assert values[0] == value[2]


@pytest.mark.parametrize(
    "value", [('test', 1), (1234, 1), ('option_symbol', 'test')])
def test_invalid_column_values(one_day_data, value):
    with pytest.raises(ValueError):
        nearest(one_day_data, value[0], value[1])


@pytest.mark.parametrize("value", [('leg_1_strike', 30),
                                   ('leg_1_strike', 0),
                                   ('leg_1_strike', 55),
                                   ('leg_1_delta', 0),
                                   ('leg_1_delta', 0.50),
                                   ('leg_1_delta', 1),
                                   ('leg_1_dte', Period.DAY.value),
                                   ('leg_1_dte', Period.TWO_WEEKS.value),
                                   ('leg_1_dte', Period.SEVEN_WEEKS.value)])
def test_lte(sample_chain, value):
    values = (sample_chain.pipe(lte, column=value[0], val=value[1]))[value[0]].unique()
    assert all(v <= value[1] for v in values)


@pytest.mark.parametrize("value", [('leg_1_strike', 30),
                                   ('leg_1_strike', 0),
                                   ('leg_1_strike', 55),
                                   ('leg_1_delta', 0),
                                   ('leg_1_delta', 0.50),
                                   ('leg_1_delta', 1),
                                   ('leg_1_dte', Period.DAY.value),
                                   ('leg_1_dte', Period.TWO_WEEKS.value),
                                   ('leg_1_dte', Period.SEVEN_WEEKS.value)])
def test_gte(sample_chain, value):
    values = (sample_chain.pipe(gte, column=value[0], val=value[1]))[value[0]].unique()
    assert all(v >= value[1] for v in values)


@pytest.mark.parametrize("value", [('leg_1_strike', 30),
                                   ('leg_1_strike', 0),
                                   ('leg_1_strike', 55),
                                   ('leg_1_delta', 0),
                                   ('leg_1_delta', 0.54),
                                   ('leg_1_delta', 1),
                                   ('leg_1_dte', Period.DAY.value),
                                   ('leg_1_dte', Period.TWO_WEEKS.value),
                                   ('leg_1_dte', Period.SEVEN_WEEKS.value)])
def test_eq(sample_chain, value):
    values = (sample_chain.pipe(eq, column=value[0], val=value[1]))[value[0]].unique()
    assert all(v == value[1] for v in values)


@pytest.mark.parametrize("value", [('leg_1_strike', 30),
                                   ('leg_1_strike', 0),
                                   ('leg_1_strike', 55),
                                   ('leg_1_delta', 0),
                                   ('leg_1_delta', 0.54),
                                   ('leg_1_delta', 1),
                                   ('leg_1_dte', Period.DAY.value),
                                   ('leg_1_dte', Period.TWO_WEEKS.value),
                                   ('leg_1_dte', Period.SEVEN_WEEKS.value)])
def test_lt(sample_chain, value):
    values = (sample_chain.pipe(eq, column=value[0], val=value[1]))[value[0]].unique()
    assert all(v < value[1] for v in values)


@pytest.mark.parametrize("value", [('leg_1_strike', 30),
                                   ('leg_1_strike', 0),
                                   ('leg_1_strike', 55),
                                   ('leg_1_delta', 0),
                                   ('leg_1_delta', 0.54),
                                   ('leg_1_delta', 1),
                                   ('leg_1_dte', Period.DAY.value),
                                   ('leg_1_dte', Period.TWO_WEEKS.value),
                                   ('leg_1_dte', Period.SEVEN_WEEKS.value)])
def test_ne(sample_chain, value):
    values = (sample_chain.pipe(eq, column=value[0], val=value[1]))[value[0]].unique()
    assert all(v != value[1] for v in values)


@pytest.mark.parametrize("value", [('leg_1_strike', 30, 35),
                                   ('leg_1_strike', 0, 20),
                                   ('leg_1_strike', 55, 70),
                                   ('leg_1_delta', 0.4, 0.6),
                                   ('leg_1_delta', 0, 0.10),
                                   ('leg_1_delta', 1, 1.10),
                                   ('leg_1_dte', Period.DAY.value, Period.ONE_WEEK.value),
                                   ('leg_1_dte', Period.TWO_WEEKS.value, Period.THREE_WEEKS.value)
                                   ])
def test_between(sample_chain, value):
    values = (sample_chain.pipe(eq, column=value[0], val=value[1]))[value[0]].unique()
    assert all(value[1] <= v <= value[2] for v in values)
