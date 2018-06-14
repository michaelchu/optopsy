import os
import optopsy as op
from .base import *
from datetime import date
import pytest


def test_calls():
    data = op.get(os.path.join(os.path.dirname(__file__), 'test_data', 'test_dod_a_daily.csv'),
                  start=date(2016, 1, 1),
                  end=date(2016, 1, 5),
                  struct=dod_struct,
                  prompt=False
                  )

    calls = op.OptionQuery(data).calls().fetch().option_type.unique()
    assert len(calls) == 1
    assert calls[0] == 'c'


def test_puts():
    data = op.get(os.path.join(os.path.dirname(__file__), 'test_data', 'test_dod_a_daily.csv'),
                  start=date(2016, 1, 1),
                  end=date(2016, 1, 5),
                  struct=dod_struct,
                  prompt=False
                  )

    puts = op.OptionQuery(data).puts().fetch().option_type.unique()
    assert len(puts) == 1
    assert puts[0] == 'p'


@pytest.mark.parametrize("option_type", [op.OptionType.CALL, op.OptionType.PUT])
def test_option_type(option_type):
    data = op.get(os.path.join(os.path.dirname(__file__), 'test_data', 'test_dod_a_daily.csv'),
                  start=date(2016, 1, 1),
                  end=date(2016, 1, 5),
                  struct=dod_struct,
                  prompt=False
                  )

    chain = op.OptionQuery(data).option_type(option_type).fetch().option_type.unique()
    assert len(chain) == 1
    assert chain[0] == option_type.value[0]




