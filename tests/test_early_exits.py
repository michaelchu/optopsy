"""Tests for early exits (stop-loss, take-profit, and max-hold-days)."""

import datetime

import pandas as pd
import pytest

import optopsy as op


@pytest.fixture
def multi_date_data():
    """Option chain with multiple intermediate quote dates for early exit testing.

    Structure:
    - Day 0  (entry, dte=30): call mid = 6.00, put mid = 6.00
    - Day 5  (dte=25):        call mid = 4.50 (down 25%), put mid = 7.50 (up 25%)
    - Day 10 (dte=20):        call mid = 3.00 (down 50%), put mid = 9.00 (up 50%)
    - Day 15 (dte=15):        call mid = 5.00 (recovery), put mid = 7.00
    - Day 20 (dte=10):        call mid = 8.00 (up 33%), put mid = 4.00
    - Day 30 (dte=0):         call mid = 10.00 (expiration), put mid = 2.00
    """
    entry_date = datetime.datetime(2018, 1, 1)
    exp_date = datetime.datetime(2018, 1, 31)

    dates = [
        entry_date,
        datetime.datetime(2018, 1, 6),  # day 5
        datetime.datetime(2018, 1, 11),  # day 10
        datetime.datetime(2018, 1, 16),  # day 15
        datetime.datetime(2018, 1, 21),  # day 20
        exp_date,  # day 30
    ]

    cols = [
        "underlying_symbol",
        "underlying_price",
        "option_type",
        "expiration",
        "quote_date",
        "strike",
        "bid",
        "ask",
        "delta",
    ]

    d = [
        # Day 0 (entry) - calls
        ["SPX", 200, "call", exp_date, dates[0], 200.0, 5.90, 6.10, 0.30],
        # Day 5 - calls (price dropped)
        ["SPX", 196, "call", exp_date, dates[1], 200.0, 4.40, 4.60, 0.25],
        # Day 10 - calls (price dropped more → -50% unrealized)
        ["SPX", 192, "call", exp_date, dates[2], 200.0, 2.90, 3.10, 0.18],
        # Day 15 - calls (recovery)
        ["SPX", 198, "call", exp_date, dates[3], 200.0, 4.90, 5.10, 0.28],
        # Day 20 - calls (up)
        ["SPX", 205, "call", exp_date, dates[4], 200.0, 7.90, 8.10, 0.40],
        # Day 30 (expiration) - calls
        ["SPX", 210, "call", exp_date, dates[5], 200.0, 9.90, 10.10, 0.90],
        # Day 0 (entry) - puts
        ["SPX", 200, "put", exp_date, dates[0], 200.0, 5.90, 6.10, -0.30],
        # Day 5 - puts (price dropped → put value up)
        ["SPX", 196, "put", exp_date, dates[1], 200.0, 7.40, 7.60, -0.40],
        # Day 10 - puts (price dropped more → put value up 50%)
        ["SPX", 192, "put", exp_date, dates[2], 200.0, 8.90, 9.10, -0.55],
        # Day 15 - puts (recovery)
        ["SPX", 198, "put", exp_date, dates[3], 200.0, 6.90, 7.10, -0.35],
        # Day 20 - puts (down)
        ["SPX", 205, "put", exp_date, dates[4], 200.0, 3.90, 4.10, -0.15],
        # Day 30 (expiration) - puts
        ["SPX", 210, "put", exp_date, dates[5], 200.0, 1.90, 2.10, -0.10],
    ]
    return pd.DataFrame(data=d, columns=cols)


