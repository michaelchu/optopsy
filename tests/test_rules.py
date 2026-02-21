import datetime

import pandas as pd

from optopsy.core import _calls, _puts
from optopsy.rules import (
    _rule_butterfly_strikes,
    _rule_expiration_ordering,
    _rule_iron_butterfly_strikes,
    _rule_iron_condor_strikes,
    _rule_non_overlapping_strike,
)
from optopsy.strategies import Side


class TestRuleNonOverlappingStrike:
    """Tests for _rule_non_overlapping_strike."""

    def test_single_leg_returns_unchanged(self, data):
        """Single-leg definition should return data unchanged."""
        leg_def = [(Side.long, _calls)]
        result = _rule_non_overlapping_strike(_calls(data), leg_def)
        assert len(result) == 4
        assert "call" in list(result["option_type"].values)

    def test_two_legs_filters_overlapping(self):
        """Two-leg data should only keep rows where leg1 strike < leg2 strike."""
        df = pd.DataFrame(
            {
                "strike_leg1": [210.0, 215.0, 210.0],
                "strike_leg2": [215.0, 210.0, 210.0],
                "other": [1, 2, 3],
            }
        )
        leg_def = [(Side.long, _calls), (Side.short, _calls)]
        result = _rule_non_overlapping_strike(df, leg_def)
        assert len(result) == 1
        assert result.iloc[0]["strike_leg1"] == 210.0
        assert result.iloc[0]["strike_leg2"] == 215.0

    def test_three_legs_ascending_order(self):
        """Three-leg data should enforce strike_leg1 < strike_leg2 < strike_leg3."""
        df = pd.DataFrame(
            {
                "strike_leg1": [200.0, 210.0, 200.0, 220.0],
                "strike_leg2": [210.0, 200.0, 210.0, 210.0],
                "strike_leg3": [220.0, 220.0, 200.0, 200.0],
            }
        )
        leg_def = [
            (Side.long, _calls),
            (Side.short, _calls),
            (Side.long, _calls),
        ]
        result = _rule_non_overlapping_strike(df, leg_def)
        assert len(result) == 1
        assert result.iloc[0]["strike_leg1"] == 200.0
        assert result.iloc[0]["strike_leg3"] == 220.0

    def test_empty_dataframe(self):
        """Empty DataFrame should return empty."""
        df = pd.DataFrame(columns=["strike_leg1", "strike_leg2"])
        leg_def = [(Side.long, _calls), (Side.short, _calls)]
        result = _rule_non_overlapping_strike(df, leg_def)
        assert len(result) == 0


class TestRuleButterflyStrikes:
    """Tests for _rule_butterfly_strikes."""

    def test_valid_butterfly_equal_width(self):
        """Butterfly with equal wing widths should pass."""
        df = pd.DataFrame(
            {
                "strike_leg1": [200.0, 200.0],
                "strike_leg2": [205.0, 210.0],
                "strike_leg3": [210.0, 215.0],
            }
        )
        leg_def = [
            (Side.long, _calls, 1),
            (Side.short, _calls, 2),
            (Side.long, _calls, 1),
        ]
        result = _rule_butterfly_strikes(df, leg_def)
        assert len(result) == 1
        # Only 200/205/210 has equal widths (5); 200/210/215 has widths 10 and 5
        assert result.iloc[0]["strike_leg2"] == 205.0

    def test_unequal_wings_filtered_out(self):
        """Butterfly with unequal wing widths should be filtered out."""
        df = pd.DataFrame(
            {
                "strike_leg1": [200.0],
                "strike_leg2": [210.0],
                "strike_leg3": [215.0],
            }
        )
        leg_def = [
            (Side.long, _calls, 1),
            (Side.short, _calls, 2),
            (Side.long, _calls, 1),
        ]
        result = _rule_butterfly_strikes(df, leg_def)
        assert len(result) == 0

    def test_non_ascending_strikes_filtered(self):
        """Strikes not in ascending order should be filtered."""
        df = pd.DataFrame(
            {
                "strike_leg1": [210.0],
                "strike_leg2": [205.0],
                "strike_leg3": [200.0],
            }
        )
        leg_def = [
            (Side.long, _calls, 1),
            (Side.short, _calls, 2),
            (Side.long, _calls, 1),
        ]
        result = _rule_butterfly_strikes(df, leg_def)
        assert len(result) == 0

    def test_wrong_leg_count_returns_unchanged(self):
        """Non-3-leg definition should return data unchanged."""
        df = pd.DataFrame({"strike_leg1": [200.0], "strike_leg2": [210.0]})
        leg_def = [(Side.long, _calls), (Side.short, _calls)]
        result = _rule_butterfly_strikes(df, leg_def)
        assert len(result) == 1


class TestRuleIronCondorStrikes:
    """Tests for _rule_iron_condor_strikes."""

    def test_valid_iron_condor_ascending(self):
        """Four strikes in ascending order should pass."""
        df = pd.DataFrame(
            {
                "strike_leg1": [200.0, 210.0],
                "strike_leg2": [205.0, 200.0],
                "strike_leg3": [210.0, 205.0],
                "strike_leg4": [215.0, 195.0],
            }
        )
        leg_def = [
            (Side.long, _puts),
            (Side.short, _puts),
            (Side.short, _calls),
            (Side.long, _calls),
        ]
        result = _rule_iron_condor_strikes(df, leg_def)
        assert len(result) == 1
        assert result.iloc[0]["strike_leg1"] == 200.0
        assert result.iloc[0]["strike_leg4"] == 215.0

    def test_non_ascending_filtered(self):
        """Non-ascending strikes should be filtered out."""
        df = pd.DataFrame(
            {
                "strike_leg1": [215.0],
                "strike_leg2": [210.0],
                "strike_leg3": [205.0],
                "strike_leg4": [200.0],
            }
        )
        leg_def = [
            (Side.long, _puts),
            (Side.short, _puts),
            (Side.short, _calls),
            (Side.long, _calls),
        ]
        result = _rule_iron_condor_strikes(df, leg_def)
        assert len(result) == 0

    def test_wrong_leg_count_returns_unchanged(self):
        """Non-4-leg definition should return data unchanged."""
        df = pd.DataFrame(
            {
                "strike_leg1": [200.0],
                "strike_leg2": [210.0],
                "strike_leg3": [220.0],
            }
        )
        leg_def = [
            (Side.long, _puts),
            (Side.short, _puts),
            (Side.short, _calls),
        ]
        result = _rule_iron_condor_strikes(df, leg_def)
        assert len(result) == 1


