"""Tests for Pydantic validation models in optopsy.types."""

import pandas as pd
import pytest
from pydantic import ValidationError

from optopsy.types import CalendarStrategyParams, SimulatorParams, StrategyParams


class TestStrategyParamsValidation:
    """Test StrategyParams Pydantic model validation."""

    def test_accepts_empty_params(self):
        model = StrategyParams.model_validate({})
        assert model.max_entry_dte is None

    def test_accepts_valid_params(self):
        model = StrategyParams.model_validate(
            {"max_entry_dte": 60, "exit_dte": 30, "raw": True}
        )
        assert model.max_entry_dte == 60
        assert model.exit_dte == 30
        assert model.raw is True

    def test_rejects_negative_max_entry_dte(self):
        with pytest.raises(ValidationError):
            StrategyParams.model_validate({"max_entry_dte": -1})

    def test_rejects_zero_max_entry_dte(self):
        with pytest.raises(ValidationError):
            StrategyParams.model_validate({"max_entry_dte": 0})

    def test_accepts_zero_exit_dte(self):
        model = StrategyParams.model_validate({"exit_dte": 0})
        assert model.exit_dte == 0

    def test_rejects_negative_exit_dte(self):
        with pytest.raises(ValidationError):
            StrategyParams.model_validate({"exit_dte": -1})

    def test_rejects_int_for_max_otm_pct(self):
        """max_otm_pct uses strict float — must reject int."""
        with pytest.raises(ValidationError):
            StrategyParams.model_validate({"max_otm_pct": 1})

    def test_accepts_float_for_max_otm_pct(self):
        model = StrategyParams.model_validate({"max_otm_pct": 0.5})
        assert model.max_otm_pct == 0.5

    def test_rejects_int_for_raw(self):
        """raw uses StrictBool — must reject int."""
        with pytest.raises(ValidationError):
            StrategyParams.model_validate({"raw": 1})

    def test_accepts_bool_for_raw(self):
        model = StrategyParams.model_validate({"raw": False})
        assert model.raw is False

    def test_rejects_int_for_drop_nan(self):
        with pytest.raises(ValidationError):
            StrategyParams.model_validate({"drop_nan": 0})

    def test_accepts_side_long(self):
        model = StrategyParams.model_validate({"side": "long"})
        assert model.side == "long"

    def test_accepts_side_short(self):
        model = StrategyParams.model_validate({"side": "short"})
        assert model.side == "short"

    def test_rejects_invalid_side(self):
        with pytest.raises(ValidationError):
            StrategyParams.model_validate({"side": "invalid"})

    def test_accepts_slippage_mid(self):
        model = StrategyParams.model_validate({"slippage": "mid"})
        assert model.slippage == "mid"

    def test_rejects_invalid_slippage(self):
        with pytest.raises(ValidationError):
            StrategyParams.model_validate({"slippage": "bad"})

    def test_fill_ratio_accepts_zero(self):
        model = StrategyParams.model_validate({"fill_ratio": 0})
        assert model.fill_ratio == 0

    def test_fill_ratio_accepts_one(self):
        model = StrategyParams.model_validate({"fill_ratio": 1})
        assert model.fill_ratio == 1

    def test_fill_ratio_rejects_above_one(self):
        with pytest.raises(ValidationError):
            StrategyParams.model_validate({"fill_ratio": 1.5})

    def test_fill_ratio_rejects_negative(self):
        with pytest.raises(ValidationError):
            StrategyParams.model_validate({"fill_ratio": -0.1})

    def test_ignores_unknown_params(self):
        model = StrategyParams.model_validate({"unknown_field": 42})
        assert not hasattr(model, "unknown_field") or model.model_extra == {}

    def test_all_none_values_accepted(self):
        params = {
            "max_entry_dte": None,
            "exit_dte": None,
            "max_otm_pct": None,
            "raw": None,
            "slippage": None,
        }
        model = StrategyParams.model_validate(params)
        assert model.max_entry_dte is None

    def test_accepts_int_for_delta_min(self):
        model = StrategyParams.model_validate({"delta_min": 1})
        assert model.delta_min == 1

    def test_accepts_float_for_delta_min(self):
        model = StrategyParams.model_validate({"delta_min": 0.3})
        assert model.delta_min == 0.3

    def test_rejects_string_for_delta_min(self):
        with pytest.raises(ValidationError):
            StrategyParams.model_validate({"delta_min": "bad"})


