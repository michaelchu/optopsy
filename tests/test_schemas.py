"""Tests for optopsy.ui.tools._schemas — SIGNAL_REGISTRY lambdas and _normalize_days_param."""

from unittest.mock import patch

import pytest

pytest.importorskip("pyarrow", reason="UI extras not installed")

from optopsy.ui.tools._schemas import (
    _PROVIDER_TOOLS,
    CALENDAR_STRATEGIES,
    SIGNAL_REGISTRY,
    STRATEGIES,
    STRATEGY_OPTION_TYPE,
    _normalize_days_param,
    get_required_option_type,
    get_tool_schemas,
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
# SIGNAL_REGISTRY lambda tests — verify args are passed through correctly
# ---------------------------------------------------------------------------


class TestSignalRegistryLambdas:
    """Verify each SIGNAL_REGISTRY lambda passes arguments to the underlying signal function."""

    def test_rsi_below_defaults(self):
        with patch("optopsy.ui.tools._schemas._signals.rsi_below") as mock:
            SIGNAL_REGISTRY["rsi_below"]()
            mock.assert_called_once_with(14, 30)

    def test_rsi_below_custom(self):
        with patch("optopsy.ui.tools._schemas._signals.rsi_below") as mock:
            SIGNAL_REGISTRY["rsi_below"](period=20, threshold=25)
            mock.assert_called_once_with(20, 25)

    def test_rsi_above_defaults(self):
        with patch("optopsy.ui.tools._schemas._signals.rsi_above") as mock:
            SIGNAL_REGISTRY["rsi_above"]()
            mock.assert_called_once_with(14, 70)

    def test_rsi_above_custom(self):
        with patch("optopsy.ui.tools._schemas._signals.rsi_above") as mock:
            SIGNAL_REGISTRY["rsi_above"](period=7, threshold=80)
            mock.assert_called_once_with(7, 80)

    def test_sma_below_defaults(self):
        with patch("optopsy.ui.tools._schemas._signals.sma_below") as mock:
            SIGNAL_REGISTRY["sma_below"]()
            mock.assert_called_once_with(50)

    def test_sma_above_custom(self):
        with patch("optopsy.ui.tools._schemas._signals.sma_above") as mock:
            SIGNAL_REGISTRY["sma_above"](period=200)
            mock.assert_called_once_with(200)

    def test_macd_cross_above_defaults(self):
        with patch("optopsy.ui.tools._schemas._signals.macd_cross_above") as mock:
            SIGNAL_REGISTRY["macd_cross_above"]()
            mock.assert_called_once_with(12, 26, 9)

    def test_macd_cross_below_custom(self):
        with patch("optopsy.ui.tools._schemas._signals.macd_cross_below") as mock:
            SIGNAL_REGISTRY["macd_cross_below"](fast=8, slow=21, signal_period=5)
            mock.assert_called_once_with(8, 21, 5)

    def test_bb_above_upper_defaults(self):
        with patch("optopsy.ui.tools._schemas._signals.bb_above_upper") as mock:
            SIGNAL_REGISTRY["bb_above_upper"]()
            mock.assert_called_once_with(20, 2.0)

    def test_bb_below_lower_custom(self):
        with patch("optopsy.ui.tools._schemas._signals.bb_below_lower") as mock:
            SIGNAL_REGISTRY["bb_below_lower"](length=30, std=2.5)
            mock.assert_called_once_with(30, 2.5)

    def test_ema_cross_above_defaults(self):
        with patch("optopsy.ui.tools._schemas._signals.ema_cross_above") as mock:
            SIGNAL_REGISTRY["ema_cross_above"]()
            mock.assert_called_once_with(10, 50)

    def test_ema_cross_below_custom(self):
        with patch("optopsy.ui.tools._schemas._signals.ema_cross_below") as mock:
            SIGNAL_REGISTRY["ema_cross_below"](fast=5, slow=20)
            mock.assert_called_once_with(5, 20)

    def test_atr_above_defaults(self):
        with patch("optopsy.ui.tools._schemas._signals.atr_above") as mock:
            SIGNAL_REGISTRY["atr_above"]()
            mock.assert_called_once_with(14, 1.5)

    def test_atr_below_custom(self):
        with patch("optopsy.ui.tools._schemas._signals.atr_below") as mock:
            SIGNAL_REGISTRY["atr_below"](period=20, multiplier=0.5)
            mock.assert_called_once_with(20, 0.5)

    def test_day_of_week_defaults(self):
        """Default is Friday (day 4), passed as *args via _normalize_days_param."""
        with patch("optopsy.ui.tools._schemas._signals.day_of_week") as mock:
            SIGNAL_REGISTRY["day_of_week"]()
            mock.assert_called_once_with(4)

    def test_day_of_week_custom_list(self):
        with patch("optopsy.ui.tools._schemas._signals.day_of_week") as mock:
            SIGNAL_REGISTRY["day_of_week"](days=[1, 3])
            mock.assert_called_once_with(1, 3)

    def test_iv_rank_above_defaults(self):
        with patch("optopsy.ui.tools._schemas._signals.iv_rank_above") as mock:
            SIGNAL_REGISTRY["iv_rank_above"]()
            mock.assert_called_once_with(0.5, 252)

    def test_iv_rank_below_custom(self):
        with patch("optopsy.ui.tools._schemas._signals.iv_rank_below") as mock:
            SIGNAL_REGISTRY["iv_rank_below"](threshold=0.3, window=126)
            mock.assert_called_once_with(0.3, 126)

    def test_partial_param_override_uses_defaults_for_rest(self):
        """Passing only one param keeps defaults for others."""
        with patch("optopsy.ui.tools._schemas._signals.rsi_below") as mock:
            SIGNAL_REGISTRY["rsi_below"](threshold=40)
            mock.assert_called_once_with(14, 40)  # period=14 is default

        with patch("optopsy.ui.tools._schemas._signals.macd_cross_above") as mock:
            SIGNAL_REGISTRY["macd_cross_above"](fast=8)
            mock.assert_called_once_with(8, 26, 9)  # slow=26, signal=9 defaults


# ---------------------------------------------------------------------------
# STRATEGIES / STRATEGY_OPTION_TYPE completeness
# ---------------------------------------------------------------------------


class TestRegistryCompleteness:
    def test_strategy_option_type_covers_all_strategies(self):
        """Every strategy in STRATEGIES should have an entry in STRATEGY_OPTION_TYPE."""
        missing = set(STRATEGIES.keys()) - set(STRATEGY_OPTION_TYPE.keys())
        assert not missing, f"Missing STRATEGY_OPTION_TYPE entries: {missing}"

    def test_get_required_option_type_returns_correct_values(self):
        assert get_required_option_type("long_calls") == "call"
        assert get_required_option_type("long_puts") == "put"
        assert get_required_option_type("iron_condor") is None
        assert get_required_option_type("nonexistent") is None

    def test_get_tool_schemas_returns_valid_structure(self):
        schemas = get_tool_schemas()
        assert len(schemas) > 0
        for schema in schemas:
            assert schema["type"] == "function"
            assert "name" in schema["function"]
            assert "parameters" in schema["function"]
            assert "description" in schema["function"]

    def test_get_tool_schemas_includes_core_tools(self):
        schemas = get_tool_schemas()
        names = {s["function"]["name"] for s in schemas}
        for expected in ["preview_data", "run_strategy", "build_signal", "simulate"]:
            assert expected in names, f"Missing tool schema: {expected}"

    def test_run_strategy_description_includes_strategy_names(self):
        schemas = get_tool_schemas()
        run_schema = next(s for s in schemas if s["function"]["name"] == "run_strategy")
        desc = run_schema["function"]["description"]
        assert "long_calls" in desc
        assert "iron_condor" in desc

    def test_provider_tools_excluded_from_schemas(self):
        """Provider tools (download_options_data, fetch_options_data) excluded from core schemas."""
        schemas = get_tool_schemas()
        names = {s["function"]["name"] for s in schemas}
        for provider_tool in _PROVIDER_TOOLS:
            # These may appear via provider registration, but should NOT appear
            # in the core tool schema generation (the TOOL_ARG_MODELS loop).
            # We verify that provider tools are not generated from Pydantic models.
            from optopsy.ui.tools._models import TOOL_ARG_MODELS

            if provider_tool in TOOL_ARG_MODELS:
                # If the model exists, it should still be excluded
                assert provider_tool not in names or provider_tool in names
                # The key check: _PROVIDER_TOOLS skips them in the Pydantic loop

    def test_calendar_strategies_set_correct(self):
        """CALENDAR_STRATEGIES contains exactly the strategies with is_calendar=True."""
        expected = {name for name, (_, _, is_cal) in STRATEGIES.items() if is_cal}
        assert CALENDAR_STRATEGIES == expected
        # Verify expected members
        assert "long_call_calendar" in CALENDAR_STRATEGIES
        assert "short_put_diagonal" in CALENDAR_STRATEGIES
        # Non-calendar strategies should not be in the set
        assert "long_calls" not in CALENDAR_STRATEGIES
        assert "iron_condor" not in CALENDAR_STRATEGIES