class TestRuleIronButterflyStrikes:
    """Tests for _rule_iron_butterfly_strikes."""

    def test_valid_iron_butterfly(self):
        """Middle strikes equal, wings outside should pass."""
        df = pd.DataFrame(
            {
                "strike_leg1": [200.0],
                "strike_leg2": [210.0],
                "strike_leg3": [210.0],
                "strike_leg4": [220.0],
            }
        )
        leg_def = [
            (Side.long, _puts),
            (Side.short, _puts),
            (Side.short, _calls),
            (Side.long, _calls),
        ]
        result = _rule_iron_butterfly_strikes(df, leg_def)
        assert len(result) == 1

    def test_middle_strikes_unequal_filtered(self):
        """Middle strikes not equal should be filtered."""
        df = pd.DataFrame(
            {
                "strike_leg1": [200.0],
                "strike_leg2": [210.0],
                "strike_leg3": [215.0],
                "strike_leg4": [220.0],
            }
        )
        leg_def = [
            (Side.long, _puts),
            (Side.short, _puts),
            (Side.short, _calls),
            (Side.long, _calls),
        ]
        result = _rule_iron_butterfly_strikes(df, leg_def)
        assert len(result) == 0

    def test_wing_not_outside_filtered(self):
        """Wing strike not outside middle should be filtered."""
        df = pd.DataFrame(
            {
                "strike_leg1": [210.0],  # not less than leg2
                "strike_leg2": [210.0],
                "strike_leg3": [210.0],
                "strike_leg4": [220.0],
            }
        )
        leg_def = [
            (Side.long, _puts),
            (Side.short, _puts),
            (Side.short, _calls),
            (Side.long, _calls),
        ]
        result = _rule_iron_butterfly_strikes(df, leg_def)
        assert len(result) == 0

    def test_wrong_leg_count_returns_unchanged(self):
        """Non-4-leg definition should return data unchanged."""
        df = pd.DataFrame({"strike_leg1": [200.0], "strike_leg2": [210.0]})
        leg_def = [(Side.long, _puts), (Side.short, _puts)]
        result = _rule_iron_butterfly_strikes(df, leg_def)
        assert len(result) == 1


class TestRuleExpirationOrdering:
    """Tests for _rule_expiration_ordering."""

    def test_front_before_back_passes(self):
        """Front expiration before back expiration should pass."""
        df = pd.DataFrame(
            {
                "expiration_leg1": [datetime.datetime(2018, 1, 31)],
                "expiration_leg2": [datetime.datetime(2018, 3, 2)],
            }
        )
        leg_def = [(Side.short, _calls), (Side.long, _calls)]
        result = _rule_expiration_ordering(df, leg_def)
        assert len(result) == 1

    def test_front_after_back_filtered(self):
        """Front expiration after back expiration should be filtered out."""
        df = pd.DataFrame(
            {
                "expiration_leg1": [datetime.datetime(2018, 3, 2)],
                "expiration_leg2": [datetime.datetime(2018, 1, 31)],
            }
        )
        leg_def = [(Side.short, _calls), (Side.long, _calls)]
        result = _rule_expiration_ordering(df, leg_def)
        assert len(result) == 0

    def test_same_expiration_filtered(self):
        """Same expiration for both legs should be filtered out."""
        df = pd.DataFrame(
            {
                "expiration_leg1": [datetime.datetime(2018, 1, 31)],
                "expiration_leg2": [datetime.datetime(2018, 1, 31)],
            }
        )
        leg_def = [(Side.short, _calls), (Side.long, _calls)]
        result = _rule_expiration_ordering(df, leg_def)
        assert len(result) == 0

    def test_wrong_leg_count_returns_unchanged(self):
        """Non-2-leg definition should return data unchanged."""
        df = pd.DataFrame(
            {
                "expiration_leg1": [datetime.datetime(2018, 3, 2)],
                "expiration_leg2": [datetime.datetime(2018, 1, 31)],
            }
        )
        leg_def = [(Side.short, _calls)]
        result = _rule_expiration_ordering(df, leg_def)
        assert len(result) == 1

    def test_mixed_ordering(self):
        """Multiple rows with mixed ordering should filter correctly."""
        df = pd.DataFrame(
            {
                "expiration_leg1": [
                    datetime.datetime(2018, 1, 31),
                    datetime.datetime(2018, 3, 2),
                    datetime.datetime(2018, 2, 15),
                ],
                "expiration_leg2": [
                    datetime.datetime(2018, 3, 2),
                    datetime.datetime(2018, 1, 31),
                    datetime.datetime(2018, 4, 1),
                ],
            }
        )
        leg_def = [(Side.short, _calls), (Side.long, _calls)]
        result = _rule_expiration_ordering(df, leg_def)
        assert len(result) == 2
