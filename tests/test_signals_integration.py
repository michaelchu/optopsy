"""Integration tests: entry/exit signal filtering, DTE tolerance, and E2E TA signal tests."""

import datetime

import pandas as pd
import pytest

from optopsy.signals import (
    and_signals,
    atr_above,
    day_of_week,
    rsi_above,
    rsi_below,
    signal_dates,
    sma_above,
    sustained,
)
from optopsy.strategies import long_calls, short_puts

# ============================================================================
# Local fixtures
# ============================================================================


@pytest.fixture
def sparse_exit_data():
    """
    Option data where exact exit DTE=0 (expiration day) data is missing,
    but DTE=1 data exists. Tests that exit_dte_tolerance can find nearby exits.

    Entry: 2018-01-03, underlying=213.93, DTE=28
    Missing: 2018-01-31 (expiration day, DTE=0)
    Available: 2018-01-30 (DTE=1)
    """
    entry_date = datetime.datetime(2018, 1, 3)
    exp_date = datetime.datetime(2018, 1, 31)
    near_exit_date = datetime.datetime(2018, 1, 30)  # DTE=1

    cols = [
        "underlying_symbol",
        "option_type",
        "expiration",
        "quote_date",
        "strike",
        "bid",
        "ask",
        "delta",
    ]

    d = [
        # Entry day (DTE=28)
        ["SPX", "call", exp_date, entry_date, 212.5, 7.35, 7.45, 0.50],
        ["SPX", "call", exp_date, entry_date, 215.0, 6.00, 6.05, 0.30],
        ["SPX", "put", exp_date, entry_date, 212.5, 5.70, 5.80, -0.30],
        ["SPX", "put", exp_date, entry_date, 215.0, 7.10, 7.20, -0.50],
        # Near-exit day (DTE=1, one day before expiration)
        # No DTE=0 data exists!
        ["SPX", "call", exp_date, near_exit_date, 212.5, 7.20, 7.30, 0.50],
        ["SPX", "call", exp_date, near_exit_date, 215.0, 4.80, 4.90, 0.30],
        ["SPX", "put", exp_date, near_exit_date, 212.5, 0.15, 0.25, -0.30],
        ["SPX", "put", exp_date, near_exit_date, 215.0, 0.30, 0.40, -0.50],
    ]
    return pd.DataFrame(data=d, columns=cols)


@pytest.fixture
def multi_exit_dte_data():
    """
    Option data with multiple possible exit DTEs for testing closest-match logic.

    Entry: 2018-01-03, DTE=28
    Available exits: DTE=3 (2018-01-28), DTE=1 (2018-01-30), DTE=0 not available
    With exit_dte=0, tolerance=3 should pick DTE=1 (closest to 0).
    """
    entry_date = datetime.datetime(2018, 1, 3)
    exp_date = datetime.datetime(2018, 1, 31)
    exit_dte3 = datetime.datetime(2018, 1, 28)  # DTE=3
    exit_dte1 = datetime.datetime(2018, 1, 30)  # DTE=1

    cols = [
        "underlying_symbol",
        "option_type",
        "expiration",
        "quote_date",
        "strike",
        "bid",
        "ask",
        "delta",
    ]

    d = [
        # Entry (DTE=28)
        ["SPX", "call", exp_date, entry_date, 212.5, 7.35, 7.45, 0.30],
        ["SPX", "put", exp_date, entry_date, 212.5, 5.70, 5.80, -0.30],
        # Exit at DTE=3
        ["SPX", "call", exp_date, exit_dte3, 212.5, 5.90, 6.00, 0.30],
        ["SPX", "put", exp_date, exit_dte3, 212.5, 0.40, 0.50, -0.30],
        # Exit at DTE=1 (closer to target of 0)
        ["SPX", "call", exp_date, exit_dte1, 212.5, 7.20, 7.30, 0.30],
        ["SPX", "put", exp_date, exit_dte1, 212.5, 0.15, 0.25, -0.30],
    ]
    return pd.DataFrame(data=d, columns=cols)


# ============================================================================
# Entry signal integration
# ============================================================================


