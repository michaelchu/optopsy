import os
from datetime import date

import pytest

import optopsy as op
from .base import dod_struct_with_opt_sym_greeks, dod_struct_underlying, dod_struct, hod_struct, \
    hod_struct_with_sym


@pytest.fixture(scope="session")
def data_dod():
    return op.get(os.path.join(os.path.dirname(__file__), 'test_data', 'test_dod_a_daily.csv'),
                  start=date(2016, 1, 1),
                  end=date(2016, 1, 5),
                  struct=dod_struct,
                  prompt=False
                  )


@pytest.fixture(scope="session")
def data_dod_greeks():
    return op.get(os.path.join(os.path.dirname(__file__), 'test_data', 'test_dod_a_daily.csv'),
                  start=date(2016, 1, 1),
                  end=date(2016, 1, 5),
                  struct=dod_struct_with_opt_sym_greeks,
                  prompt=False
                  )


@pytest.fixture(scope="session")
def data_dod_underlying():
    return op.get(os.path.join(os.path.dirname(__file__), 'test_data', 'test_dod_a_daily.csv'),
                  start=date(2016, 1, 1),
                  end=date(2016, 1, 5),
                  struct=dod_struct_underlying,
                  prompt=False
                  )


@pytest.fixture(scope="session")
def data_hod():
    return op.get(os.path.join(os.path.dirname(__file__), 'test_data', 'test_hod_vxx_daily.csv'),
                  start=date(2016, 12, 1),
                  end=date(2016, 12, 1),
                  struct=hod_struct,
                  prompt=False
                  )


@pytest.fixture(scope="session")
def data_hod_sym():
    return op.get(os.path.join(os.path.dirname(__file__), 'test_data', 'test_hod_vxx_daily.csv'),
                  start=date(2016, 12, 1),
                  end=date(2016, 12, 1),
                  struct=hod_struct_with_sym,
                  prompt=False
                  )


@pytest.fixture(scope="module", params=[
    (data_dod_greeks, op.OptionType.CALL, 0.5),
    (data_dod_greeks, op.OptionType.CALL, 2),
    (data_dod_greeks, op.OptionType.CALL, 4),
    (data_dod_greeks, op.OptionType.CALL, 10),
    (data_dod_greeks, op.OptionType.PUT, 0.5),
    (data_dod_greeks, op.OptionType.PUT, 2),
    (data_dod_greeks, op.OptionType.PUT, 4),
    (data_dod_greeks, op.OptionType.PUT, 10)
])
def vertical_strategies(request):
    data = op.option_strategy.Vertical(option_type=request.param[1],
                                       width=request.param[2])(request.param[0]())
    return op.OptionQuery(data)
