from datetime import date

import pytest

import optopsy as op
from .base import data_factory, dod_struct, dod_struct_underlying

data = data_factory('test_dod_a_daily.csv', dod_struct, date(2016, 1, 1), date(2016, 1, 5))

def test_calls():
    calls = op.OptionQuery(data).calls().fetch().option_type.unique()
    assert len(calls) == 1
    assert calls[0] == 'c'


def test_puts():
    puts = op.OptionQuery(data).puts().fetch().option_type.unique()
    assert len(puts) == 1
    assert puts[0] == 'p'


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


@pytest.mark.parametrize("value", [(30, 30), (30.625, 30), (31.25, 32.5),
                                   (31.625, 32.5), (32.5, 32.5)])
def test_nearest_column_round_up(value):
    # here we test for mid-point, values returned should round up.
    chain = op.OptionQuery(data).nearest('strike', value[0]).fetch().strike.unique()
    assert len(chain) == 1
    assert chain[0] == value[1]


@pytest.mark.parametrize("value", [(30, 30), (30.625, 30), (31.25, 30),
                                   (31.625, 32.5), (32.5, 32.5)])
def test_nearest_column_round_down(value):
    # here we test for mid-point, values returned should round down.
    chain = op.OptionQuery(data).nearest('strike', value[0], 'rounddown').fetch().strike.unique()
    assert len(chain) == 1
    assert chain[0] == value[1]


def test_nearest_invalid_column():
    with pytest.raises(ValueError):
        op.OptionQuery(data).nearest('option_type', 1)


# @pytest.mark.parametrize("value",[])
# def test_offset():
#     pass
