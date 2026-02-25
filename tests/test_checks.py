"""Tests for parameter and DataFrame validation in optopsy.checks.

Tests the public entry points ``_run_checks`` and ``_run_calendar_checks``
which validate parameters via Pydantic models and check DataFrame schemas.
Also tests the helper predicates ``_requires_delta`` and ``_requires_volume``.
"""

import pandas as pd
import pytest

import optopsy.checks as op

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def valid_data():
    """Minimal valid option chain DataFrame for checks."""
    return pd.DataFrame(
        {
            "underlying_symbol": ["SPY"],
            "underlying_price": [450.0],
            "option_type": ["call"],
            "expiration": pd.to_datetime(["2024-03-15"]),
            "quote_date": pd.to_datetime(["2024-01-15"]),
            "strike": [455.0],
            "bid": [2.50],
            "ask": [2.80],
        }
    )


# ---------------------------------------------------------------------------
# _run_checks — standard strategies
# ---------------------------------------------------------------------------


class TestRunChecks:
    """Integration tests for _run_checks (standard strategy validation)."""

    def test_returns_dict_with_defaults(self, valid_data):
        result = op._run_checks({}, valid_data)
        assert isinstance(result, dict)
        assert result["max_entry_dte"] == 90
        assert result["exit_dte"] == 0
        assert result["dte_interval"] == 7
        assert result["slippage"] == "mid"
        assert result["raw"] is False
        assert result["drop_nan"] is True

    def test_user_overrides_applied(self, valid_data):
        result = op._run_checks({"max_entry_dte": 60, "exit_dte": 14}, valid_data)
        assert result["max_entry_dte"] == 60
        assert result["exit_dte"] == 14

    def test_raises_on_invalid_params(self, valid_data):
        with pytest.raises(ValueError):
            op._run_checks({"max_entry_dte": -1}, valid_data)

    def test_raises_on_unknown_params(self, valid_data):
        with pytest.raises(ValueError):
            op._run_checks({"unknown_param": 42}, valid_data)

    def test_raises_on_missing_columns(self):
        bad_data = pd.DataFrame({"foo": [1]})
        with pytest.raises(ValueError, match="Expected column"):
            op._run_checks({}, bad_data)

    def test_raises_on_wrong_column_dtype(self):
        bad_data = pd.DataFrame(
            {
                "underlying_symbol": [123],  # wrong type
                "underlying_price": [450.0],
                "option_type": ["call"],
                "expiration": pd.to_datetime(["2024-03-15"]),
                "quote_date": pd.to_datetime(["2024-01-15"]),
                "strike": [455.0],
                "bid": [2.50],
                "ask": [2.80],
            }
        )
        with pytest.raises(ValueError, match="does not match expected types"):
            op._run_checks({}, bad_data)

    def test_raises_on_exit_dte_gte_max_entry_dte(self, valid_data):
        with pytest.raises(ValueError):
            op._run_checks({"exit_dte": 90, "max_entry_dte": 90}, valid_data)


# ---------------------------------------------------------------------------
# _run_calendar_checks — calendar/diagonal strategies
# ---------------------------------------------------------------------------


class TestRunCalendarChecks:
    """Integration tests for _run_calendar_checks."""

    def test_returns_dict_with_calendar_defaults(self, valid_data):
        result = op._run_calendar_checks({}, valid_data)
        assert isinstance(result, dict)
        assert result["exit_dte"] == 7
        assert result["max_entry_dte"] is None
        assert result["front_dte_min"] == 20
        assert result["front_dte_max"] == 40
        assert result["back_dte_min"] == 50
        assert result["back_dte_max"] == 90

    def test_user_overrides_applied(self, valid_data):
        result = op._run_calendar_checks(
            {"front_dte_min": 10, "front_dte_max": 30, "back_dte_min": 40},
            valid_data,
        )
        assert result["front_dte_min"] == 10
        assert result["front_dte_max"] == 30
        assert result["back_dte_min"] == 40

    def test_raises_on_overlapping_ranges(self, valid_data):
        with pytest.raises(ValueError):
            op._run_calendar_checks(
                {"front_dte_max": 60, "back_dte_min": 50}, valid_data
            )

    def test_raises_on_unknown_params(self, valid_data):
        with pytest.raises(ValueError):
            op._run_calendar_checks({"bad_param": 42}, valid_data)


# ---------------------------------------------------------------------------
# DataFrame schema checks
# ---------------------------------------------------------------------------


class TestCheckDataTypes:
    def test_rejects_missing_column(self):
        with pytest.raises(ValueError, match="Expected column"):
            op._check_data_types(pd.DataFrame({"some_col": ["some val"]}))

    def test_rejects_wrong_type(self):
        with pytest.raises(
            ValueError, match="underlying_symbol does not match expected types"
        ):
            op._check_data_types(pd.DataFrame({"underlying_symbol": [123]}))


class TestCheckGreekColumn:
    def test_rejects_missing_delta(self):
        with pytest.raises(ValueError, match="Greek column 'delta' not found"):
            op._check_greek_column(pd.DataFrame({"bid": [1.0]}), "delta")

    def test_rejects_wrong_type(self):
        with pytest.raises(ValueError, match="does not match expected types"):
            op._check_greek_column(pd.DataFrame({"delta": ["string"]}), "delta")

    def test_accepts_valid_delta(self):
        assert op._check_greek_column(pd.DataFrame({"delta": [0.5]}), "delta") is None


class TestCheckVolumeColumn:
    def test_rejects_missing_volume(self):
        with pytest.raises(ValueError, match="volume.*not found"):
            op._check_volume_column(pd.DataFrame({"bid": [1.0]}))

    def test_rejects_wrong_type(self):
        with pytest.raises(ValueError, match="does not match expected types"):
            op._check_volume_column(pd.DataFrame({"volume": ["string"]}))

    def test_accepts_valid_volume(self):
        assert op._check_volume_column(pd.DataFrame({"volume": [100]})) is None


# ---------------------------------------------------------------------------
# Helper predicates
# ---------------------------------------------------------------------------


class TestRequiresDelta:
    def test_true_when_delta_min_set(self):
        assert op._requires_delta(
            {"delta_min": 0.3, "delta_max": None, "delta_interval": None}
        )

    def test_true_when_delta_max_set(self):
        assert op._requires_delta(
            {"delta_min": None, "delta_max": -0.3, "delta_interval": None}
        )

    def test_true_when_delta_interval_set(self):
        assert op._requires_delta(
            {"delta_min": None, "delta_max": None, "delta_interval": 0.1}
        )

    def test_false_when_all_none(self):
        assert not op._requires_delta(
            {"delta_min": None, "delta_max": None, "delta_interval": None}
        )


class TestRequiresVolume:
    def test_true_when_liquidity(self):
        assert op._requires_volume({"slippage": "liquidity"})

    def test_false_when_mid(self):
        assert not op._requires_volume({"slippage": "mid"})

    def test_false_when_spread(self):
        assert not op._requires_volume({"slippage": "spread"})
