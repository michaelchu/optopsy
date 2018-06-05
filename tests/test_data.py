from datetime import date

import pandas as pd
import pytest

import optopsy as op


def test_invalid_fields():
    invalid = (
        ('symbol', -1),
        ('invalid', -1)
    )

    with pytest.raises(ValueError):
        data = op.get('../data/A.csv',
                      start=date(2016, 1, 1),
                      end=date(2016, 12, 31),
                      struct=invalid
                      )


def test_valid_fields():
    valid = (
        ('symbol', 0),
        ('quote_date', 1)
    )

    try:
        data = op.get('../data/tests/test_dod_a.csv',
                      start=date(2016, 1, 1),
                      end=date(2016, 12, 31),
                      struct=valid
                      )
    except ValueError:
        pytest.fail('ValueError raised')


def test_data_import():
    # struct for CBOE data
    struct = (
        ('symbol', 0),
        ('quote_date', 1),
        ('root', 2),
        ('expiration', 3),
        ('strike', 4),
        ('option_type', 5),
        ('volume', 10),
        ('bid', 12),
        ('ask', 14),
        ('underlying_price', 17),
        ('iv', 18),
        ('delta', 19),
        ('gamma', 20),
        ('theta', 21),
        ('vega', 22),
        ('rho', 23),
        ('oi', 24)
    )

    names = (
        'symbol',
        'quote_date',
        'root',
        'expiration',
        'strike',
        'option_type',
        'volume',
        'bid',
        'ask',
        'underlying_price',
        'iv',
        'delta',
        'gamma',
        'theta',
        'vega',
        'rho',
        'oi'
    )

    idx = (0, 1, 2, 3, 4, 5, 10, 12, 14, 17, 18, 19, 20, 21, 22, 23, 24)

    # We import the data with our defined columns and indexes to check against the one returned by the get function.
    raw_import = pd.read_csv('../data/tests/test_cboe_spx.csv', parse_dates=True, names=names, usecols=idx,
                             skiprows=1)

    data = op.get('../data/tests/test_cboe_spx.csv',
                  start=date(2016, 1, 1),
                  end=date(2016, 12, 31),
                  struct=struct
                  )

    assert raw_import.equals(data)