class TestEntrySignalIntegration:
    def test_day_of_week_filters_entries(self, option_data_entry_exit):
        """entry_dates from day_of_week(3) should only include Thursday entries."""
        # Without signal - should include both Wednesday and Thursday entries
        results_all = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            raw=True,
        )

        # With Thursday-only dates
        entry_dates = signal_dates(option_data_entry_exit, day_of_week(3))
        results_thu = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            entry_dates=entry_dates,
            raw=True,
        )

        # Thursday results should be a subset of all results
        assert len(results_thu) <= len(results_all)
        assert len(results_thu) > 0

    def test_signal_filters_no_match_returns_empty(self, option_data_entry_exit):
        """entry_dates with no matches should return empty DataFrame."""
        # Saturday signal on weekday data -> no matches
        entry_dates = signal_dates(option_data_entry_exit, day_of_week(5))
        results = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            entry_dates=entry_dates,
            raw=True,
        )
        assert len(results) == 0

    def test_always_true_signal_same_as_no_signal(
        self, option_data_entry_exit, always_true_signal
    ):
        """entry_dates from always-True signal should give same results as no dates."""
        results_no_signal = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            raw=True,
        )

        entry_dates = signal_dates(option_data_entry_exit, always_true_signal)
        results_true_signal = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            entry_dates=entry_dates,
            raw=True,
        )

        pd.testing.assert_frame_equal(results_no_signal, results_true_signal)

    def test_entry_dates_with_short_puts(self, option_data_entry_exit):
        """entry_dates should work with short put strategies too."""
        entry_dates = signal_dates(option_data_entry_exit, day_of_week(3))
        results = short_puts(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            entry_dates=entry_dates,
            raw=True,
        )
        # Should return results (Thursday has put data)
        assert isinstance(results, pd.DataFrame)

    def test_invalid_entry_dates_raises(self, option_data_entry_exit):
        """Non-DataFrame entry_dates should raise ValueError."""
        with pytest.raises(ValueError, match="entry_dates"):
            long_calls(
                option_data_entry_exit,
                max_entry_dte=90,
                exit_dte=0,
                entry_dates="not_a_dataframe",
                raw=True,
            )

    def test_combined_signal_integration(
        self, option_data_entry_exit, always_true_signal
    ):
        """Combined signals should work end-to-end with strategies."""
        # Combine Thursday + always True (effectively just Thursday)
        combined = and_signals(day_of_week(3), always_true_signal)

        entry_dates_combined = signal_dates(option_data_entry_exit, combined)
        results_combined = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            entry_dates=entry_dates_combined,
            raw=True,
        )

        entry_dates_thu = signal_dates(option_data_entry_exit, day_of_week(3))
        results_thu = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            entry_dates=entry_dates_thu,
            raw=True,
        )

        pd.testing.assert_frame_equal(results_combined, results_thu)


# ============================================================================
# Exit signal integration
# ============================================================================