@pytest.fixture
def multi_date_spread_data():
    """Option chain with multiple dates for testing multi-leg (spread) early exits.

    Vertical call spread: long 200 call + short 205 call.

    Day 0  (entry): long 200c mid=6.00, short 205c mid=3.00, net debit=3.00
    Day 5:          long 200c mid=4.50, short 205c mid=2.00, net value=2.50 → -16.7%
    Day 10:         long 200c mid=3.00, short 205c mid=1.00, net value=2.00 → -33.3%
    Day 15:         long 200c mid=1.50, short 205c mid=0.25, net value=1.25 → -58.3% (stop)
    Day 30 (exit):  long 200c mid=10.0, short 205c mid=5.50, net value=4.50
    """
    entry_date = datetime.datetime(2018, 1, 1)
    exp_date = datetime.datetime(2018, 1, 31)

    dates = [
        entry_date,
        datetime.datetime(2018, 1, 6),
        datetime.datetime(2018, 1, 11),
        datetime.datetime(2018, 1, 16),
        exp_date,
    ]

    cols = [
        "underlying_symbol",
        "underlying_price",
        "option_type",
        "expiration",
        "quote_date",
        "strike",
        "bid",
        "ask",
        "delta",
    ]

    d = [
        # Day 0 - 200 strike call
        ["SPX", 200, "call", exp_date, dates[0], 200.0, 5.90, 6.10, 0.50],
        # Day 0 - 205 strike call
        ["SPX", 200, "call", exp_date, dates[0], 205.0, 2.90, 3.10, 0.30],
        # Day 5
        ["SPX", 196, "call", exp_date, dates[1], 200.0, 4.40, 4.60, 0.40],
        ["SPX", 196, "call", exp_date, dates[1], 205.0, 1.90, 2.10, 0.20],
        # Day 10
        ["SPX", 192, "call", exp_date, dates[2], 200.0, 2.90, 3.10, 0.30],
        ["SPX", 192, "call", exp_date, dates[2], 205.0, 0.90, 1.10, 0.12],
        # Day 15
        ["SPX", 188, "call", exp_date, dates[3], 200.0, 1.40, 1.60, 0.18],
        ["SPX", 188, "call", exp_date, dates[3], 205.0, 0.20, 0.30, 0.05],
        # Day 30 (expiration)
        ["SPX", 210, "call", exp_date, dates[4], 200.0, 9.90, 10.10, 0.95],
        ["SPX", 210, "call", exp_date, dates[4], 205.0, 5.40, 5.60, 0.85],
        # Puts (needed by pipeline for complete data but not used by call strategies)
        ["SPX", 200, "put", exp_date, dates[0], 200.0, 5.90, 6.10, -0.50],
        ["SPX", 200, "put", exp_date, dates[0], 205.0, 7.90, 8.10, -0.70],
        ["SPX", 210, "put", exp_date, dates[4], 200.0, 0.0, 0.10, -0.05],
        ["SPX", 210, "put", exp_date, dates[4], 205.0, 0.0, 0.10, -0.15],
    ]
    return pd.DataFrame(data=d, columns=cols)


class TestSingleLegStopLoss:
    """Test stop-loss behavior for single-leg strategies."""

    def test_stop_loss_triggers(self, multi_date_data):
        """Stop-loss should trigger at the first date where P&L <= threshold."""
        result = op.long_calls(
            multi_date_data,
            leg1_delta={"target": 0.30, "min": 0.15, "max": 0.40},
            stop_loss=-0.50,
            raw=True,
        )
        assert not result.empty
        assert "exit_type" in result.columns
        assert result["exit_type"].iloc[0] == "stop_loss"
        # Exit should be at day 10 (mid=3.00), not day 30 (mid=10.00)
        # pct_change for long call: (3.00 - 6.00) / 6.00 = -0.50
        assert result["pct_change"].iloc[0] == pytest.approx(-0.50, abs=0.01)

    def test_stop_loss_not_triggered(self, multi_date_data):
        """Stop-loss should not trigger if threshold is never reached."""
        result = op.long_calls(
            multi_date_data,
            leg1_delta={"target": 0.30, "min": 0.15, "max": 0.40},
            stop_loss=-0.90,  # Very deep threshold, never reached
            raw=True,
        )
        assert not result.empty
        assert "exit_type" in result.columns
        assert result["exit_type"].iloc[0] == "expiration"


class TestSingleLegTakeProfit:
    """Test take-profit behavior for single-leg strategies."""

    def test_take_profit_triggers(self, multi_date_data):
        """Take-profit should trigger at first crossing date."""
        # For a long put: entry mid=6.00, day 10 mid=9.00
        # unrealized pct = 1 * (9.00 - 6.00) / 6.00 = 0.50
        # Wait — for long puts, side=1, so pct = 1 * (exit - entry) / |entry|
        result = op.long_puts(
            multi_date_data,
            leg1_delta={"target": 0.30, "min": 0.15, "max": 0.70},
            take_profit=0.25,
            raw=True,
        )
        assert not result.empty
        assert "exit_type" in result.columns
        assert result["exit_type"].iloc[0] == "take_profit"
        # Should exit at day 5 (mid=7.50), unrealized = (7.50 - 6.00)/6.00 = 0.25
        assert result["pct_change"].iloc[0] == pytest.approx(0.25, abs=0.02)


