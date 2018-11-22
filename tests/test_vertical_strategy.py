from optopsy.enums import OrderAction
from optopsy.option_strategies import (
    long_call_spread,
    short_call_spread,
    long_put_spread,
    short_put_spread,
)
from datetime import datetime
import pytest


start = datetime(1990, 1, 20)
end = datetime(1990, 1, 20)


call_params = {
    "leg1_delta": (0.45, 0.50, 0.55),
    "leg2_delta": (0.25, 0.30, 0.45),
    "entry_dte": (18, 18, 18),
}

put_params = {
    "leg1_delta": (0.25, 0.30, 0.45),
    "leg2_delta": (0.45, 0.50, 0.55),
    "entry_dte": (18, 18, 18),
}


def test_long_call_spread(options_data):
    actual_spread = long_call_spread(options_data, start, end, call_params)
    print(actual_spread)
    assert all(actual_spread["option_type"] == "c")
    assert (
        actual_spread.iat[0, 3] == 1
        and actual_spread.iat[0, 5] == 360
        and actual_spread.iat[0, 9] == 0.55
    )
    assert (
        actual_spread.iat[1, 3] == -1
        and actual_spread.iat[0, 5] == 360
        and actual_spread.iat[1, 9] == 0.35
    )


def test_invalid_long_call_spread(options_data):
    with pytest.raises(ValueError):
        long_call_spread(options_data, start, end, put_params)


def test_short_call_spread(options_data):
    actual_spread = short_call_spread(options_data, start, end, call_params)
    print(actual_spread)
    assert all(actual_spread["option_type"] == "c")
    assert (
        actual_spread.iat[0, 3] == -1
        and actual_spread.iat[0, 5] == 360
        and actual_spread.iat[0, 9] == 0.55
    )
    assert (
        actual_spread.iat[1, 3] == 1
        and actual_spread.iat[1, 5] == 365
        and actual_spread.iat[1, 9] == 0.35
    )


def test_invalid_short_call_spread(options_data):
    with pytest.raises(ValueError):
        short_call_spread(options_data, start, end, put_params)


def test_long_put_spread(options_data):
    actual_spread = long_put_spread(options_data, start, end, put_params)
    print(actual_spread)
    assert all(actual_spread["option_type"] == "p")
    assert (
        actual_spread.iat[0, 3] == -1
        and actual_spread.iat[0, 5] == 355
        and actual_spread.iat[0, 9] == -0.31
    )
    assert (
        actual_spread.iat[1, 3] == 1
        and actual_spread.iat[1, 5] == 360
        and actual_spread.iat[1, 9] == -0.46
    )


def test_invalid_long_put_spread(options_data):
    with pytest.raises(ValueError):
        long_put_spread(options_data, start, end, call_params)


def test_short_put_spread(options_data):
    actual_spread = short_put_spread(options_data, start, end, put_params)
    print(actual_spread)
    assert all(actual_spread["option_type"] == "p")
    assert (
        actual_spread.iat[0, 3] == 1
        and actual_spread.iat[0, 5] == 355
        and actual_spread.iat[0, 9] == -0.31
    )
    assert (
        actual_spread.iat[1, 3] == -1
        and actual_spread.iat[1, 5] == 360
        and actual_spread.iat[1, 9] == -0.46
    )


def test_invalid_short_put_spread(options_data):
    with pytest.raises(ValueError):
        short_put_spread(options_data, start, end, call_params)