class TestExitSignalIntegration:
    def test_exit_dates_filters_exits(self, option_data_entry_exit):
        """exit_dates should filter which exit dates are valid."""
        # Without dates
        results_all = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            raw=True,
        )

        # With exit dates that match the exit date (Saturday Feb 3 -> dayofweek=5)
        # The expiration date 2018-02-03 is a Saturday
        exit_dates = signal_dates(option_data_entry_exit, day_of_week(5))
        results_sat = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            exit_dates=exit_dates,
            raw=True,
        )

        # Saturday matches the exit date, so results should be the same
        assert len(results_sat) == len(results_all)

    def test_exit_dates_no_match_returns_empty(self, option_data_entry_exit):
        """exit_dates with no matches should return empty DataFrame."""
        # The exit date (2018-02-03) is Saturday. Filter for Monday exits only.
        exit_dates = signal_dates(option_data_entry_exit, day_of_week(0))
        results = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            exit_dates=exit_dates,
            raw=True,
        )
        assert len(results) == 0

    def test_always_true_exit_dates_same_as_no_dates(
        self, option_data_entry_exit, always_true_signal
    ):
        """exit_dates from always-True signal should give same results as no dates."""
        results_no_signal = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            raw=True,
        )

        exit_dates = signal_dates(option_data_entry_exit, always_true_signal)
        results_true_signal = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            exit_dates=exit_dates,
            raw=True,
        )

        pd.testing.assert_frame_equal(results_no_signal, results_true_signal)

    def test_entry_and_exit_dates_combined(
        self, option_data_entry_exit, always_true_signal
    ):
        """entry_dates and exit_dates should both be applied independently."""
        # Entry on Thursday only, exit any time
        entry_dates = signal_dates(option_data_entry_exit, day_of_week(3))
        results_entry_only = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            entry_dates=entry_dates,
            raw=True,
        )

        # Entry on Thursday, exit dates always true (no additional filtering)
        exit_dates = signal_dates(option_data_entry_exit, always_true_signal)
        results_both = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            entry_dates=entry_dates,
            exit_dates=exit_dates,
            raw=True,
        )

        pd.testing.assert_frame_equal(results_entry_only, results_both)

    def test_exit_dates_with_short_puts(
        self, option_data_entry_exit, always_true_signal
    ):
        """exit_dates should work with short put strategies."""
        results_no_signal = short_puts(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            raw=True,
        )

        exit_dates = signal_dates(option_data_entry_exit, always_true_signal)
        results_with_dates = short_puts(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            exit_dates=exit_dates,
            raw=True,
        )

        pd.testing.assert_frame_equal(results_no_signal, results_with_dates)

    def test_invalid_exit_dates_raises(self, option_data_entry_exit):
        """Non-DataFrame exit_dates should raise ValueError."""
        with pytest.raises(ValueError, match="exit_dates"):
            long_calls(
                option_data_entry_exit,
                max_entry_dte=90,
                exit_dte=0,
                exit_dates="not_a_dataframe",
                raw=True,
            )

    def test_exit_dates_price_based(self, option_data_entry_exit, stock_data_spx):
        """exit_dates based on price threshold should filter correctly."""

        # Exit only when underlying price > 215
        # Exit date has close=220, so this should pass
        def price_above_215(data):
            return data["close"] > 215

        exit_dates = signal_dates(stock_data_spx, price_above_215)
        results = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            exit_dates=exit_dates,
            raw=True,
        )

        results_all = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            raw=True,
        )

        # Exit price is 220 > 215, so all trades should pass
        pd.testing.assert_frame_equal(results, results_all)

    def test_exit_dates_price_based_filters_out(
        self, option_data_entry_exit, stock_data_spx
    ):
        """exit_dates with price condition that fails should filter trades."""

        # Exit only when underlying price > 225
        # Exit date has close=220, so this should filter everything
        def price_above_225(data):
            return data["close"] > 225

        exit_dates = signal_dates(stock_data_spx, price_above_225)
        results = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            exit_dates=exit_dates,
            raw=True,
        )

        assert len(results) == 0


# ============================================================================
# Exit DTE tolerance
# ============================================================================


