import pytest

import optopsy as op
from optopsy.enums import Period


def test_option_query_init():
    with pytest.raises(ValueError):
        op.OptionQuery(op.OptionStrategy())


def test_calls(data_dod_greeks):
    calls = op.OptionQuery(data_dod_greeks).calls().fetch().option_type.unique()
    assert len(calls) == 1
    assert calls[0] == 'c'


def test_puts(data_dod_greeks):
    puts = op.OptionQuery(data_dod_greeks).puts().fetch().option_type.unique()
    assert len(puts) == 1
    assert puts[0] == 'p'


@pytest.mark.parametrize('option_type', [2, 'x', 'invalid', (3, 4)])
def test_invalid_option_type(data_dod_greeks, option_type):
    with pytest.raises(ValueError):
        op.OptionQuery(data_dod_greeks).option_type(option_type)


@pytest.mark.parametrize("option_type", [op.OptionType.CALL, op.OptionType.PUT])
def test_option_type(data_dod_greeks, option_type):
    chain = op.OptionQuery(data_dod_greeks).option_type(option_type).fetch().option_type.unique()
    assert len(chain) == 1
    assert chain[0] == option_type.value[0]


def test_underlying_price(data_dod_underlying):
    chain = op.OptionQuery(data_dod_underlying).underlying_price()
    assert chain == 40.55


def test_without_underlying_price(data_dod_greeks):
    with pytest.raises(ValueError):
        op.OptionQuery(data_dod_greeks).underlying_price()


@pytest.mark.parametrize("value", [('strike', 30, 30),
                                   ('strike', 30.625, 30),
                                   ('strike', 31.25, 32.5),
                                   ('strike', 31.625, 32.5),
                                   ('strike', 32.5, 32.5),
                                   ('delta', 1, 0.99),
                                   ('delta', -1, -1),
                                   ('delta', 0.50, 0.49)])
def test_nearest_column_round_up(data_dod_greeks, value):
    # here we test for mid-point, values returned should round up.
    chain = op.OptionQuery(data_dod_greeks).nearest(value[0], value[1]).fetch()
    values = chain[value[0]].unique()

    assert len(values) == 1
    assert values[0] == value[2]


@pytest.mark.parametrize("value", [('strike', 30, 30),
                                   ('strike', 30.625, 30),
                                   ('strike', 31.25, 30),
                                   ('strike', 31.625, 32.5),
                                   ('strike', 32.5, 32.5),
                                   ('delta', 1, 0.99),
                                   ('delta', -1, -1),
                                   ('delta', 0.50, 0.49)])
def test_nearest_column_round_down(data_dod_greeks, value):
    # here we test for mid-point, values returned should round down.
    chain = op.OptionQuery(data_dod_greeks).nearest(value[0], value[1], 'rounddown').fetch()
    values = chain[value[0]].unique()

    assert len(values) == 1
    assert values[0] == value[2]


@pytest.mark.parametrize("value", [('test', 1), (1234, 1), ('option_symbol', 'test')])
def test_invalid_column_values(data_dod_greeks, value):
    with pytest.raises(ValueError):
        op.OptionQuery(data_dod_greeks)._check_inputs(value[0], value[1])


@pytest.mark.parametrize("value", [('strike', 30),
                                   ('strike', 0),
                                   ('strike', 55),
                                   ('delta', 0),
                                   ('delta', 0.50),
                                   ('delta', 1),
                                   ('dte', Period.DAY.value),
                                   ('dte', Period.TWO_WEEKS.value),
                                   ('dte', Period.SEVEN_WEEKS.value)])
def test_lte(data_dod_greeks, value):
    chain = op.OptionQuery(data_dod_greeks).lte(value[0], value[1])
    values = chain.oc[value[0]].unique()
    assert all(v <= value[1] for v in values)


@pytest.mark.parametrize("value", [('strike', 30),
                                   ('strike', 0),
                                   ('strike', 55),
                                   ('delta', 0),
                                   ('delta', 0.50),
                                   ('delta', 1),
                                   ('dte', Period.DAY.value),
                                   ('dte', Period.TWO_WEEKS.value),
                                   ('dte', Period.SEVEN_WEEKS.value)])
def test_gte(data_dod_greeks, value):
    chain = op.OptionQuery(data_dod_greeks).gte(value[0], value[1])
    values = chain.oc[value[0]].unique()
    assert all(v >= value[1] for v in values)


@pytest.mark.parametrize("value", [('strike', 30),
                                   ('strike', 0),
                                   ('strike', 55),
                                   ('delta', 0),
                                   ('delta', 0.54),
                                   ('delta', 1),
                                   ('dte', Period.DAY.value),
                                   ('dte', Period.TWO_WEEKS.value),
                                   ('dte', Period.SEVEN_WEEKS.value)])
def test_eq(data_dod_greeks, value):
    chain = op.OptionQuery(data_dod_greeks).eq(value[0], value[1])
    values = chain.oc[value[0]].unique()
    assert all(v == value[1] for v in values)


@pytest.mark.parametrize("value", [('strike', 30),
                                   ('strike', 0),
                                   ('strike', 55),
                                   ('delta', 0),
                                   ('delta', 0.54),
                                   ('delta', 1),
                                   ('dte', Period.DAY.value),
                                   ('dte', Period.TWO_WEEKS.value),
                                   ('dte', Period.SEVEN_WEEKS.value)])
def test_lt(data_dod_greeks, value):
    chain = op.OptionQuery(data_dod_greeks).lt(value[0], value[1])
    values = chain.oc[value[0]].unique()
    assert all(v < value[1] for v in values)


@pytest.mark.parametrize("value", [('strike', 30),
                                   ('strike', 0),
                                   ('strike', 55),
                                   ('delta', 0),
                                   ('delta', 0.54),
                                   ('delta', 1),
                                   ('dte', Period.DAY.value),
                                   ('dte', Period.TWO_WEEKS.value),
                                   ('dte', Period.SEVEN_WEEKS.value)])
def test_ne(data_dod_greeks, value):
    chain = op.OptionQuery(data_dod_greeks).ne(value[0], value[1])
    values = chain.oc[value[0]].unique()
    assert all(v != value[1] for v in values)


@pytest.mark.parametrize("value", [('strike', 30, 35),
                                   ('strike', 0, 20),
                                   ('strike', 55, 70),
                                   ('delta', 0.4, 0.6),
                                   ('delta', 0, 0.10),
                                   ('delta', 1, 1.10),
                                   ('dte', Period.DAY.value, Period.ONE_WEEK.value),
                                   ('dte', Period.TWO_WEEKS.value, Period.THREE_WEEKS.value)
                                   ])
def test_between(data_dod_greeks, value):
    chain = op.OptionQuery(data_dod_greeks).between(value[0], value[1], value[2])
    values = chain.oc[value[0]].unique()
    assert all(value[1] <= v <= value[2] for v in values)
