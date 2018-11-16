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


def _test_call_results(result):
    print(result)
    assert all(result["option_type"] == "c")
    assert all(v in [0.35, 0.55] for v in result["delta"].unique().tolist())
    assert result.shape == (2, 15)


def _test_put_results(result):
    print(result)
    assert all(result["option_type"] == "p")
    assert all(v in [-0.31, -0.46] for v in result["delta"].unique().tolist())
    assert result.shape == (2, 15)


def test_long_call_spread(options_data):
    actual_spread = long_call_spread(options_data, start, end, call_params)
    _test_call_results(actual_spread)


def test_invalid_long_call_spread(options_data):
    with pytest.raises(ValueError):
        long_call_spread(options_data, start, end, put_params)


def test_short_call_spread(options_data):
    actual_spread = short_call_spread(options_data, start, end, call_params)
    _test_call_results(actual_spread)


def test_invalid_short_call_spread(options_data):
    with pytest.raises(ValueError):
        short_call_spread(options_data, start, end, put_params)


def test_long_put_spread(options_data):
    actual_spread = long_put_spread(options_data, start, end, put_params)
    _test_put_results(actual_spread)


def test_invalid_long_put_spread(options_data):
    with pytest.raises(ValueError):
        long_put_spread(options_data, start, end, call_params)


def test_short_put_spread(options_data):
    actual_spread = short_put_spread(options_data, start, end, put_params)
    _test_put_results(actual_spread)


def test_invalid_short_put_spread(options_data):
    with pytest.raises(ValueError):
        short_put_spread(options_data, start, end, call_params)