class TestExitDteTolerance:
    def test_zero_tolerance_is_default(self, option_data_entry_exit):
        """Default tolerance=0 should behave identically to original behavior."""
        results_default = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            raw=True,
        )

        results_explicit = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            exit_dte_tolerance=0,
            raw=True,
        )

        pd.testing.assert_frame_equal(results_default, results_explicit)

    def test_exact_dte_missing_zero_tolerance_returns_empty(self, sparse_exit_data):
        """Without tolerance, missing exact exit DTE should return no results."""
        results = long_calls(
            sparse_exit_data,
            max_entry_dte=90,
            exit_dte=0,
            exit_dte_tolerance=0,
            raw=True,
        )
        assert len(results) == 0

    def test_tolerance_finds_nearby_exit(self, sparse_exit_data):
        """With tolerance, should find nearby DTE when exact is missing."""
        results = long_calls(
            sparse_exit_data,
            max_entry_dte=90,
            exit_dte=0,
            exit_dte_tolerance=1,
            raw=True,
        )
        # DTE=1 data exists and is within tolerance
        assert len(results) > 0

    def test_tolerance_picks_closest_dte(self, multi_exit_dte_data):
        """With multiple DTEs in range, should pick closest to target."""
        results = long_calls(
            multi_exit_dte_data,
            max_entry_dte=90,
            exit_dte=0,
            exit_dte_tolerance=3,
            raw=True,
            slippage="mid",
        )
        assert len(results) > 0
        # The exit price should come from DTE=1 (underlying 219.50),
        # not DTE=3 (underlying 218.00)
        row = results.iloc[0]
        # exit mid price for 212.5 call at DTE=1 = (7.20+7.30)/2 = 7.25
        assert round(row["exit"], 2) == 7.25

    def test_tolerance_insufficient_still_empty(self, sparse_exit_data):
        """Tolerance that's too small should still return empty."""
        # Exact DTE=5 is missing, DTE=1 exists but is 4 away
        results = long_calls(
            sparse_exit_data,
            max_entry_dte=90,
            exit_dte=5,
            exit_dte_tolerance=1,  # DTE 4-6, but only DTE=1 exists
            raw=True,
        )
        assert len(results) == 0

    def test_tolerance_with_exit_dates(self, sparse_exit_data, always_true_signal):
        """exit_dte_tolerance should work alongside exit_dates."""
        exit_dates = signal_dates(sparse_exit_data, always_true_signal)
        results = long_calls(
            sparse_exit_data,
            max_entry_dte=90,
            exit_dte=0,
            exit_dte_tolerance=1,
            exit_dates=exit_dates,
            raw=True,
        )
        assert len(results) > 0

    def test_tolerance_with_entry_dates(self, sparse_exit_data, always_true_signal):
        """exit_dte_tolerance should work alongside entry_dates."""
        entry_dates = signal_dates(sparse_exit_data, always_true_signal)
        results = long_calls(
            sparse_exit_data,
            max_entry_dte=90,
            exit_dte=0,
            exit_dte_tolerance=1,
            entry_dates=entry_dates,
            raw=True,
        )
        assert len(results) > 0

    def test_tolerance_exact_match_preferred(self, option_data_entry_exit):
        """When exact DTE exists, tolerance shouldn't change results."""
        results_exact = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            exit_dte_tolerance=0,
            raw=True,
        )

        results_tolerant = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            exit_dte_tolerance=5,
            raw=True,
        )

        # Same number of results and same exit prices (exact match wins)
        pd.testing.assert_frame_equal(results_exact, results_tolerant)


# ============================================================================
# signal_dates() tests
# ============================================================================


