import pytest

import optopsy.checks as op


class TestCheckPositiveInteger:
    def test_rejects_negative(self):
        with pytest.raises(ValueError):
            op._check_positive_integer("some key", -1)

    def test_rejects_zero(self):
        with pytest.raises(ValueError):
            op._check_positive_integer("some key", 0)

    def test_rejects_float(self):
        with pytest.raises(ValueError):
            op._check_positive_integer("some key", 1.0)

    def test_accepts_positive(self):
        assert op._check_positive_integer("some key", 1) is None


class TestCheckPositiveIntegerInclusive:
    def test_rejects_negative(self):
        with pytest.raises(ValueError):
            op._check_positive_integer_inclusive("some key", -1)

    def test_rejects_float(self):
        with pytest.raises(ValueError):
            op._check_positive_integer_inclusive("some key", 1.0)

    def test_accepts_positive(self):
        assert op._check_positive_integer_inclusive("some key", 1) is None

    def test_accepts_zero(self):
        assert op._check_positive_integer_inclusive("some key", 0) is None


class TestCheckPositiveFloat:
    def test_rejects_negative(self):
        with pytest.raises(ValueError):
            op._check_positive_float("some key", -1.0)

    def test_rejects_zero(self):
        with pytest.raises(ValueError):
            op._check_positive_float("some key", 0.0)

    def test_rejects_int(self):
        with pytest.raises(ValueError):
            op._check_positive_float("some key", 1)

    def test_accepts_positive_float(self):
        assert op._check_positive_float("some key", 1.0) is None


class TestCheckSide:
    def test_rejects_invalid(self):
        with pytest.raises(ValueError):
            op._check_side("some key", "invalid")

    def test_accepts_short(self):
        assert op._check_side("some key", "short") is None

    def test_accepts_long(self):
        assert op._check_side("some key", "long") is None


class TestCheckBoolType:
    def test_rejects_string(self):
        with pytest.raises(ValueError):
            op._check_bool_type("some key", "invalid")

    def test_rejects_int(self):
        with pytest.raises(ValueError):
            op._check_bool_type("some key", 1)

    def test_accepts_true(self):
        assert op._check_bool_type("some key", True) is None

    def test_accepts_false(self):
        assert op._check_bool_type("some key", False) is None


class TestCheckListType:
    def test_rejects_string(self):
        with pytest.raises(ValueError):
            op._check_list_type("some key", "invalid")

    def test_rejects_tuple(self):
        with pytest.raises(ValueError):
            op._check_list_type("some key", (1, 2))

    def test_accepts_empty_list(self):
        assert op._check_list_type("some key", []) is None

    def test_accepts_list(self):
        assert op._check_list_type("some key", [1, 2]) is None


class TestCheckOptionalFloat:
    def test_accepts_none(self):
        assert op._check_optional_float("some key", None) is None

    def test_accepts_float(self):
        assert op._check_optional_float("some key", 0.5) is None

    def test_accepts_int(self):
        assert op._check_optional_float("some key", 1) is None

    def test_rejects_string(self):
        with pytest.raises(ValueError):
            op._check_optional_float("some key", "invalid")


class TestCheckSlippage:
    def test_rejects_invalid(self):
        with pytest.raises(ValueError, match="must be 'mid', 'spread', or 'liquidity'"):
            op._check_slippage("some key", "invalid")

    def test_accepts_mid(self):
        assert op._check_slippage("some key", "mid") is None

    def test_accepts_spread(self):
        assert op._check_slippage("some key", "spread") is None

    def test_accepts_liquidity(self):
        assert op._check_slippage("some key", "liquidity") is None


class TestCheckFillRatio:
    def test_rejects_above_one(self):
        with pytest.raises(ValueError, match="between 0 and 1"):
            op._check_fill_ratio("some key", 1.5)

    def test_rejects_negative(self):
        with pytest.raises(ValueError, match="between 0 and 1"):
            op._check_fill_ratio("some key", -0.1)

    def test_rejects_string(self):
        with pytest.raises(ValueError, match="between 0 and 1"):
            op._check_fill_ratio("some key", "invalid")

    def test_accepts_zero(self):
        assert op._check_fill_ratio("some key", 0) is None

    def test_accepts_one(self):
        assert op._check_fill_ratio("some key", 1) is None

    def test_accepts_mid(self):
        assert op._check_fill_ratio("some key", 0.5) is None


class TestCheckDatesDataframe:
    def test_accepts_none(self):
        assert op._check_dates_dataframe("some key", None) is None

    def test_rejects_non_dataframe(self):
        with pytest.raises(ValueError, match="must be a DataFrame"):
            op._check_dates_dataframe("some key", "invalid")

    def test_rejects_missing_columns(self):
        import pandas as pd

        with pytest.raises(ValueError, match="missing required columns"):
            op._check_dates_dataframe("some key", pd.DataFrame({"foo": [1]}))

    def test_accepts_valid_dataframe(self):
        import pandas as pd

        df = pd.DataFrame({"underlying_symbol": ["SPX"], "quote_date": ["2024-01-01"]})
        assert op._check_dates_dataframe("some key", df) is None


class TestCheckDataTypes:
    def test_rejects_missing_column(self):
        import pandas as pd

        with pytest.raises(ValueError, match="Expected column"):
            op._check_data_types(pd.DataFrame({"some_col": ["some val"]}))

    def test_rejects_wrong_type(self):
        import pandas as pd

        with pytest.raises(
            ValueError, match="underlying_symbol does not match expected types"
        ):
            op._check_data_types(pd.DataFrame({"underlying_symbol": [123]}))


class TestCheckGreekColumn:
    def test_rejects_missing_delta(self):
        import pandas as pd

        with pytest.raises(ValueError, match="Greek column 'delta' not found"):
            op._check_greek_column(pd.DataFrame({"bid": [1.0]}), "delta")

    def test_rejects_wrong_type(self):
        import pandas as pd

        with pytest.raises(ValueError, match="does not match expected types"):
            op._check_greek_column(pd.DataFrame({"delta": ["string"]}), "delta")

    def test_accepts_valid_delta(self):
        import pandas as pd

        assert op._check_greek_column(pd.DataFrame({"delta": [0.5]}), "delta") is None


class TestCheckVolumeColumn:
    def test_rejects_missing_volume(self):
        import pandas as pd

        with pytest.raises(ValueError, match="volume.*not found"):
            op._check_volume_column(pd.DataFrame({"bid": [1.0]}))

    def test_rejects_wrong_type(self):
        import pandas as pd

        with pytest.raises(ValueError, match="does not match expected types"):
            op._check_volume_column(pd.DataFrame({"volume": ["string"]}))

    def test_accepts_valid_volume(self):
        import pandas as pd

        assert op._check_volume_column(pd.DataFrame({"volume": [100]})) is None
