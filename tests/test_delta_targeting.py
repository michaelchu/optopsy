"""Tests for per-leg delta targeting feature."""

import pytest

import optopsy as op
from optopsy.types import TargetRange


class TestTargetRangeValidation:
    """Test TargetRange model validation."""

    def test_valid_target_range(self):
        tr = TargetRange(target=0.30, min=0.25, max=0.35)
        assert tr.target == 0.30
        assert tr.min == 0.25
        assert tr.max == 0.35

    def test_target_equals_min_and_max(self):
        tr = TargetRange(target=0.30, min=0.30, max=0.30)
        assert tr.target == 0.30

    def test_min_greater_than_target_raises(self):
        with pytest.raises(ValueError, match="min.*must be <= target"):
            TargetRange(target=0.20, min=0.30, max=0.35)

    def test_target_greater_than_max_raises(self):
        with pytest.raises(ValueError, match="target.*must be <= max"):
            TargetRange(target=0.40, min=0.25, max=0.35)

    def test_zero_target_raises(self):
        with pytest.raises(ValueError):
            TargetRange(target=0.0, min=0.0, max=0.5)

    def test_above_one_raises(self):
        with pytest.raises(ValueError):
            TargetRange(target=1.5, min=0.5, max=1.5)


class TestSingleLegDeltaTargeting:
    """Test single-leg strategies with delta targeting."""

    def test_long_calls_with_delta_target(self, multi_strike_data_with_delta):
        result = op.long_calls(
            multi_strike_data_with_delta,
            leg1_delta=TargetRange(target=0.35, min=0.25, max=0.45),
            raw=True,
        )
        assert not result.empty
        # Should select the 215.0 strike (delta=0.35, closest to target)
        assert (result["strike"] == 215.0).all()

    def test_long_puts_with_delta_target(self, multi_strike_data_with_delta):
        result = op.long_puts(
            multi_strike_data_with_delta,
            leg1_delta=TargetRange(target=0.35, min=0.25, max=0.45),
            raw=True,
        )
        assert not result.empty
        # Should select the 210.0 strike (abs(delta)=0.35, closest to target)
        assert (result["strike"] == 210.0).all()

    def test_delta_entry_column_in_raw_output(self, multi_strike_data_with_delta):
        result = op.long_calls(
            multi_strike_data_with_delta,
            leg1_delta=TargetRange(target=0.50, min=0.40, max=0.60),
            raw=True,
        )
        assert "delta_entry" in result.columns


class TestVerticalSpreadDeltaTargeting:
    """Test vertical spreads with per-leg delta targeting."""

    def test_short_put_spread_with_delta_targets(self, multi_strike_data_with_delta):
        result = op.short_put_spread(
            multi_strike_data_with_delta,
            leg1_delta=TargetRange(target=0.20, min=0.15, max=0.25),
            leg2_delta=TargetRange(target=0.50, min=0.40, max=0.60),
            raw=True,
        )
        assert not result.empty
        # leg1 (long put): abs(delta)=0.20 -> strike 207.5
        # leg2 (short put): abs(delta)=0.50 -> strike 212.5
        assert (result["strike_leg1"] == 207.5).all()
        assert (result["strike_leg2"] == 212.5).all()

    def test_long_call_spread_with_delta_targets(self, multi_strike_data_with_delta):
        result = op.long_call_spread(
            multi_strike_data_with_delta,
            leg1_delta=TargetRange(target=0.50, min=0.40, max=0.60),
            leg2_delta=TargetRange(target=0.20, min=0.15, max=0.25),
            raw=True,
        )
        assert not result.empty
        # leg1 (long call): delta=0.50 -> strike 212.5
        # leg2 (short call): delta=0.20 -> strike 217.5
        assert (result["strike_leg1"] == 212.5).all()
        assert (result["strike_leg2"] == 217.5).all()

    def test_spread_no_near_zero_entry(self, multi_strike_data_with_delta):
        """Delta targeting should produce meaningful entry costs, not near-zero."""
        result = op.short_put_spread(
            multi_strike_data_with_delta,
            leg1_delta=TargetRange(target=0.20, min=0.15, max=0.25),
            leg2_delta=TargetRange(target=0.50, min=0.40, max=0.60),
            raw=True,
        )
        assert not result.empty
        assert (result["total_entry_cost"].abs() > 0.50).all()


class TestIronCondorDeltaTargeting:
    """Test iron condor with 4 per-leg delta targets."""

    def test_iron_condor_with_delta_targets(self, multi_strike_data_with_delta):
        result = op.iron_condor(
            multi_strike_data_with_delta,
            leg1_delta=TargetRange(target=0.20, min=0.15, max=0.25),
            leg2_delta=TargetRange(target=0.35, min=0.30, max=0.45),
            leg3_delta=TargetRange(target=0.35, min=0.30, max=0.45),
            leg4_delta=TargetRange(target=0.20, min=0.15, max=0.25),
            raw=True,
        )
        assert not result.empty


class TestStraddleDeltaTargeting:
    """Test straddle with same delta target for both legs."""

    def test_long_straddle_with_delta_targets(self, multi_strike_data_with_delta):
        result = op.long_straddles(
            multi_strike_data_with_delta,
            leg1_delta=TargetRange(target=0.50, min=0.40, max=0.60),
            leg2_delta=TargetRange(target=0.50, min=0.40, max=0.60),
            raw=True,
        )
        assert not result.empty


class TestDeltaTargetingValidationErrors:
    """Test validation errors for delta targeting."""

    def test_missing_delta_column_raises(self):
        """Data without delta column should raise ValueError."""
        import datetime

        import pandas as pd

        # Create data without delta column
        exp_date = datetime.datetime(2018, 1, 31)
        entry_date = datetime.datetime(2018, 1, 1)
        no_delta_data = pd.DataFrame(
            {
                "underlying_symbol": ["SPX"],
                "underlying_price": [212.5],
                "option_type": ["call"],
                "expiration": [exp_date],
                "quote_date": [entry_date],
                "strike": [212.5],
                "bid": [3.0],
                "ask": [3.10],
            }
        )
        with pytest.raises(ValueError, match="delta"):
            op.long_calls(no_delta_data, raw=True)


class TestAggregatedOutput:
    """Test aggregated output with delta targeting."""

    def test_aggregated_output_has_delta_range(self, multi_strike_data_with_delta):
        result = op.long_calls(
            multi_strike_data_with_delta,
            leg1_delta=TargetRange(target=0.50, min=0.40, max=0.60),
        )
        assert "delta_range" in result.columns
        assert "dte_range" in result.columns

    def test_spread_aggregated_has_per_leg_delta_range(
        self, multi_strike_data_with_delta
    ):
        result = op.short_put_spread(
            multi_strike_data_with_delta,
            leg1_delta=TargetRange(target=0.20, min=0.15, max=0.25),
            leg2_delta=TargetRange(target=0.50, min=0.40, max=0.60),
        )
        assert "delta_range_leg1" in result.columns
        assert "delta_range_leg2" in result.columns