class TestSignalDates:
    """Tests for the signal_dates() function that decouples signal computation."""

    @pytest.fixture
    def ohlcv_stock_data(self):
        """OHLCV stock data suitable for signal computation."""
        dates = pd.date_range("2018-01-01", periods=30, freq="B")
        # Calm first half, volatile second half
        close = [100.0] * 14 + [100 + ((-1) ** i) * (i * 3) for i in range(16)]
        high = [c + 1.0 for c in close]
        low = [c - 1.0 for c in close]
        return pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "open": close,
                "high": high,
                "low": low,
                "close": close,
                "volume": [1000000] * 30,
            }
        )

    def test_signal_dates_returns_dates_dataframe(self, ohlcv_stock_data):
        """signal_dates should return a DataFrame with (underlying_symbol, quote_date)."""

        def always_true(d):
            return pd.Series(True, index=d.index)

        result = signal_dates(ohlcv_stock_data, always_true)
        assert isinstance(result, pd.DataFrame)
        assert "underlying_symbol" in result.columns
        assert "quote_date" in result.columns
        assert len(result.columns) == 2

    def test_signal_dates_close_maps_to_underlying_price(self, ohlcv_stock_data):
        """signal_dates should auto-map 'close' to 'underlying_price' for TA signals."""
        # This signal reads underlying_price — should work when only close is present
        sig = sma_above(period=10)
        result = signal_dates(ohlcv_stock_data, sig)
        assert isinstance(result, pd.DataFrame)

    def test_signal_dates_all_true_returns_all_dates(self, ohlcv_stock_data):
        """signal_dates with always-true signal returns all unique dates."""

        def always_true(d):
            return pd.Series(True, index=d.index)

        result = signal_dates(ohlcv_stock_data, always_true)
        n_unique = ohlcv_stock_data.drop_duplicates(
            ["underlying_symbol", "quote_date"]
        ).shape[0]
        assert len(result) == n_unique

    def test_signal_dates_all_false_returns_empty(self, ohlcv_stock_data):
        """signal_dates with always-false signal returns empty DataFrame."""

        def always_false(d):
            return pd.Series(False, index=d.index)

        result = signal_dates(ohlcv_stock_data, always_false)
        assert len(result) == 0
        assert "underlying_symbol" in result.columns
        assert "quote_date" in result.columns

    def test_signal_dates_date_only_signal(self, ohlcv_stock_data):
        """Date-based signals (e.g. day_of_week) work with signal_dates."""
        result = signal_dates(ohlcv_stock_data, day_of_week(3))
        assert isinstance(result, pd.DataFrame)
        # All flagged dates should be Thursdays
        assert (result["quote_date"].dt.dayofweek == 3).all()

    def test_signal_dates_entry_dates_accepted_by_strategy(
        self, option_data_entry_exit, ohlcv_stock_data
    ):
        """entry_dates from signal_dates are accepted by strategy functions."""

        def always_true(d):
            return pd.Series(True, index=d.index)

        entry_dates = signal_dates(ohlcv_stock_data, always_true)
        results = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            entry_dates=entry_dates,
            raw=True,
        )
        assert isinstance(results, pd.DataFrame)

    def test_signal_dates_with_combined_signal(self, ohlcv_stock_data):
        """signal_dates works with combined signals (and_signals, Signal class)."""

        def always_true(d):
            return pd.Series(True, index=d.index)

        combined = and_signals(day_of_week(0, 1, 2, 3, 4), always_true)
        result = signal_dates(ohlcv_stock_data, combined)
        assert isinstance(result, pd.DataFrame)

    def test_signal_dates_with_signal_class(self, ohlcv_stock_data):
        """signal_dates works with Signal objects."""
        from optopsy.signals import signal

        sig = signal(day_of_week(3)) & signal(day_of_week(0, 1, 2, 3, 4))
        result = signal_dates(ohlcv_stock_data, sig)
        assert (result["quote_date"].dt.dayofweek == 3).all()

    def test_atr_uses_real_high_low_when_available(self, ohlcv_stock_data):
        """ATR signal should detect and use high/low columns from stock_data."""
        sig = atr_above(period=14, multiplier=0.0)
        result = sig(
            ohlcv_stock_data.assign(underlying_price=ohlcv_stock_data["close"])
        )
        # With multiplier=0, ATR > 0 should fire after warmup
        assert result.any()

    def test_atr_without_ohlcv_still_works(self):
        """ATR signal should still work with close-only data (no high/low)."""
        dates = pd.date_range("2018-01-01", periods=30, freq="B")
        prices = [100.0] * 14 + [100 + ((-1) ** i) * (i * 3) for i in range(16)]
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "close": prices,
            }
        )
        result = atr_above(period=14, multiplier=0.0)(data)
        assert result.any()

    def test_dates_validation_rejects_non_dataframe(self):
        """entry_dates that is not a DataFrame should be rejected."""
        from pydantic import ValidationError

        from optopsy.types import StrategyParams

        with pytest.raises(ValidationError, match="must be a DataFrame"):
            StrategyParams.model_validate({"entry_dates": "not_a_dataframe"})

    def test_dates_validation_rejects_missing_columns(self):
        """entry_dates missing required columns should be rejected."""
        from pydantic import ValidationError

        from optopsy.types import StrategyParams

        df = pd.DataFrame({"quote_date": [1]})
        with pytest.raises(ValidationError, match="missing required columns"):
            StrategyParams.model_validate({"entry_dates": df})

    def test_dates_validation_accepts_valid(self):
        """Valid dates DataFrame should pass validation."""
        from optopsy.types import StrategyParams

        df = pd.DataFrame(
            {"underlying_symbol": ["SPX"], "quote_date": [pd.Timestamp("2018-01-01")]}
        )
        model = StrategyParams.model_validate({"entry_dates": df})
        assert model.entry_dates is not None

    def test_dates_validation_accepts_none(self):
        """None should pass validation."""
        from optopsy.types import StrategyParams

        model = StrategyParams.model_validate({"entry_dates": None})
        assert model.entry_dates is None


