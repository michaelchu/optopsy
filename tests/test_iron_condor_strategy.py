from optopsy.enums import OrderAction
from optopsy.option_strategies import long_iron_condor, short_iron_condor
from datetime import datetime
import pytest


start = datetime(1990, 1, 20)
end = datetime(1990, 1, 20)


params_butterfly = {
    "leg1_delta": (0.25, 0.30, 0.45),
    "leg2_delta": (0.45, 0.50, 0.55),
    "leg3_delta": (0.45, 0.50, 0.55),
    "leg4_delta": (0.25, 0.30, 0.45),
    "entry_dte": (18, 18, 18),
}

params = {
    "leg1_delta": (0.05, 0.10, 0.15),
    "leg2_delta": (0.25, 0.30, 0.45),
    "leg3_delta": (0.25, 0.30, 0.45),
    "leg4_delta": (0.05, 0.10, 0.15),
    "entry_dte": (18, 18, 18),
}

params_float = {
    "leg1_delta": 0.10,
    "leg2_delta": 0.30,
    "leg3_delta": 0.30,
    "leg4_delta": 0.10,
    "entry_dte": 18,
}

invalid_params = {
    "leg1_delta": (0.05, 0.30, 0.15),
    "leg2_delta": (0.25, 0.10, 0.45),
    "leg3_delta": (0.25, 0.10, 0.45),
    "leg4_delta": (0.05, 0.30, 0.15),
    "entry_dte": (18, 18, 18),
}

invalid_params_2 = {
    "leg1_delta": (0.05, 0.10, 0.15),
    "leg2_delta": (0.25, 0.30, 0.45),
    "leg3_delta": (0.25, 0.10, 0.45),
    "leg4_delta": (0.05, 0.30, 0.15),
    "entry_dte": (18, 18, 18),
}

invalid_params_3 = {
    "leg1_delta": (0.05, 0.30, 0.15),
    "leg2_delta": (0.25, 0.10, 0.45),
    "leg3_delta": (0.25, 0.30, 0.45),
    "leg4_delta": (0.05, 0.10, 0.15),
    "entry_dte": (18, 18, 18),
}

invalid_params_4 = {
    "leg1_delta": datetime(2016, 1, 31),
    "leg2_delta": (0.25, 0.10, 0.45),
    "leg3_delta": (0.25, 0.30, 0.45),
    "leg4_delta": (0.05, 0.10, 0.15),
    "entry_dte": "(18, 18, 18)",
}


def test_long_iron_condor_spread(options_data):
    actual_spread = long_iron_condor(options_data, start, end, params)
    print(actual_spread)
    assert (
        actual_spread.iat[0, 3] == 1
        and actual_spread.iat[0, 5] == 340
        and actual_spread.iat[0, 9] == -0.09
        and actual_spread.iat[0, 4] == "p"
    )
    assert (
        actual_spread.iat[1, 3] == -1
        and actual_spread.iat[1, 5] == 355
        and actual_spread.iat[1, 9] == -0.31
        and actual_spread.iat[1, 4] == "p"
    )
    assert (
        actual_spread.iat[2, 3] == -1
        and actual_spread.iat[2, 5] == 365
        and actual_spread.iat[2, 9] == 0.35
        and actual_spread.iat[2, 4] == "c"
    )
    assert (
        actual_spread.iat[3, 3] == 1
        and actual_spread.iat[3, 5] == 375
        and actual_spread.iat[3, 9] == 0.10
        and actual_spread.iat[3, 4] == "c"
    )


def test_short_iron_condor_spread(options_data):
    actual_spread = short_iron_condor(options_data, start, end, params)
    print(actual_spread)
    assert (
        actual_spread.iat[0, 3] == -1
        and actual_spread.iat[0, 5] == 340
        and actual_spread.iat[0, 9] == -0.09
        and actual_spread.iat[0, 4] == "p"
    )
    assert (
        actual_spread.iat[1, 3] == 1
        and actual_spread.iat[1, 5] == 355
        and actual_spread.iat[1, 9] == -0.31
        and actual_spread.iat[1, 4] == "p"
    )
    assert (
        actual_spread.iat[2, 3] == 1
        and actual_spread.iat[2, 5] == 365
        and actual_spread.iat[2, 9] == 0.35
        and actual_spread.iat[2, 4] == "c"
    )
    assert (
        actual_spread.iat[3, 3] == -1
        and actual_spread.iat[3, 5] == 375
        and actual_spread.iat[3, 9] == 0.10
        and actual_spread.iat[3, 4] == "c"
    )


def test_same_middle_strikes(options_data):
    actual_spread = long_iron_condor(options_data, start, end, params_butterfly)
    print(actual_spread)
    assert actual_spread.empty == True


def test_float_params(options_data):
    actual_spread = long_iron_condor(options_data, start, end, params_float)
    print(actual_spread)
    assert (
        actual_spread.iat[0, 3] == 1
        and actual_spread.iat[0, 5] == 340
        and actual_spread.iat[0, 9] == -0.09
        and actual_spread.iat[0, 4] == "p"
    )
    assert (
        actual_spread.iat[1, 3] == -1
        and actual_spread.iat[1, 5] == 355
        and actual_spread.iat[1, 9] == -0.31
        and actual_spread.iat[1, 4] == "p"
    )
    assert (
        actual_spread.iat[2, 3] == -1
        and actual_spread.iat[2, 5] == 365
        and actual_spread.iat[2, 9] == 0.35
        and actual_spread.iat[2, 4] == "c"
    )
    assert (
        actual_spread.iat[3, 3] == 1
        and actual_spread.iat[3, 5] == 375
        and actual_spread.iat[3, 9] == 0.10
        and actual_spread.iat[3, 4] == "c"
    )


def test_invalid_deltas(options_data):
    with pytest.raises(ValueError):
        actual_spread = long_iron_condor(options_data, start, end, invalid_params)
        print(actual_spread)


def test_invalid_deltas_2(options_data):
    with pytest.raises(ValueError):
        actual_spread = long_iron_condor(options_data, start, end, invalid_params_2)
        print(actual_spread)


def test_invalid_deltas_3(options_data):
    with pytest.raises(ValueError):
        actual_spread = long_iron_condor(options_data, start, end, invalid_params_3)
        print(actual_spread)


def test_invalid_deltas_4(options_data):
    with pytest.raises(ValueError):
        actual_spread = long_iron_condor(options_data, start, end, invalid_params_4)
        print(actual_spread)
