import pandas as pd
import pytest

from optopsy.enums import Period


# Struts for testing purposes --------------------------------------------
@pytest.fixture
def valid_struct():
    return (
        ('underlying_symbol', 0),
        ('underlying_price', 1),
        ('root', 2),
        ('option_type', 4),
        ('expiration', 5),
        ('quote_date', 6),
        ('strike', 7),
        ('bid', 9),
        ('ask', 10),
        ('volume', 11),
        ('open_interest', 12),
        ('implied_vol', 14),
        ('delta', 17),
        ('gamma', 18),
        ('theta', 19),
        ('vega', 20)
    )


@pytest.fixture
def invalid_idx():
    return (
        ('symbol', -1),
        ('quote_date', -2)
    )


@pytest.fixture
def invalid_fields():
    return (
        ('symbol', 0),
        ('invalid', 1)
    )


@pytest.fixture
def invalid_struct():
    return (
        ('option_type', 4),
        ('expiration', 5),
        ('quote_date', 5),
        ('strike', 7),
        ('bid', 9),
        ('ask', 10)
    )


@pytest.fixture
def cboe_struct():
    return (
        ('underlying_symbol', 0),
        ('quote_date', 1),
        ('root', 2),
        ('expiration', 3),
        ('strike', 4),
        ('option_type', 5),
        ('bid', 12),
        ('ask', 14),
        ('underlying_price', 17),
        ('delta', 19),
        ('gamma', 20),
        ('theta', 21),
        ('vega', 22)
    )