# ============================================================================
# E2E integration: real TA signal + stock_data → core engine → output
# ============================================================================


class TestTASignalE2E:
    """
    End-to-end tests that exercise the full pipeline:
    real pandas_ta signal + signal_dates() → entry_dates/exit_dates → strategy output.
    """

    def _get_entry_dates(self, stock_data_long_history):
        """Return the 4 entry dates used by option_data_with_stock."""
        dates = stock_data_long_history["quote_date"].values
        return {
            "decline": {
                pd.Timestamp(dates[30]),
                pd.Timestamp(dates[55]),
            },
            "recovery": {
                pd.Timestamp(dates[160]),
                pd.Timestamp(dates[170]),
            },
        }

    def _exp_dates(self, stock_data_long_history):
        """Return the 2 expiration dates used by option_data_with_stock."""
        dates = stock_data_long_history["quote_date"].values
        return {
            "A": pd.Timestamp(dates[100]),  # RSI≈14, rsi_above(14,70)=False
            "B": pd.Timestamp(dates[195]),  # RSI≈100, rsi_above(14,70)=True
        }

    def test_sma_entry_dates_filter_entries(
        self, option_data_with_stock, stock_data_long_history
    ):
        """sma_above(20) entry_dates should only keep recovery-phase entries."""
        ed = self._get_entry_dates(stock_data_long_history)

        results_all = long_calls(
            option_data_with_stock,
            max_entry_dte=365,
            exit_dte=0,
            raw=True,
        )
        assert len(results_all) > 0

        entry_dates = signal_dates(stock_data_long_history, sma_above(20))
        results_sma = long_calls(
            option_data_with_stock,
            max_entry_dte=365,
            exit_dte=0,
            entry_dates=entry_dates,
            raw=True,
        )
        assert len(results_sma) > 0
        assert len(results_sma) < len(results_all)

        actual_dates = set(results_sma["quote_date_entry"].unique())
        assert actual_dates.isdisjoint(ed["decline"])

    def test_rsi_entry_dates_with_stock_data(
        self, option_data_with_stock, stock_data_long_history
    ):
        """rsi_below(14, 30) entry_dates should only keep decline-phase entries."""
        ed = self._get_entry_dates(stock_data_long_history)

        entry_dates = signal_dates(stock_data_long_history, rsi_below(14, 30))
        results = short_puts(
            option_data_with_stock,
            max_entry_dte=365,
            exit_dte=0,
            entry_dates=entry_dates,
            raw=True,
        )
        assert len(results) > 0

        actual_dates = set(results["quote_date_entry"].unique())
        assert actual_dates.issubset(ed["decline"])
        assert actual_dates.isdisjoint(ed["recovery"])

    def test_ta_exit_dates_filter_exits(
        self, option_data_with_stock, stock_data_long_history
    ):
        """rsi_above(14, 70) exit_dates should remove expiration-A exits."""
        exps = self._exp_dates(stock_data_long_history)

        results_all = long_calls(
            option_data_with_stock,
            max_entry_dte=365,
            exit_dte=0,
            raw=True,
        )
        assert len(results_all) > 0

        exit_dates = signal_dates(stock_data_long_history, rsi_above(14, 70))
        results_exit = long_calls(
            option_data_with_stock,
            max_entry_dte=365,
            exit_dte=0,
            exit_dates=exit_dates,
            raw=True,
        )
        assert len(results_exit) > 0
        assert len(results_exit) < len(results_all)

        # All surviving rows must have exp-B
        assert set(results_exit["expiration"].unique()) == {exps["B"]}

        # Inverse: rsi_below(14, 30) keeps only exp-A exits
        exit_dates_inv = signal_dates(stock_data_long_history, rsi_below(14, 30))
        results_inverse = long_calls(
            option_data_with_stock,
            max_entry_dte=365,
            exit_dte=0,
            exit_dates=exit_dates_inv,
            raw=True,
        )
        assert len(results_inverse) > 0

        # All surviving inverse rows must have exp-A
        assert set(results_inverse["expiration"].unique()) == {exps["A"]}

    def test_entry_and_exit_dates_both_filter(
        self, option_data_with_stock, stock_data_long_history
    ):
        """Combined entry_dates + exit_dates should both filter independently."""
        ed = self._get_entry_dates(stock_data_long_history)
        exps = self._exp_dates(stock_data_long_history)

        entry_dates = signal_dates(stock_data_long_history, rsi_below(14, 30))
        exit_dates = signal_dates(stock_data_long_history, rsi_above(14, 70))
        results = long_calls(
            option_data_with_stock,
            max_entry_dte=365,
            exit_dte=0,
            entry_dates=entry_dates,
            exit_dates=exit_dates,
            raw=True,
        )
        assert len(results) > 0

        # Verify entry dates are decline-only
        actual_dates = set(results["quote_date_entry"].unique())
        assert actual_dates.issubset(ed["decline"])

        # Verify expiration is B-only
        assert set(results["expiration"].unique()) == {exps["B"]}

        # Cross-check: each individual filter produces more rows
        results_entry_only = long_calls(
            option_data_with_stock,
            max_entry_dte=365,
            exit_dte=0,
            entry_dates=entry_dates,
            raw=True,
        )
        results_exit_only = long_calls(
            option_data_with_stock,
            max_entry_dte=365,
            exit_dte=0,
            exit_dates=exit_dates,
            raw=True,
        )
        assert len(results_entry_only) > 0
        assert len(results_exit_only) > 0
        # Combined is strictly fewer than either individual filter
        assert len(results) < len(results_entry_only)
        assert len(results) < len(results_exit_only)

    def test_sustained_ta_signal_with_signal_dates(
        self, option_data_with_stock, stock_data_long_history
    ):
        """sustained(rsi_below(14, 30), days=3) must reject bar 55."""
        decline_deep = {pd.Timestamp(stock_data_long_history["quote_date"].values[30])}

        # Plain rsi_below keeps both decline entries
        entry_dates_plain = signal_dates(stock_data_long_history, rsi_below(14, 30))
        results_plain = long_calls(
            option_data_with_stock,
            max_entry_dte=365,
            exit_dte=0,
            entry_dates=entry_dates_plain,
            raw=True,
        )
        assert len(results_plain) > 0

        # sustained(days=3) rejects bar 55 (streak < 3 bars)
        entry_dates_sust = signal_dates(
            stock_data_long_history, sustained(rsi_below(14, 30), days=3)
        )
        results_sustained = long_calls(
            option_data_with_stock,
            max_entry_dte=365,
            exit_dte=0,
            entry_dates=entry_dates_sust,
            raw=True,
        )
        assert len(results_sustained) > 0

        # Only bar 30 survives (deep in streak)
        actual_dates = set(results_sustained["quote_date_entry"].unique())
        assert actual_dates == decline_deep

        # Prove sustained is strictly more selective than plain
        assert len(results_sustained) < len(results_plain)

    def test_atr_signal_uses_real_ohlcv(
        self, option_data_with_stock, stock_data_long_history
    ):
        """ATR signal should use real high/low from stock_data when available."""
        sd_full = stock_data_long_history
        sd_close_only = sd_full.drop(columns=["high", "low"])

        entry_dates_ohlcv = signal_dates(sd_full, atr_above(period=14, multiplier=1.0))
        results_ohlcv = long_calls(
            option_data_with_stock,
            max_entry_dte=365,
            exit_dte=0,
            entry_dates=entry_dates_ohlcv,
            raw=True,
        )

        entry_dates_close = signal_dates(
            sd_close_only, atr_above(period=14, multiplier=1.0)
        )
        results_close = long_calls(
            option_data_with_stock,
            max_entry_dte=365,
            exit_dte=0,
            entry_dates=entry_dates_close,
            raw=True,
        )

        assert len(results_ohlcv) > 0
        assert len(results_close) > 0
        # OHLCV data should produce at least as many results as close-only
        assert len(results_ohlcv) >= len(results_close)

        # OHLCV includes bar 160 that close-only misses
        ohlcv_dates = set(results_ohlcv["quote_date_entry"].unique())
        close_dates = set(results_close["quote_date_entry"].unique())
        assert close_dates < ohlcv_dates, (
            "Expected close-only to be a strict subset of OHLCV dates"
        )