class TestStrategyParamsDatesValidation:
    """Test entry_dates/exit_dates DataFrame validation."""

    def test_accepts_none_for_entry_dates(self):
        model = StrategyParams.model_validate({"entry_dates": None})
        assert model.entry_dates is None

    def test_accepts_valid_dataframe(self):
        df = pd.DataFrame({"underlying_symbol": ["SPX"], "quote_date": ["2024-01-01"]})
        model = StrategyParams.model_validate({"entry_dates": df})
        assert model.entry_dates is not None

    def test_rejects_non_dataframe(self):
        with pytest.raises(ValidationError, match="must be a DataFrame"):
            StrategyParams.model_validate({"entry_dates": "invalid"})

    def test_rejects_missing_columns(self):
        with pytest.raises(ValidationError, match="missing required columns"):
            StrategyParams.model_validate({"entry_dates": pd.DataFrame({"foo": [1]})})


class TestCalendarStrategyParamsValidation:
    """Test CalendarStrategyParams cross-field validators."""

    def test_accepts_valid_dte_ranges(self):
        model = CalendarStrategyParams.model_validate(
            {
                "front_dte_min": 20,
                "front_dte_max": 40,
                "back_dte_min": 50,
                "back_dte_max": 80,
            }
        )
        assert model.front_dte_min == 20

    def test_rejects_front_dte_min_gt_max(self):
        with pytest.raises(
            ValidationError, match="front_dte_min.*must be <=.*front_dte_max"
        ):
            CalendarStrategyParams.model_validate(
                {
                    "front_dte_min": 50,
                    "front_dte_max": 20,
                    "back_dte_min": 60,
                    "back_dte_max": 90,
                }
            )

    def test_rejects_back_dte_min_gt_max(self):
        with pytest.raises(
            ValidationError, match="back_dte_min.*must be <=.*back_dte_max"
        ):
            CalendarStrategyParams.model_validate(
                {
                    "front_dte_min": 20,
                    "front_dte_max": 40,
                    "back_dte_min": 90,
                    "back_dte_max": 60,
                }
            )

    def test_rejects_overlapping_ranges(self):
        with pytest.raises(
            ValidationError, match="front_dte_max.*must be <.*back_dte_min"
        ):
            CalendarStrategyParams.model_validate(
                {
                    "front_dte_min": 20,
                    "front_dte_max": 60,
                    "back_dte_min": 50,
                    "back_dte_max": 80,
                }
            )

    def test_rejects_adjacent_ranges(self):
        with pytest.raises(
            ValidationError, match="front_dte_max.*must be <.*back_dte_min"
        ):
            CalendarStrategyParams.model_validate(
                {
                    "front_dte_min": 20,
                    "front_dte_max": 50,
                    "back_dte_min": 50,
                    "back_dte_max": 80,
                }
            )

    def test_inherits_base_validation(self):
        """Calendar params should also validate base StrategyParams fields."""
        with pytest.raises(ValidationError):
            CalendarStrategyParams.model_validate({"max_entry_dte": -1})


class TestSimulatorParamsValidation:
    """Test SimulatorParams Pydantic model validation."""

    def test_accepts_valid_params(self):
        model = SimulatorParams(
            capital=10000, quantity=1, max_positions=5, multiplier=100
        )
        assert model.capital == 10000

    def test_rejects_negative_capital(self):
        with pytest.raises(ValidationError):
            SimulatorParams(capital=-1, quantity=1, max_positions=5, multiplier=100)

    def test_rejects_zero_quantity(self):
        with pytest.raises(ValidationError):
            SimulatorParams(capital=10000, quantity=0, max_positions=5, multiplier=100)

    def test_accepts_float_capital(self):
        model = SimulatorParams(
            capital=10000.5, quantity=1, max_positions=5, multiplier=100
        )
        assert model.capital == 10000.5

    def test_rejects_float_quantity(self):
        with pytest.raises(ValidationError):
            SimulatorParams(
                capital=10000, quantity=1.5, max_positions=5, multiplier=100
            )
