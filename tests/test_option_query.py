from datetime import date

import pytest

from .base import *

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