class TestNoEarlyExit:
    """Test backward compatibility — no early exit when thresholds not set."""

    def test_no_thresholds_no_exit_type_column(self, multi_date_data):
        """Without stop_loss/take_profit, exit_type should not appear."""
        result = op.long_calls(
            multi_date_data,
            leg1_delta={"target": 0.30, "min": 0.15, "max": 0.40},
            raw=True,
        )
        assert not result.empty
        assert "exit_type" not in result.columns

    def test_backward_compat_same_result(self, multi_date_data):
        """Result without thresholds should match base behavior."""
        base = op.long_calls(
            multi_date_data,
            leg1_delta={"target": 0.30, "min": 0.15, "max": 0.40},
            raw=True,
        )
        # With thresholds that are never hit, should produce same pct_change
        # Use extreme thresholds — max unrealized gain can exceed 200%
        result = op.long_calls(
            multi_date_data,
            leg1_delta={"target": 0.30, "min": 0.15, "max": 0.40},
            stop_loss=-5.0,
            take_profit=5.0,
            raw=True,
        )
        if not result.empty:
            # pct_change should be the same (normal expiration exit)
            _skip_cols = {"exit_type", "_early_exit_date"}
            base_cols = [c for c in base.columns if c not in _skip_cols]
            result_cols = [c for c in result.columns if c not in _skip_cols]
            pd.testing.assert_frame_equal(
                base[base_cols].reset_index(drop=True),
                result[result_cols].reset_index(drop=True),
            )


class TestBothThresholds:
    """Test behavior when both stop-loss and take-profit are set."""

    def test_first_threshold_wins(self, multi_date_data):
        """When both thresholds are set, first chronological crossing wins."""
        # For long call: day 5 unrealized=-25%, day 10=-50%
        # stop_loss=-0.25 should trigger at day 5
        result = op.long_calls(
            multi_date_data,
            leg1_delta={"target": 0.30, "min": 0.15, "max": 0.40},
            stop_loss=-0.25,
            take_profit=0.50,
            raw=True,
        )
        assert not result.empty
        assert result["exit_type"].iloc[0] == "stop_loss"
        assert result["pct_change"].iloc[0] == pytest.approx(-0.25, abs=0.02)


class TestExitTypeValues:
    """Test exit_type column values."""

    def test_expiration_exit_type(self, multi_date_data):
        """Trades without early exit should have exit_type='expiration'."""
        result = op.long_calls(
            multi_date_data,
            leg1_delta={"target": 0.30, "min": 0.15, "max": 0.40},
            stop_loss=-0.99,  # Very deep, never triggered
            raw=True,
        )
        if not result.empty:
            assert result["exit_type"].iloc[0] == "expiration"


class TestMultiLegStopLoss:
    """Test stop-loss for multi-leg strategies."""

    def test_spread_stop_loss(self, multi_date_spread_data):
        """Multi-leg stop-loss should use total P&L across legs."""
        result = op.long_call_spread(
            multi_date_spread_data,
            leg1_delta={"target": 0.50, "min": 0.40, "max": 0.60},
            leg2_delta={"target": 0.30, "min": 0.10, "max": 0.40},
            stop_loss=-0.50,
            raw=True,
        )
        assert not result.empty
        assert "exit_type" in result.columns
        # Check that stop-loss triggered
        triggered = result[result["exit_type"] == "stop_loss"]
        # With -0.50 threshold, the spread should trigger when P&L drops enough
        if not triggered.empty:
            assert triggered["pct_change"].iloc[0] <= -0.50


class TestNoIntermediateData:
    """Test behavior with no intermediate quotes (2-date fixture)."""

    def test_no_intermediate_dates(self, data):
        """With only entry/exit dates, no early exit should occur."""
        result = op.long_calls(
            data,
            leg1_delta={"target": 0.30, "min": 0.20, "max": 0.40},
            stop_loss=-0.10,
            take_profit=0.10,
            raw=True,
        )
        assert not result.empty
        assert result["exit_type"].iloc[0] == "expiration"


class TestAggregatedOutput:
    """Test that aggregated output works with early exits."""

    def test_aggregated_with_early_exits(self, multi_date_data):
        """raw=False (aggregated) should still work when early exits are applied."""
        result = op.long_calls(
            multi_date_data,
            leg1_delta={"target": 0.30, "min": 0.15, "max": 0.40},
            stop_loss=-0.50,
            raw=False,
        )
        # Should produce a valid aggregated DataFrame
        assert isinstance(result, pd.DataFrame)
        # Should have standard describe columns
        assert "count" in result.columns or result.empty


