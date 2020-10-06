import pytest
import optopsy.checks as op


def test_check_positive_integer():
    with pytest.raises(ValueError):
        op._check_positive_integer("some key", -1)
        op._check_positive_integer("some key", 0)
        op._check_positive_integer("some key", 1.0)

    assert op._check_positive_integer("some key", 1) is None


def test_check_positive_integer_inclusive():
    with pytest.raises(ValueError):
        op._check_positive_integer_inclusive("some key", -1)
        op._check_positive_integer_inclusive("some key", 1.0)

    assert op._check_positive_integer_inclusive("some key", 1) is None
    assert op._check_positive_integer_inclusive("some key", 0) is None


def test_check_positive_float():
    with pytest.raises(ValueError):
        op._check_positive_float("some key", -1)
        op._check_positive_float("some key", 0)
        op._check_positive_float("some key", 1)

    assert op._check_positive_float("some key", 1.0) is None


def test_check_side():
    with pytest.raises(ValueError):
        op._check_side("some key", "invalid")

    assert op._check_side("some key", "short") is None
    assert op._check_side("some key", "long") is None


def test_check_bool_type():
    with pytest.raises(ValueError):
        op._check_bool_type("some key", "invalid")

    assert op._check_bool_type("some key", True) is None
    assert op._check_bool_type("some key", False) is None


def test_check_list_type():
    with pytest.raises(ValueError):
        op._check_list_type("some key", "invalid")

    assert op._check_list_type("some key", []) is None


def test_check_data_types():
    import pandas as pd

    invalid_cols = {"some_col": ["some val"]}
    invalid_types = {"underlying_symbol": [123]}

    with pytest.raises(ValueError, match="Expected column"):
        op._check_data_types(pd.DataFrame(invalid_cols))

    with pytest.raises(
        ValueError, match="underlying_symbol does not match expected types"
    ):
        op._check_data_types(pd.DataFrame(invalid_types))
