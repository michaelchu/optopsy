from datetime import date

import pytest

import optopsy as op
from optopsy.enums import Period
from .base import data_factory, dod_struct, dod_struct_underlying, dod_struct_with_opt_sym_greeks

data = data_factory('test_dod_a_daily.csv', dod_struct_with_opt_sym_greeks, date(2016, 1, 1),
                    date(2016, 1, 5))


def test_option_query_init():
    with pytest.raises(ValueError):
        op.OptionQuery(op.Option())


def test_calls():
    calls = op.OptionQuery(data).calls().fetch().option_type.unique()
    assert len(calls) == 1
    assert calls[0] == 'c'


def test_puts():
    puts = op.OptionQuery(data).puts().fetch().option_type.unique()
    assert len(puts) == 1
    assert puts[0] == 'p'


@pytest.mark.parametrize('option_type', [2, 'x', 'invalid', (3, 4)])
def test_invalid_option_type(option_type):
    with pytest.raises(ValueError):
        op.OptionQuery(data).option_type(option_type)


@pytest.mark.parametrize("option_type", [op.OptionType.CALL, op.OptionType.PUT])
def test_option_type(option_type):
    chain = op.OptionQuery(data).option_type(option_type).fetch().option_type.unique()
    assert len(chain) == 1
    assert chain[0] == option_type.value[0]


def test_underlying_price():
    u_data = data_factory('test_dod_a_daily.csv', dod_struct_underlying, date(2016, 1, 1),
                          date(2016, 1, 5))
    chain = op.OptionQuery(u_data).underlying_price()
    assert chain == 40.55


def test_without_underlying_price():
    with pytest.raises(ValueError):
        op.OptionQuery(data).underlying_price()


@pytest.mark.parametrize("value", [('strike', 30, 30),
                                   ('strike', 30.625, 30),
                                   ('strike', 31.25, 32.5),
                                   ('strike', 31.625, 32.5),
                                   ('strike', 32.5, 32.5),
                                   ('delta', 1, 0.99),
                                   ('delta', -1, -1),
                                   ('delta', 0.50, 0.49)])
def test_nearest_column_round_up(value):
    # here we test for mid-point, values returned should round up.
    chain = op.OptionQuery(data).nearest(value[0], value[1]).fetch()
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
def test_nearest_column_round_down(value):
    # here we test for mid-point, values returned should round down.
    chain = op.OptionQuery(data).nearest(value[0], value[1], 'rounddown').fetch()
    values = chain[value[0]].unique()

    assert len(values) == 1
    assert values[0] == value[2]


@pytest.mark.parametrize("value", [('test', 1), (1234, 1), ('option_symbol', 'test')])
def test_invalid_column_values(value):
    with pytest.raises(ValueError):
        op.OptionQuery(data)._check_inputs(value[0], value[1])


@pytest.mark.parametrize("value", [('strike', 30),
                                   ('strike', 0),
                                   ('strike', 55),
                                   ('delta', 0),
                                   ('delta', 0.50),
                                   ('delta', 1),
                                   ('dte', Period.DAY.value),
                                   ('dte', Period.TWO_WEEKS.value),
                                   ('dte', Period.SEVEN_WEEKS.value)])
def test_lte(value):
    chain = op.OptionQuery(data).lte(value[0], value[1])
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
def test_gte(value):
    chain = op.OptionQuery(data).gte(value[0], value[1])
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
def test_eq(value):
    chain = op.OptionQuery(data).eq(value[0], value[1])
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
def test_lt(value):
    chain = op.OptionQuery(data).lt(value[0], value[1])
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
def test_ne(value):
    chain = op.OptionQuery(data).ne(value[0], value[1])
    values = chain.oc[value[0]].unique()
    assert all(v != value[1] for v in values)