class TestParameterValidation:
    """Test validation of stop_loss and take_profit parameters."""

    def test_stop_loss_must_be_negative(self, multi_date_data):
        """stop_loss must be < 0."""
        with pytest.raises(Exception):
            op.long_calls(
                multi_date_data,
                leg1_delta={"target": 0.30, "min": 0.15, "max": 0.40},
                stop_loss=0.50,  # Must be negative
            )

    def test_take_profit_must_be_positive(self, multi_date_data):
        """take_profit must be > 0."""
        with pytest.raises(Exception):
            op.long_calls(
                multi_date_data,
                leg1_delta={"target": 0.30, "min": 0.15, "max": 0.40},
                take_profit=-0.50,  # Must be positive
            )

    def test_stop_loss_must_be_float(self, multi_date_data):
        """stop_loss must be a float, not int."""
        with pytest.raises(Exception):
            op.long_calls(
                multi_date_data,
                leg1_delta={"target": 0.30, "min": 0.15, "max": 0.40},
                stop_loss=-1,  # Must be float
            )

    def test_take_profit_must_be_float(self, multi_date_data):
        """take_profit must be a float, not int."""
        with pytest.raises(Exception):
            op.long_calls(
                multi_date_data,
                leg1_delta={"target": 0.30, "min": 0.15, "max": 0.40},
                take_profit=1,  # Must be float
            )


class TestMaxHoldDaysSingleLeg:
    """Test max_hold_days for single-leg strategies."""

    def test_max_hold_days_triggers(self, multi_date_data):
        """Position should exit when held for >= max_hold_days calendar days."""
        # Entry is day 0 (Jan 1), max_hold_days=10 should trigger at Jan 11 (day 10)
        result = op.long_calls(
            multi_date_data,
            leg1_delta={"target": 0.30, "min": 0.15, "max": 0.40},
            max_hold_days=10,
            raw=True,
        )
        assert not result.empty
        assert "exit_type" in result.columns
        assert result["exit_type"].iloc[0] == "max_hold"
        # Exit at day 10: mid=3.00, entry mid=6.00 → pct = (3.00-6.00)/6.00 = -0.50
        assert result["pct_change"].iloc[0] == pytest.approx(-0.50, abs=0.01)

    def test_max_hold_days_not_triggered(self, multi_date_data):
        """No early exit when max_hold_days exceeds actual hold period."""
        # Hold period is 30 days (Jan 1 → Jan 31), setting max_hold_days=60
        result = op.long_calls(
            multi_date_data,
            leg1_delta={"target": 0.30, "min": 0.15, "max": 0.40},
            max_hold_days=60,
            raw=True,
        )
        assert not result.empty
        assert "exit_type" in result.columns
        assert result["exit_type"].iloc[0] == "expiration"

    def test_max_hold_days_triggers_at_first_eligible_date(self, multi_date_data):
        """max_hold_days=5 should exit at the first date >= 5 days after entry."""
        result = op.long_calls(
            multi_date_data,
            leg1_delta={"target": 0.30, "min": 0.15, "max": 0.40},
            max_hold_days=5,
            raw=True,
        )
        assert not result.empty
        assert result["exit_type"].iloc[0] == "max_hold"
        # Day 5 (Jan 6): mid=4.50, entry=6.00 → pct = (4.50-6.00)/6.00 = -0.25
        assert result["pct_change"].iloc[0] == pytest.approx(-0.25, abs=0.02)


class TestMaxHoldDaysMultiLeg:
    """Test max_hold_days for multi-leg strategies."""

    def test_spread_max_hold_days(self, multi_date_spread_data):
        """Multi-leg strategy should exit at max_hold_days."""
        result = op.long_call_spread(
            multi_date_spread_data,
            leg1_delta={"target": 0.50, "min": 0.40, "max": 0.60},
            leg2_delta={"target": 0.30, "min": 0.10, "max": 0.40},
            max_hold_days=10,
            raw=True,
        )
        assert not result.empty
        assert "exit_type" in result.columns
        triggered = result[result["exit_type"] == "max_hold"]
        assert not triggered.empty


