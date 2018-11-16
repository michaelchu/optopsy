from optopsy.enums import OrderAction
from optopsy.option_strategies import (
    long_call_spread,
    short_call_spread,
    long_put_spread,
    short_put_spread,
)
from datetime import datetime


start = datetime(1990, 1, 20)
end = datetime(1990, 1, 20)

params = {
    "leg1_delta": (0.25, 0.30, 0.45),
    "leg2_delta": (0.45, 0.50, 0.55),
    "entry_dte": (18, 18, 18),
}


def _test_call_results(result):
    assert all(result["option_type"] == "c")
    assert all(v in [0.35, 0.55] for v in result["delta"].unique().tolist())
    assert result.shape == (2, 15)


def _test_put_results(result):
    assert all(result["option_type"] == "p")
    assert all(v in [-0.31, -0.46] for v in result["delta"].unique().tolist())
    assert result.shape == (2, 15)


def test_long_call_spread(options_data):
    actual_spread = long_call_spread(options_data, start, end, params)
    _test_call_results(actual_spread)


def test_short_call_spread(options_data):
    actual_spread = short_call_spread(options_data, start, end, params)
    _test_call_results(actual_spread)


def test_long_put_spread(options_data):
    actual_spread = long_put_spread(options_data, start, end, params)
    _test_put_results(actual_spread)


def test_short_put_spread(options_data):
    actual_spread = short_put_spread(options_data, start, end, params)
    _test_put_results(actual_spread)
