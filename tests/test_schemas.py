"""Tests for optopsy.ui.tools._schemas — SIGNAL_REGISTRY lambdas and _normalize_days_param."""

import pytest

pytest.importorskip("pyarrow", reason="UI extras not installed")

from optopsy.ui.tools._schemas import (
    SIGNAL_REGISTRY,
    _normalize_days_param,
)

# ---------------------------------------------------------------------------
# _normalize_days_param tests
# ---------------------------------------------------------------------------


class TestNormalizeDaysParam:
    def test_int_input(self):
        assert _normalize_days_param(3) == [3]

    def test_list_input(self):
        assert _normalize_days_param([0, 4]) == [0, 4]

    def test_single_element_list(self):
        assert _normalize_days_param([2]) == [2]

    def test_empty_list_raises(self):
        with pytest.raises(ValueError, match="empty"):
            _normalize_days_param([])

    def test_invalid_type_raises(self):
        with pytest.raises(TypeError, match="int or list"):
            _normalize_days_param("friday")

    def test_out_of_range_int_raises(self):
        with pytest.raises(ValueError, match="0-6"):
            _normalize_days_param(7)

    def test_negative_int_raises(self):
        with pytest.raises(ValueError, match="0-6"):
            _normalize_days_param(-1)

    def test_out_of_range_list_raises(self):
        with pytest.raises(ValueError, match="invalid values"):
            _normalize_days_param([0, 8])

    def test_non_int_in_list_raises(self):
        with pytest.raises(TypeError, match="integers"):
            _normalize_days_param([1, "two"])

    def test_boundary_values(self):
        assert _normalize_days_param(0) == [0]
        assert _normalize_days_param(6) == [6]

    def test_all_weekdays(self):
        result = _normalize_days_param([0, 1, 2, 3, 4])
        assert result == [0, 1, 2, 3, 4]


# ---------------------------------------------------------------------------
# SIGNAL_REGISTRY lambda tests
# ---------------------------------------------------------------------------


class TestSignalRegistryLambdas:
    """Each SIGNAL_REGISTRY lambda should be callable with defaults and custom params."""

    def test_all_signals_callable_with_defaults(self):
        """Every registry entry produces a callable with no arguments."""
        for name, factory in SIGNAL_REGISTRY.items():
            result = factory()
            assert callable(result), f"{name} factory did not return a callable"

    def test_rsi_below_defaults(self):
        sig = SIGNAL_REGISTRY["rsi_below"]()
        assert callable(sig)

    def test_rsi_below_custom(self):
        sig = SIGNAL_REGISTRY["rsi_below"](period=20, threshold=25)
        assert callable(sig)

    def test_rsi_above_defaults(self):
        sig = SIGNAL_REGISTRY["rsi_above"]()
        assert callable(sig)

    def test_rsi_above_custom(self):
        sig = SIGNAL_REGISTRY["rsi_above"](period=7, threshold=80)
        assert callable(sig)

    def test_sma_below_defaults(self):
        sig = SIGNAL_REGISTRY["sma_below"]()
        assert callable(sig)

    def test_sma_above_custom(self):
        sig = SIGNAL_REGISTRY["sma_above"](period=200)
        assert callable(sig)

    def test_macd_cross_above_defaults(self):
        sig = SIGNAL_REGISTRY["macd_cross_above"]()
        assert callable(sig)

    def test_macd_cross_below_custom(self):
        sig = SIGNAL_REGISTRY["macd_cross_below"](fast=8, slow=21, signal_period=5)
        assert callable(sig)

    def test_bb_above_upper_defaults(self):
        sig = SIGNAL_REGISTRY["bb_above_upper"]()
        assert callable(sig)

    def test_bb_below_lower_custom(self):
        sig = SIGNAL_REGISTRY["bb_below_lower"](length=30, std=2.5)
        assert callable(sig)

    def test_ema_cross_above_defaults(self):
        sig = SIGNAL_REGISTRY["ema_cross_above"]()
        assert callable(sig)

    def test_ema_cross_below_custom(self):
        sig = SIGNAL_REGISTRY["ema_cross_below"](fast=5, slow=20)
        assert callable(sig)

    def test_atr_above_defaults(self):
        sig = SIGNAL_REGISTRY["atr_above"]()
        assert callable(sig)

    def test_atr_below_custom(self):
        sig = SIGNAL_REGISTRY["atr_below"](period=20, multiplier=0.5)
        assert callable(sig)

    def test_day_of_week_defaults(self):
        """Default is Friday (day 4)."""
        sig = SIGNAL_REGISTRY["day_of_week"]()
        assert callable(sig)

    def test_day_of_week_custom_single_day(self):
        sig = SIGNAL_REGISTRY["day_of_week"](days=0)
        assert callable(sig)

    def test_day_of_week_custom_list(self):
        sig = SIGNAL_REGISTRY["day_of_week"](days=[1, 3])
        assert callable(sig)

    def test_iv_rank_above_defaults(self):
        sig = SIGNAL_REGISTRY["iv_rank_above"]()
        assert callable(sig)

    def test_iv_rank_below_custom(self):
        sig = SIGNAL_REGISTRY["iv_rank_below"](threshold=0.3, window=126)
        assert callable(sig)

    def test_partial_param_overrides(self):
        """Passing only some params uses defaults for the rest."""
        sig = SIGNAL_REGISTRY["rsi_below"](threshold=40)
        assert callable(sig)
        sig = SIGNAL_REGISTRY["macd_cross_above"](fast=8)
        assert callable(sig)
        sig = SIGNAL_REGISTRY["bb_above_upper"](std=3.0)
        assert callable(sig)