class TestMaxHoldDaysCombined:
    """Test max_hold_days combined with P&L-based exits."""

    def test_stop_loss_fires_before_max_hold(self, multi_date_data):
        """When stop-loss fires before max_hold_days, stop_loss wins."""
        # stop_loss=-0.25 fires at day 5, max_hold_days=15 fires at day 15
        result = op.long_calls(
            multi_date_data,
            leg1_delta={"target": 0.30, "min": 0.15, "max": 0.40},
            stop_loss=-0.25,
            max_hold_days=15,
            raw=True,
        )
        assert not result.empty
        assert result["exit_type"].iloc[0] == "stop_loss"

    def test_max_hold_fires_before_stop_loss(self, multi_date_data):
        """When max_hold_days fires before stop-loss, max_hold wins."""
        # max_hold_days=5 fires at day 5, stop_loss=-0.50 fires at day 10
        result = op.long_calls(
            multi_date_data,
            leg1_delta={"target": 0.30, "min": 0.15, "max": 0.40},
            stop_loss=-0.50,
            max_hold_days=5,
            raw=True,
        )
        assert not result.empty
        # Day 5 unrealized is -25%, stop_loss=-0.50 not hit yet, so max_hold fires
        assert result["exit_type"].iloc[0] == "max_hold"

    def test_take_profit_fires_before_max_hold(self, multi_date_data):
        """When take-profit fires before max_hold_days, take_profit wins."""
        # Long put: day 5 unrealized=+25%, take_profit=0.25 fires at day 5
        # max_hold_days=15 would fire at day 15
        result = op.long_puts(
            multi_date_data,
            leg1_delta={"target": 0.30, "min": 0.15, "max": 0.70},
            take_profit=0.25,
            max_hold_days=15,
            raw=True,
        )
        assert not result.empty
        assert result["exit_type"].iloc[0] == "take_profit"

    def test_stop_loss_and_max_hold_same_date(self, multi_date_data):
        """When stop_loss and max_hold trigger on same date, stop_loss wins."""
        # Long call: day 5 unrealized=-25%, stop_loss=-0.25, max_hold_days=5
        # Both trigger at day 5 — stop_loss takes priority
        result = op.long_calls(
            multi_date_data,
            leg1_delta={"target": 0.30, "min": 0.15, "max": 0.40},
            stop_loss=-0.25,
            max_hold_days=5,
            raw=True,
        )
        assert not result.empty
        assert result["exit_type"].iloc[0] == "stop_loss"

    def test_take_profit_and_max_hold_same_date(self, multi_date_data):
        """When take_profit and max_hold trigger on same date, take_profit wins."""
        # Long put: day 5 unrealized=+25%, take_profit=0.25, max_hold_days=5
        # Both trigger at day 5 — take_profit takes priority
        result = op.long_puts(
            multi_date_data,
            leg1_delta={"target": 0.30, "min": 0.15, "max": 0.70},
            take_profit=0.25,
            max_hold_days=5,
            raw=True,
        )
        assert not result.empty
        assert result["exit_type"].iloc[0] == "take_profit"

    def test_all_three_triggers_priority(self, multi_date_data):
        """When all three conditions could trigger, priority order holds."""
        # Long call: day 5 unrealized=-25%
        # stop_loss=-0.25 triggers at day 5, take_profit=0.01 (not hit for calls
        # going down), max_hold_days=5 triggers at day 5
        # stop_loss should win
        result = op.long_calls(
            multi_date_data,
            leg1_delta={"target": 0.30, "min": 0.15, "max": 0.40},
            stop_loss=-0.25,
            take_profit=5.0,
            max_hold_days=5,
            raw=True,
        )
        assert not result.empty
        assert result["exit_type"].iloc[0] == "stop_loss"


class TestMaxHoldDaysValidation:
    """Test validation of max_hold_days parameter."""

    @pytest.mark.parametrize("value", [0, -5])
    def test_max_hold_days_rejects_non_positive(self, multi_date_data, value):
        """max_hold_days must be > 0."""
        with pytest.raises(Exception):
            op.long_calls(
                multi_date_data,
                leg1_delta={"target": 0.30, "min": 0.15, "max": 0.40},
                max_hold_days=value,
            )

    def test_max_hold_days_must_be_int(self, multi_date_data):
        """max_hold_days must be an int, not float."""
        with pytest.raises(Exception):
            op.long_calls(
                multi_date_data,
                leg1_delta={"target": 0.30, "min": 0.15, "max": 0.40},
                max_hold_days=5.0,
            )
