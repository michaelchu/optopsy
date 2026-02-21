"""Tests for entry and exit signal filtering functionality."""

import datetime

import numpy as np
import pandas as pd
import pytest

from optopsy.signals import (
    Signal,
    _compute_rsi,
    and_signals,
    apply_signal,
    atr_above,
    atr_below,
    bb_above_upper,
    bb_below_lower,
    day_of_week,
    ema_cross_above,
    ema_cross_below,
    macd_cross_above,
    macd_cross_below,
    or_signals,
    rsi_above,
    rsi_below,
    signal,
    sma_above,
    sma_below,
    sustained,
)
from optopsy.strategies import long_calls, short_puts

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def always_true_signal():
    """Signal function that always returns True (passes all dates)."""
    return lambda data: pd.Series(True, index=data.index)


@pytest.fixture
def price_data():
    """Simple underlying price data for testing signal functions."""
    dates = pd.date_range("2018-01-01", periods=30, freq="B")
    return pd.DataFrame(
        {
            "underlying_symbol": "SPX",
            "quote_date": dates,
            "underlying_price": [
                # Declining trend then recovering
                100,
                99,
                98,
                97,
                96,
                95,
                94,
                93,
                92,
                91,
                90,
                89,
                88,
                87,
                86,
                85,
                86,
                87,
                88,
                89,
                90,
                91,
                92,
                93,
                94,
                95,
                96,
                97,
                98,
                99,
            ],
        }
    )


@pytest.fixture
def option_data_with_signal():
    """
    Option chain data spanning multiple quote_dates with varying underlying prices.
    Used to test entry_signal integration with strategy functions.

    We need enough quote_dates for RSI calculation (14+ periods) plus
    dates that satisfy entry DTE and exit DTE conditions.
    """
    # Use business days to have well-defined day-of-week
    quote_dates = pd.date_range("2018-01-01", periods=5, freq="B")
    # quote_dates:
    #   2018-01-01 (Monday)
    #   2018-01-02 (Tuesday)
    #   2018-01-03 (Wednesday)
    #   2018-01-04 (Thursday)
    #   2018-01-05 (Friday)

    exp_date = datetime.datetime(2018, 2, 2)  # ~30 DTE

    cols = [
        "underlying_symbol",
        "underlying_price",
        "option_type",
        "expiration",
        "quote_date",
        "strike",
        "bid",
        "ask",
    ]

    rows = []
    prices = [100.0, 99.0, 98.0, 97.0, 96.0]
    for i, qd in enumerate(quote_dates):
        price = prices[i]
        # Calls
        rows.append(["SPX", price, "call", exp_date, qd, 95.0, 6.0, 6.10])
        rows.append(["SPX", price, "call", exp_date, qd, 100.0, 3.0, 3.10])
        rows.append(["SPX", price, "call", exp_date, qd, 105.0, 1.0, 1.10])
        # Puts
        rows.append(["SPX", price, "put", exp_date, qd, 95.0, 1.0, 1.10])
        rows.append(["SPX", price, "put", exp_date, qd, 100.0, 3.0, 3.10])
        rows.append(["SPX", price, "put", exp_date, qd, 105.0, 6.0, 6.10])

    return pd.DataFrame(data=rows, columns=cols)


# ============================================================================
# Unit tests for signal functions
# ============================================================================


class TestComputeRSI:
    def test_rsi_constant_price(self):
        """RSI should be NaN when prices don't change."""
        prices = pd.Series([100.0] * 20)
        rsi = _compute_rsi(prices, period=14)
        # With no price change, gain and loss are 0, RSI is undefined
        assert rsi.iloc[:14].isna().all()

    def test_rsi_trending_down(self):
        """RSI should be low when prices are consistently declining."""
        prices = pd.Series([100.0 - i for i in range(20)])
        rsi = _compute_rsi(prices, period=14)
        # Strong downtrend should produce low RSI
        assert rsi.iloc[-1] < 15

    def test_rsi_trending_up(self):
        """RSI should be high when prices are consistently rising."""
        prices = pd.Series([100.0 + i for i in range(20)])
        rsi = _compute_rsi(prices, period=14)
        # Strong uptrend should produce high RSI
        assert rsi.iloc[-1] > 85

    def test_rsi_range(self):
        """RSI values should be between 0 and 100."""
        np.random.seed(42)
        prices = pd.Series(np.cumsum(np.random.randn(100)) + 100)
        rsi = _compute_rsi(prices, period=14)
        valid_rsi = rsi.dropna()
        assert (valid_rsi >= 0).all()
        assert (valid_rsi <= 100).all()

    def test_rsi_insufficient_data(self):
        """RSI should be NaN when there's insufficient data for the period."""
        prices = pd.Series([100.0, 101.0, 102.0])
        rsi = _compute_rsi(prices, period=14)
        assert rsi.isna().all()


class TestRSISignals:
    def test_rsi_below(self, price_data):
        """rsi_below should flag oversold conditions."""
        signal = rsi_below(period=14, threshold=30)
        result = signal(price_data)
        assert isinstance(result, pd.Series)
        assert result.dtype == bool
        assert len(result) == len(price_data)

    def test_rsi_above(self, price_data):
        """rsi_above should flag overbought conditions."""
        signal = rsi_above(period=14, threshold=70)
        result = signal(price_data)
        assert isinstance(result, pd.Series)
        assert result.dtype == bool
        assert len(result) == len(price_data)

    def test_rsi_below_strong_downtrend(self):
        """rsi_below should fire during strong downtrends."""
        dates = pd.date_range("2018-01-01", periods=20, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0 - i for i in range(20)],
            }
        )
        signal = rsi_below(period=14, threshold=30)
        result = signal(data)
        # After 14+ periods of decline, RSI should be below 30
        assert result.iloc[-1] == True

    def test_rsi_above_strong_uptrend(self):
        """rsi_above should fire during strong uptrends."""
        dates = pd.date_range("2018-01-01", periods=20, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0 + i for i in range(20)],
            }
        )
        signal = rsi_above(period=14, threshold=70)
        result = signal(data)
        # After 14+ periods of gains, RSI should be above 70
        assert result.iloc[-1] == True


class TestDayOfWeek:
    def test_day_of_week_thursday(self, price_data):
        """day_of_week(3) should only flag Thursdays."""
        signal = day_of_week(3)
        result = signal(price_data)
        # Verify all True entries are actually Thursdays
        flagged_days = price_data.loc[result, "quote_date"].dt.dayofweek
        assert (flagged_days == 3).all()

    def test_day_of_week_multiple(self, price_data):
        """day_of_week with multiple days should flag all specified days."""
        signal = day_of_week(0, 4)  # Monday and Friday
        result = signal(price_data)
        flagged_days = price_data.loc[result, "quote_date"].dt.dayofweek
        assert flagged_days.isin([0, 4]).all()

    def test_day_of_week_no_matches(self):
        """day_of_week for weekend on weekday data should return all False."""
        dates = pd.date_range("2018-01-01", periods=5, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": 100.0,
            }
        )
        signal = day_of_week(5, 6)  # Saturday, Sunday
        result = signal(data)
        assert not result.any()


class TestSMASignals:
    def test_sma_below_declining(self):
        """sma_below should fire when price drops below its moving average."""
        dates = pd.date_range("2018-01-01", periods=25, freq="B")
        # Price starts high then drops
        prices = [110.0] * 15 + [100.0 - i for i in range(10)]
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": prices,
            }
        )
        signal = sma_below(period=10)
        result = signal(data)
        # After the price drops, it should be below the SMA
        assert result.iloc[-1] == True

    def test_sma_above_rising(self):
        """sma_above should fire when price is above its moving average."""
        dates = pd.date_range("2018-01-01", periods=25, freq="B")
        # Price starts low then rises
        prices = [90.0] * 15 + [100.0 + i for i in range(10)]
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": prices,
            }
        )
        signal = sma_above(period=10)
        result = signal(data)
        # After price rises, it should be above the SMA
        assert result.iloc[-1] == True


class TestSignalCombinators:
    def test_and_signals(self, price_data, always_true_signal):
        """and_signals should require all signals to be True."""

        def always_false(data):
            return pd.Series(False, index=data.index)

        result = and_signals(always_true_signal, always_true_signal)(price_data)
        assert result.all()

        result = and_signals(always_true_signal, always_false)(price_data)
        assert not result.any()

    def test_or_signals(self, price_data, always_true_signal):
        """or_signals should require at least one signal to be True."""

        def always_false(data):
            return pd.Series(False, index=data.index)

        result = or_signals(always_true_signal, always_false)(price_data)
        assert result.all()

        result = or_signals(always_false, always_false)(price_data)
        assert not result.any()

    def test_and_signals_with_real_signals(self, price_data):
        """and_signals should work with actual signal functions."""
        signal = and_signals(day_of_week(0, 1, 2, 3, 4), sma_below(period=5))
        result = signal(price_data)
        assert isinstance(result, pd.Series)
        assert result.dtype == bool


# ============================================================================
# Integration tests: entry_signal with strategy functions
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
        entry_dates = apply_signal(option_data_entry_exit, day_of_week(3))
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
        entry_dates = apply_signal(option_data_entry_exit, day_of_week(5))
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

        entry_dates = apply_signal(option_data_entry_exit, always_true_signal)
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
        entry_dates = apply_signal(option_data_entry_exit, day_of_week(3))
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

        entry_dates_combined = apply_signal(option_data_entry_exit, combined)
        results_combined = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            entry_dates=entry_dates_combined,
            raw=True,
        )

        entry_dates_thu = apply_signal(option_data_entry_exit, day_of_week(3))
        results_thu = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            entry_dates=entry_dates_thu,
            raw=True,
        )

        pd.testing.assert_frame_equal(results_combined, results_thu)


# ============================================================================
# Integration tests: exit_signal with strategy functions
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
        exit_dates = apply_signal(option_data_entry_exit, day_of_week(5))
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
        exit_dates = apply_signal(option_data_entry_exit, day_of_week(0))
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

        exit_dates = apply_signal(option_data_entry_exit, always_true_signal)
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
        entry_dates = apply_signal(option_data_entry_exit, day_of_week(3))
        results_entry_only = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            entry_dates=entry_dates,
            raw=True,
        )

        # Entry on Thursday, exit dates always true (no additional filtering)
        exit_dates = apply_signal(option_data_entry_exit, always_true_signal)
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

        exit_dates = apply_signal(option_data_entry_exit, always_true_signal)
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
        # Exit date has underlying_price=220, so this should pass
        def price_above_215(data):
            return data["underlying_price"] > 215

        exit_dates = apply_signal(stock_data_spx, price_above_215)
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
        # Exit date has underlying_price=220, so this should filter everything
        def price_above_225(data):
            return data["underlying_price"] > 225

        exit_dates = apply_signal(stock_data_spx, price_above_225)
        results = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            exit_dates=exit_dates,
            raw=True,
        )

        assert len(results) == 0


# ============================================================================
# Tests for exit_dte_tolerance
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
        "underlying_price",
        "option_type",
        "expiration",
        "quote_date",
        "strike",
        "bid",
        "ask",
    ]

    d = [
        # Entry day (DTE=28)
        ["SPX", 213.93, "call", exp_date, entry_date, 212.5, 7.35, 7.45],
        ["SPX", 213.93, "call", exp_date, entry_date, 215.0, 6.00, 6.05],
        ["SPX", 213.93, "put", exp_date, entry_date, 212.5, 5.70, 5.80],
        ["SPX", 213.93, "put", exp_date, entry_date, 215.0, 7.10, 7.20],
        # Near-exit day (DTE=1, one day before expiration)
        # No DTE=0 data exists!
        ["SPX", 219.50, "call", exp_date, near_exit_date, 212.5, 7.20, 7.30],
        ["SPX", 219.50, "call", exp_date, near_exit_date, 215.0, 4.80, 4.90],
        ["SPX", 219.50, "put", exp_date, near_exit_date, 212.5, 0.15, 0.25],
        ["SPX", 219.50, "put", exp_date, near_exit_date, 215.0, 0.30, 0.40],
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
        "underlying_price",
        "option_type",
        "expiration",
        "quote_date",
        "strike",
        "bid",
        "ask",
    ]

    d = [
        # Entry (DTE=28)
        ["SPX", 213.93, "call", exp_date, entry_date, 212.5, 7.35, 7.45],
        ["SPX", 213.93, "put", exp_date, entry_date, 212.5, 5.70, 5.80],
        # Exit at DTE=3
        ["SPX", 218.00, "call", exp_date, exit_dte3, 212.5, 5.90, 6.00],
        ["SPX", 218.00, "put", exp_date, exit_dte3, 212.5, 0.40, 0.50],
        # Exit at DTE=1 (closer to target of 0)
        ["SPX", 219.50, "call", exp_date, exit_dte1, 212.5, 7.20, 7.30],
        ["SPX", 219.50, "put", exp_date, exit_dte1, 212.5, 0.15, 0.25],
    ]
    return pd.DataFrame(data=d, columns=cols)


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
        exit_dates = apply_signal(sparse_exit_data, always_true_signal)
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
        entry_dates = apply_signal(sparse_exit_data, always_true_signal)
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
# Fixtures for new TA signal tests
# ============================================================================


@pytest.fixture
def macd_price_data_bullish():
    """80 bars: long decline then sharp recovery to force a bullish MACD crossover.

    With MACD(12,26,9) defaults the signal line lags the MACD line, so after
    a sustained decline the MACD is deeply negative. A sharp recovery makes
    the MACD line turn up faster than the signal line, producing a cross-above.
    80 bars ensures enough warmup (~47 bars) for the crossover to be real.
    """
    dates = pd.date_range("2018-01-01", periods=80, freq="B")
    prices = [100.0 - i * 0.5 for i in range(50)] + [75.0 + i * 2.0 for i in range(30)]
    return pd.DataFrame(
        {
            "underlying_symbol": "SPX",
            "quote_date": dates,
            "underlying_price": prices,
        }
    )


@pytest.fixture
def bb_spike_data():
    """30 bars: stable then a dramatic spike far above the upper Bollinger Band.

    With 25 bars at 100.0 the std ≈ 0, so 2σ bands are very tight.
    The spike to 200 is well above any reasonable upper band.
    """
    dates = pd.date_range("2018-01-01", periods=30, freq="B")
    prices = [100.0] * 25 + [200.0, 201.0, 202.0, 203.0, 204.0]
    return pd.DataFrame(
        {
            "underlying_symbol": "SPX",
            "quote_date": dates,
            "underlying_price": prices,
        }
    )


@pytest.fixture
def ema_cross_data():
    """60 bars: flat then sharply rising to force fast EMA above slow EMA."""
    dates = pd.date_range("2018-01-01", periods=60, freq="B")
    prices = [100.0] * 30 + [100.0 + i * 2 for i in range(30)]
    return pd.DataFrame(
        {
            "underlying_symbol": "SPX",
            "quote_date": dates,
            "underlying_price": prices,
        }
    )


@pytest.fixture
def volatile_price_data():
    """30 bars: calm first half then large swings in second half."""
    dates = pd.date_range("2018-01-01", periods=30, freq="B")
    prices = [100.0] * 14 + [100 + ((-1) ** i) * (i * 3) for i in range(16)]
    return pd.DataFrame(
        {
            "underlying_symbol": "SPX",
            "quote_date": dates,
            "underlying_price": prices,
        }
    )


@pytest.fixture
def multi_symbol_price_data():
    """Two symbols with opposite trends: SPX declining, NDX rising."""
    dates = pd.date_range("2018-01-01", periods=20, freq="B")
    rows = []
    for i, d in enumerate(dates):
        rows.append(
            {"underlying_symbol": "SPX", "quote_date": d, "underlying_price": 100.0 - i}
        )
        rows.append(
            {"underlying_symbol": "NDX", "quote_date": d, "underlying_price": 100.0 + i}
        )
    return pd.DataFrame(rows)


# ============================================================================
# MACD crossover signal tests
# ============================================================================


class TestMACDSignals:
    def test_macd_cross_above_returns_bool_series(self, macd_price_data_bullish):
        result = macd_cross_above()(macd_price_data_bullish)
        assert isinstance(result, pd.Series)
        assert result.dtype == bool

    def test_macd_cross_below_returns_bool_series(self, macd_price_data_bullish):
        result = macd_cross_below()(macd_price_data_bullish)
        assert isinstance(result, pd.Series)
        assert result.dtype == bool

    def test_macd_cross_above_fires_after_v_recovery(self, macd_price_data_bullish):
        """MACD cross above should fire at least once after a V-shaped recovery."""
        result = macd_cross_above()(macd_price_data_bullish)
        assert (
            result.any()
        ), "Expected at least one bullish MACD crossover in V-recovery"

    def test_macd_cross_above_not_always_true(self, macd_price_data_bullish):
        """Crossover is an event, not a state — should not be True on every bar."""
        result = macd_cross_above()(macd_price_data_bullish)
        assert not result.all()

    def test_macd_cross_above_below_mutually_exclusive(self, macd_price_data_bullish):
        """Cross above and cross below cannot fire on the same bar."""
        above = macd_cross_above()(macd_price_data_bullish)
        below = macd_cross_below()(macd_price_data_bullish)
        assert not (above & below).any(), "Same bar cannot cross both above and below"

    def test_macd_insufficient_data_returns_all_false(self):
        """With fewer bars than warmup, MACD should return all False (no signals)."""
        dates = pd.date_range("2018-01-01", periods=10, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0 + i for i in range(10)],
            }
        )
        result = macd_cross_above()(data)
        assert not result.any()

    def test_macd_cross_above_length_matches_input(self, macd_price_data_bullish):
        result = macd_cross_above()(macd_price_data_bullish)
        assert len(result) == len(macd_price_data_bullish)


# ============================================================================
# Bollinger Band signal tests
# ============================================================================


class TestBollingerBandSignals:
    def test_bb_above_upper_returns_bool_series(self, bb_spike_data):
        result = bb_above_upper()(bb_spike_data)
        assert isinstance(result, pd.Series)
        assert result.dtype == bool

    def test_bb_below_lower_returns_bool_series(self, bb_spike_data):
        result = bb_below_lower()(bb_spike_data)
        assert isinstance(result, pd.Series)
        assert result.dtype == bool

    def test_bb_above_upper_fires_on_spike(self, bb_spike_data):
        """Price spike above bands should trigger bb_above_upper on at least one bar."""
        result = bb_above_upper(length=20, std=2.0)(bb_spike_data)
        # The first spike bar (index 25) has the window still dominated by 100s,
        # so the upper band is ~100 and 200 is well above it.
        assert (
            result.any()
        ), "Expected bb_above_upper to fire when price spikes far above bands"
        assert result.iloc[25] == True  # first spike bar must fire

    def test_bb_below_lower_not_true_on_spike(self, bb_spike_data):
        """Price spike above upper band should not fire bb_below_lower."""
        result = bb_below_lower(length=20, std=2.0)(bb_spike_data)
        assert result.iloc[-1] == False

    def test_bb_above_below_never_simultaneously_true(self, bb_spike_data):
        """No single bar can be both above upper and below lower band."""
        above = bb_above_upper()(bb_spike_data)
        below = bb_below_lower()(bb_spike_data)
        assert not (above & below).any()

    def test_bb_insufficient_data_returns_all_false(self):
        """Fewer bars than period → no bands computed → all False."""
        dates = pd.date_range("2018-01-01", periods=5, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0] * 5,
            }
        )
        result = bb_above_upper(length=20)(data)
        assert not result.any()

    def test_bb_length_matches_input(self, bb_spike_data):
        assert len(bb_above_upper()(bb_spike_data)) == len(bb_spike_data)


# ============================================================================
# EMA crossover signal tests
# ============================================================================


class TestEMACrossoverSignals:
    def test_ema_cross_above_returns_bool_series(self, ema_cross_data):
        result = ema_cross_above(fast=5, slow=20)(ema_cross_data)
        assert isinstance(result, pd.Series)
        assert result.dtype == bool

    def test_ema_cross_below_returns_bool_series(self, ema_cross_data):
        result = ema_cross_below(fast=5, slow=20)(ema_cross_data)
        assert isinstance(result, pd.Series)
        assert result.dtype == bool

    def test_ema_cross_above_fires_on_rising_trend(self, ema_cross_data):
        """Fast EMA should cross above slow EMA when trend turns bullish."""
        result = ema_cross_above(fast=5, slow=20)(ema_cross_data)
        assert result.any(), "Expected at least one EMA golden cross"

    def test_ema_cross_above_not_always_true(self, ema_cross_data):
        result = ema_cross_above(fast=5, slow=20)(ema_cross_data)
        assert not result.all()

    def test_ema_cross_above_below_mutually_exclusive(self, ema_cross_data):
        above = ema_cross_above(fast=5, slow=20)(ema_cross_data)
        below = ema_cross_below(fast=5, slow=20)(ema_cross_data)
        assert not (above & below).any()

    def test_ema_cross_insufficient_data_returns_all_false(self):
        """With fewer bars than slow period, EMA cross should return all False."""
        dates = pd.date_range("2018-01-01", periods=5, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0 + i for i in range(5)],
            }
        )
        result = ema_cross_above(fast=5, slow=50)(data)
        assert not result.any()

    def test_ema_cross_length_matches_input(self, ema_cross_data):
        assert len(ema_cross_above(fast=5, slow=20)(ema_cross_data)) == len(
            ema_cross_data
        )


# ============================================================================
# ATR volatility regime signal tests
# ============================================================================


class TestATRSignals:
    def test_atr_above_returns_bool_series(self, volatile_price_data):
        result = atr_above(period=14)(volatile_price_data)
        assert isinstance(result, pd.Series)
        assert result.dtype == bool

    def test_atr_below_returns_bool_series(self, volatile_price_data):
        result = atr_below(period=14)(volatile_price_data)
        assert isinstance(result, pd.Series)
        assert result.dtype == bool

    def test_atr_above_fires_during_volatile_period(self, volatile_price_data):
        """After large price swings, ATR should exceed median — atr_above fires."""
        result = atr_above(period=14, multiplier=1.0)(volatile_price_data)
        assert result.any(), "Expected atr_above to fire during volatile period"

    def test_atr_above_below_differ_across_bars(self, volatile_price_data):
        """atr_above and atr_below should not agree on every bar."""
        above = atr_above(period=14, multiplier=1.0)(volatile_price_data)
        below = atr_below(period=14, multiplier=1.0)(volatile_price_data)
        assert not (
            above == below
        ).all(), "Expected above and below to disagree on some bars"

    def test_atr_insufficient_data_returns_all_false(self):
        """With fewer bars than ATR period, should return all False."""
        dates = pd.date_range("2018-01-01", periods=5, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0, 101.0, 99.0, 102.0, 98.0],
            }
        )
        result = atr_above(period=14)(data)
        assert not result.any()

    def test_atr_length_matches_input(self, volatile_price_data):
        assert len(atr_above()(volatile_price_data)) == len(volatile_price_data)

    def test_atr_high_multiplier_rarely_fires(self, volatile_price_data):
        """Very high multiplier should almost never fire."""
        result = atr_above(period=14, multiplier=100.0)(volatile_price_data)
        assert not result.any()

    def test_atr_zero_multiplier_always_fires(self, volatile_price_data):
        """Multiplier=0 means ATR > 0, which is almost always true for real prices."""
        result = atr_above(period=14, multiplier=0.0)(volatile_price_data)
        # Should fire on bars where ATR can be computed (after warmup)
        assert result.any()


# ============================================================================
# Signal class and fluent API tests
# ============================================================================


class TestSignalClass:
    def test_signal_is_callable(self, price_data):
        """Signal wrapping a SignalFunc is itself callable."""
        sig = Signal(day_of_week(0))
        result = sig(price_data)
        assert isinstance(result, pd.Series)
        assert result.dtype == bool

    def test_signal_and_operator(self, price_data):
        """& operator should produce the logical AND of both signals."""
        # All weekdays AND Monday only = Monday only
        sig1 = Signal(day_of_week(0, 1, 2, 3, 4))
        sig2 = Signal(day_of_week(0))
        combined = sig1 & sig2
        result = combined(price_data)
        expected = day_of_week(0)(price_data)
        pd.testing.assert_series_equal(result, expected)

    def test_signal_or_operator(self, price_data):
        """| operator should produce the logical OR of both signals."""
        sig1 = Signal(day_of_week(0))  # Monday
        sig2 = Signal(day_of_week(4))  # Friday
        combined = sig1 | sig2
        result = combined(price_data)
        expected = or_signals(day_of_week(0), day_of_week(4))(price_data)
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_signal_chaining_three_conditions(self, price_data):
        """Three signals chained with | should equal or_signals with all three."""
        sig = Signal(day_of_week(0)) | Signal(day_of_week(1)) | Signal(day_of_week(2))
        result = sig(price_data)
        expected = or_signals(day_of_week(0), day_of_week(1), day_of_week(2))(
            price_data
        )
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_signal_factory_function(self, price_data):
        """signal() factory produces a Signal equivalent to Signal()."""
        sig = signal(day_of_week(3))
        result = sig(price_data)
        expected = day_of_week(3)(price_data)
        pd.testing.assert_series_equal(result, expected)

    def test_signal_factory_supports_and(self, price_data):
        """signal() return value should support & operator."""
        combined = signal(day_of_week(0)) & signal(day_of_week(1))
        result = combined(price_data)
        assert isinstance(result, pd.Series)
        assert result.dtype == bool
        # Monday AND Tuesday — no single day can be both
        assert not result.any()

    def test_signal_accepted_via_apply_signal(self, option_data_entry_exit):
        """Signal object accepted by apply_signal and used as entry_dates."""
        sig = Signal(day_of_week(3))  # Thursday
        entry_dates = apply_signal(option_data_entry_exit, sig)
        results = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            entry_dates=entry_dates,
            raw=True,
        )
        assert isinstance(results, pd.DataFrame)

    def test_signal_combined_with_callable(self, option_data_entry_exit):
        """Signal combined with another Signal and used via apply_signal works."""

        def always_true(data):
            return pd.Series(True, index=data.index)

        sig = Signal(day_of_week(3)) & Signal(always_true)
        entry_dates = apply_signal(option_data_entry_exit, sig)
        results = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            entry_dates=entry_dates,
            raw=True,
        )
        assert isinstance(results, pd.DataFrame)


# ============================================================================
# Multi-symbol per-symbol isolation tests
# ============================================================================


class TestMultiSymbolIsolation:
    """Verify signals compute per-symbol, not mixing price histories."""

    def test_rsi_computed_per_symbol(self, multi_symbol_price_data):
        """RSI on declining SPX should fire; RSI on rising NDX should not."""
        sig = rsi_below(period=14, threshold=30)
        result = sig(multi_symbol_price_data)
        spx_mask = multi_symbol_price_data["underlying_symbol"] == "SPX"
        ndx_mask = multi_symbol_price_data["underlying_symbol"] == "NDX"
        # SPX strong downtrend -> last bar RSI < 30
        assert result.loc[spx_mask].iloc[-1] == True
        # NDX strong uptrend -> last bar RSI should NOT be < 30
        assert result.loc[ndx_mask].iloc[-1] == False

    def test_sma_computed_per_symbol(self, multi_symbol_price_data):
        """SMA signal isolates each symbol's price history."""
        sig_below = sma_below(period=10)
        sig_above = sma_above(period=10)
        result_below = sig_below(multi_symbol_price_data)
        result_above = sig_above(multi_symbol_price_data)
        spx_mask = multi_symbol_price_data["underlying_symbol"] == "SPX"
        ndx_mask = multi_symbol_price_data["underlying_symbol"] == "NDX"
        # SPX declining: last bar should be below its SMA
        assert result_below.loc[spx_mask].iloc[-1] == True
        # NDX rising: last bar should be above its SMA
        assert result_above.loc[ndx_mask].iloc[-1] == True

    def test_signal_result_length_matches_all_symbols(self, multi_symbol_price_data):
        """Signal output must have same length as input (all symbols)."""
        result = rsi_below()(multi_symbol_price_data)
        assert len(result) == len(multi_symbol_price_data)


# ============================================================================
# sustained() combinator tests
# ============================================================================


def _make_data(prices, symbol="SPX"):
    """Helper: build a minimal price DataFrame from a list of prices."""
    dates = pd.date_range("2018-01-01", periods=len(prices), freq="B")
    return pd.DataFrame(
        {"underlying_symbol": symbol, "quote_date": dates, "underlying_price": prices}
    )


class TestSustainedSignal:
    def test_sustained_not_true_before_streak(self):
        """Should be False when streak is shorter than required days."""
        # Always-True signal, but only 4 bars, days=5 → all False
        data = _make_data([100.0] * 4)

        def always_true(d):
            return pd.Series(True, index=d.index)

        result = sustained(always_true, days=5)(data)
        assert not result.any()

    def test_sustained_fires_after_streak(self):
        """Should be True on the Nth consecutive True bar (exactly days bars)."""
        # 6 bars of always-True, days=5 → bars 4 and 5 (0-indexed) should fire
        data = _make_data([100.0] * 6)

        def always_true(d):
            return pd.Series(True, index=d.index)

        result = sustained(always_true, days=5)(data)
        # First 4 bars False (warmup), last 2 True
        assert not result.iloc[:4].any()
        assert result.iloc[4]
        assert result.iloc[5]

    def test_sustained_resets_on_false(self):
        """A single False bar breaks the streak; must restart from 0."""
        # True*4, False, True*5 — streak resets; only last 5 bars should fire
        inner_bools = [True] * 4 + [False] + [True] * 5
        data = _make_data([100.0] * len(inner_bools))

        def inner(d):
            return pd.Series(inner_bools, index=d.index)

        result = sustained(inner, days=5)(data)
        # All bars before the streak of 5 is complete should be False
        assert not result.iloc[:8].any()
        # The 5th consecutive True (index 9, 0-based) should fire
        assert result.iloc[9]

    def test_sustained_all_false_returns_all_false(self):
        """Wrapping an always-False signal stays all False regardless of days."""
        data = _make_data([100.0] * 20)

        def always_false(d):
            return pd.Series(False, index=d.index)

        result = sustained(always_false, days=3)(data)
        assert not result.any()

    def test_sustained_all_true_fires_after_warmup(self):
        """Wrapping always-True: first days-1 bars False, then True forever."""
        days = 4
        n = 10
        data = _make_data([100.0] * n)

        def always_true(d):
            return pd.Series(True, index=d.index)

        result = sustained(always_true, days=days)(data)
        assert not result.iloc[: days - 1].any()
        assert result.iloc[days - 1 :].all()

    def test_sustained_days_1_is_identity(self):
        """days=1 should produce the same output as the unwrapped signal."""
        data = _make_data([100.0 - i for i in range(20)])
        inner = rsi_below(period=14, threshold=30)
        raw = inner(data)
        wrapped = sustained(inner, days=1)(data)
        pd.testing.assert_series_equal(raw.astype(bool), wrapped)

    def test_sustained_per_symbol_isolation(self, multi_symbol_price_data):
        """Each symbol's streak is counted independently."""
        # SPX is declining (RSI will drop below 30), NDX rising (RSI stays high).
        # With days=1 we test that streaks don't bleed across symbols.
        inner = rsi_below(period=14, threshold=30)
        raw = inner(multi_symbol_price_data)
        wrapped = sustained(inner, days=1)(multi_symbol_price_data)
        # With days=1, sustained == raw
        pd.testing.assert_series_equal(raw.astype(bool), wrapped)

    def test_sustained_returns_bool_series(self, price_data):
        """Return type must be a boolean Series with the same length as input."""
        result = sustained(rsi_below(14, 30), days=3)(price_data)
        assert isinstance(result, pd.Series)
        assert result.dtype == bool
        assert len(result) == len(price_data)

    def test_sustained_works_with_signal_class(self, price_data):
        """sustained() output can be wrapped in Signal and combined with &."""
        # sustained(all weekdays, 1) & Monday = Monday only
        all_weekdays = day_of_week(0, 1, 2, 3, 4)
        sig = signal(sustained(all_weekdays, days=1)) & signal(day_of_week(0))
        result = sig(price_data)
        assert isinstance(result, pd.Series)
        assert result.dtype == bool
        # All True entries must be Mondays
        flagged_days = price_data.loc[result, "quote_date"].dt.dayofweek
        assert (flagged_days == 0).all()

    def test_sustained_accepted_via_apply_signal(self, option_data_entry_exit):
        """sustained() output is accepted by apply_signal and used as entry_dates."""

        def always_true(d):
            return pd.Series(True, index=d.index)

        sig = sustained(always_true, days=1)
        entry_dates = apply_signal(option_data_entry_exit, sig)
        results = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            entry_dates=entry_dates,
            raw=True,
        )
        assert isinstance(results, pd.DataFrame)


# ============================================================================
# stock_data parameter tests
# ============================================================================


class TestApplySignal:
    """Tests for the apply_signal() function that decouples signal computation."""

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

    def test_apply_signal_returns_dates_dataframe(self, ohlcv_stock_data):
        """apply_signal should return a DataFrame with (underlying_symbol, quote_date)."""

        def always_true(d):
            return pd.Series(True, index=d.index)

        result = apply_signal(ohlcv_stock_data, always_true)
        assert isinstance(result, pd.DataFrame)
        assert "underlying_symbol" in result.columns
        assert "quote_date" in result.columns
        assert len(result.columns) == 2

    def test_apply_signal_close_maps_to_underlying_price(self, ohlcv_stock_data):
        """apply_signal should auto-map 'close' to 'underlying_price' for TA signals."""
        # This signal reads underlying_price — should work when only close is present
        sig = sma_above(period=10)
        result = apply_signal(ohlcv_stock_data, sig)
        assert isinstance(result, pd.DataFrame)

    def test_apply_signal_all_true_returns_all_dates(self, ohlcv_stock_data):
        """apply_signal with always-true signal returns all unique dates."""

        def always_true(d):
            return pd.Series(True, index=d.index)

        result = apply_signal(ohlcv_stock_data, always_true)
        n_unique = ohlcv_stock_data.drop_duplicates(
            ["underlying_symbol", "quote_date"]
        ).shape[0]
        assert len(result) == n_unique

    def test_apply_signal_all_false_returns_empty(self, ohlcv_stock_data):
        """apply_signal with always-false signal returns empty DataFrame."""

        def always_false(d):
            return pd.Series(False, index=d.index)

        result = apply_signal(ohlcv_stock_data, always_false)
        assert len(result) == 0
        assert "underlying_symbol" in result.columns
        assert "quote_date" in result.columns

    def test_apply_signal_date_only_signal(self, ohlcv_stock_data):
        """Date-based signals (e.g. day_of_week) work with apply_signal."""
        result = apply_signal(ohlcv_stock_data, day_of_week(3))
        assert isinstance(result, pd.DataFrame)
        # All flagged dates should be Thursdays
        assert (result["quote_date"].dt.dayofweek == 3).all()

    def test_apply_signal_entry_dates_accepted_by_strategy(
        self, option_data_entry_exit, ohlcv_stock_data
    ):
        """entry_dates from apply_signal are accepted by strategy functions."""

        def always_true(d):
            return pd.Series(True, index=d.index)

        entry_dates = apply_signal(ohlcv_stock_data, always_true)
        results = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            entry_dates=entry_dates,
            raw=True,
        )
        assert isinstance(results, pd.DataFrame)

    def test_apply_signal_with_combined_signal(self, ohlcv_stock_data):
        """apply_signal works with combined signals (and_signals, Signal class)."""

        def always_true(d):
            return pd.Series(True, index=d.index)

        combined = and_signals(day_of_week(0, 1, 2, 3, 4), always_true)
        result = apply_signal(ohlcv_stock_data, combined)
        assert isinstance(result, pd.DataFrame)

    def test_apply_signal_with_signal_class(self, ohlcv_stock_data):
        """apply_signal works with Signal objects."""
        sig = signal(day_of_week(3)) & signal(day_of_week(0, 1, 2, 3, 4))
        result = apply_signal(ohlcv_stock_data, sig)
        assert (result["quote_date"].dt.dayofweek == 3).all()

    def test_atr_uses_real_high_low_when_available(self, ohlcv_stock_data):
        """ATR signal should detect and use high/low columns from stock_data."""
        sig = atr_above(period=14, multiplier=0.0)
        result = sig(
            ohlcv_stock_data.assign(underlying_price=ohlcv_stock_data["close"])
        )
        # With multiplier=0, ATR > 0 should fire after warmup
        assert result.any()

    def test_atr_without_ohlcv_still_works(self, volatile_price_data):
        """ATR signal should still work with close-only data (no high/low)."""
        result = atr_above(period=14, multiplier=0.0)(volatile_price_data)
        assert result.any()

    def test_dates_validation_rejects_non_dataframe(self):
        """entry_dates that is not a DataFrame should be rejected."""
        from optopsy.checks import _check_dates_dataframe

        with pytest.raises(ValueError, match="must be a DataFrame"):
            _check_dates_dataframe("entry_dates", "not_a_dataframe")

    def test_dates_validation_rejects_missing_columns(self):
        """entry_dates missing required columns should be rejected."""
        from optopsy.checks import _check_dates_dataframe

        df = pd.DataFrame({"quote_date": [1]})
        with pytest.raises(ValueError, match="missing required columns"):
            _check_dates_dataframe("entry_dates", df)

    def test_dates_validation_accepts_valid(self):
        """Valid dates DataFrame should pass validation."""
        from optopsy.checks import _check_dates_dataframe

        df = pd.DataFrame(
            {"underlying_symbol": ["SPX"], "quote_date": [pd.Timestamp("2018-01-01")]}
        )
        _check_dates_dataframe("entry_dates", df)  # no exception

    def test_dates_validation_accepts_none(self):
        """None should pass validation."""
        from optopsy.checks import _check_dates_dataframe

        _check_dates_dataframe("entry_dates", None)  # no exception


# ============================================================================
# E2E integration tests: real TA signal + stock_data → core engine → output
# ============================================================================


class TestTASignalE2E:
    """
    End-to-end tests that exercise the full pipeline:
    real pandas_ta signal + apply_signal() → entry_dates/exit_dates → strategy output.

    These tests use ``stock_data_long_history`` (200-bar OHLCV with a
    mid-decline bounce) and ``option_data_with_stock`` (option chain with
    fixed strikes 195/200/205, 4 entry dates across decline/recovery phases,
    and 2 expirations: exp-A at bar 100 (RSI≈14) and exp-B at bar 195
    (RSI≈100)).

    Key entry-bar properties:
      bar 30:  RSI=0,    sma_above=False, rsi_below=True,  sustained(3)=True
      bar 53:  RSI≈29.8, sma_above=False, rsi_below=True,  sustained(3)=False
      bar 160: RSI≈99.8, sma_above=True,  rsi_below=False, atr_ohlcv=True,  atr_close=False
      bar 170: RSI≈99.9, sma_above=True,  rsi_below=False, atr_ohlcv=True,  atr_close=True

    Decline entries (30, 53) match both exps → 3 calls × 2 exps = 6 each.
    Recovery entries (160, 170) are after exp-A → 3 calls × 1 exp = 3 each.
    Baseline: 6 + 6 + 3 + 3 = 18 call rows.

    Assertions use ``quote_date_entry`` for date-level verification,
    ``expiration`` for exit-level verification, and exact row counts.
    """

    def _get_entry_dates(self, stock_data_long_history):
        """Return the 4 entry dates used by option_data_with_stock."""
        dates = stock_data_long_history["quote_date"].values
        return {
            "decline": {
                pd.Timestamp(dates[30]),
                pd.Timestamp(dates[53]),
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
        """sma_above(20) entry_dates should only keep recovery-phase entries.

        Stock data has 4 entry dates: 2 during decline (SMA False) and
        2 during recovery (SMA True).  Only recovery dates should survive.
        Baseline 18 → filtered 6 (recovery entries × exp-B only × 3 strikes).
        """
        ed = self._get_entry_dates(stock_data_long_history)

        results_all = long_calls(
            option_data_with_stock,
            max_entry_dte=365,
            exit_dte=0,
            raw=True,
        )
        assert len(results_all) == 18

        entry_dates = apply_signal(stock_data_long_history, sma_above(20))
        results_sma = long_calls(
            option_data_with_stock,
            max_entry_dte=365,
            exit_dte=0,
            entry_dates=entry_dates,
            raw=True,
        )
        assert len(results_sma) == 6

        actual_dates = set(results_sma["quote_date_entry"].unique())
        assert actual_dates == ed["recovery"]
        assert actual_dates.isdisjoint(ed["decline"])

    def test_rsi_entry_dates_with_stock_data(
        self, option_data_with_stock, stock_data_long_history
    ):
        """rsi_below(14, 30) entry_dates should only keep decline-phase entries.

        RSI < 30 during decline (bars 30, 53) but not during recovery
        (bars 160, 170).  Decline entries match both exps → 12 rows.
        """
        ed = self._get_entry_dates(stock_data_long_history)

        entry_dates = apply_signal(stock_data_long_history, rsi_below(14, 30))
        results = short_puts(
            option_data_with_stock,
            max_entry_dte=365,
            exit_dte=0,
            entry_dates=entry_dates,
            raw=True,
        )
        assert len(results) == 12

        actual_dates = set(results["quote_date_entry"].unique())
        assert actual_dates == ed["decline"]
        assert actual_dates.isdisjoint(ed["recovery"])

    def test_ta_exit_dates_filter_exits(
        self, option_data_with_stock, stock_data_long_history
    ):
        """rsi_above(14, 70) exit_dates should remove expiration-A exits.

        Exp-A (bar 100, RSI≈14) → rsi_above(14,70)=False → filtered out.
        Exp-B (bar 195, RSI≈100) → rsi_above(14,70)=True → kept.
        Baseline 18 → filtered 12 (only exp-B rows survive).
        """
        exps = self._exp_dates(stock_data_long_history)

        results_all = long_calls(
            option_data_with_stock,
            max_entry_dte=365,
            exit_dte=0,
            raw=True,
        )
        assert len(results_all) == 18

        exit_dates = apply_signal(stock_data_long_history, rsi_above(14, 70))
        results_exit = long_calls(
            option_data_with_stock,
            max_entry_dte=365,
            exit_dte=0,
            exit_dates=exit_dates,
            raw=True,
        )
        assert len(results_exit) == 12

        # All surviving rows must have exp-B
        assert set(results_exit["expiration"].unique()) == {exps["B"]}

        # Inverse: rsi_below(14, 30) keeps only exp-A exits
        # (bar 100 RSI≈14 < 30 → True; bar 195 RSI≈100 → False)
        exit_dates_inv = apply_signal(stock_data_long_history, rsi_below(14, 30))
        results_inverse = long_calls(
            option_data_with_stock,
            max_entry_dte=365,
            exit_dte=0,
            exit_dates=exit_dates_inv,
            raw=True,
        )
        assert len(results_inverse) == 6

        # All surviving inverse rows must have exp-A
        assert set(results_inverse["expiration"].unique()) == {exps["A"]}

    def test_entry_and_exit_dates_both_filter(
        self, option_data_with_stock, stock_data_long_history
    ):
        """Combined entry_dates + exit_dates should both filter independently.

        Use rsi_below(14,30) for entry_dates (keeps bars 30, 53 → 12 rows)
        and rsi_above(14,70) for exit_dates (keeps exp-B only).
        Combined: decline entries × exp-B = 6 rows.

        Crucially, BOTH filters independently reduce the result set:
          - Entry-only:  18 → 12 (removes recovery entries)
          - Exit-only:   18 → 12 (removes exp-A)
          - Combined:    18 → 6  (removes both)
        """
        ed = self._get_entry_dates(stock_data_long_history)
        exps = self._exp_dates(stock_data_long_history)

        entry_dates = apply_signal(stock_data_long_history, rsi_below(14, 30))
        exit_dates = apply_signal(stock_data_long_history, rsi_above(14, 70))
        results = long_calls(
            option_data_with_stock,
            max_entry_dte=365,
            exit_dte=0,
            entry_dates=entry_dates,
            exit_dates=exit_dates,
            raw=True,
        )
        assert len(results) == 6

        # Verify entry dates are decline-only
        actual_dates = set(results["quote_date_entry"].unique())
        assert actual_dates == ed["decline"]

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
        assert len(results_entry_only) == 12
        assert len(results_exit_only) == 12
        # Combined is strictly fewer than either individual filter
        assert len(results) < len(results_entry_only)
        assert len(results) < len(results_exit_only)

    def test_sustained_ta_signal_with_apply_signal(
        self, option_data_with_stock, stock_data_long_history
    ):
        """sustained(rsi_below(14, 30), days=3) must reject bar 53.

        The bounce at bars 41-42 resets the RSI streak.  At bar 53,
        RSI just crossed back below 30 for <3 consecutive bars, so
        sustained(days=3) rejects it.  Bar 30 is deep in the streak
        (30+ consecutive bars with RSI=0) and survives.

        This test MUST produce fewer rows than plain rsi_below(14,30)
        to prove sustained actually checks streak length.

        plain rsi_below: bars 30 + 53 → 12 rows
        sustained(3):    bar 30 only  → 6 rows
        """
        ed = self._get_entry_dates(stock_data_long_history)
        decline_deep = {pd.Timestamp(stock_data_long_history["quote_date"].values[30])}

        # Plain rsi_below keeps both decline entries
        entry_dates_plain = apply_signal(stock_data_long_history, rsi_below(14, 30))
        results_plain = long_calls(
            option_data_with_stock,
            max_entry_dte=365,
            exit_dte=0,
            entry_dates=entry_dates_plain,
            raw=True,
        )
        assert len(results_plain) == 12
        assert set(results_plain["quote_date_entry"].unique()) == ed["decline"]

        # sustained(days=3) rejects bar 53 (streak < 3 bars)
        entry_dates_sust = apply_signal(
            stock_data_long_history, sustained(rsi_below(14, 30), days=3)
        )
        results_sustained = long_calls(
            option_data_with_stock,
            max_entry_dte=365,
            exit_dte=0,
            entry_dates=entry_dates_sust,
            raw=True,
        )
        assert len(results_sustained) == 6

        # Only bar 30 survives (deep in streak)
        actual_dates = set(results_sustained["quote_date_entry"].unique())
        assert actual_dates == decline_deep

        # Prove sustained is strictly more selective than plain
        assert len(results_sustained) < len(results_plain)

    def test_atr_signal_uses_real_ohlcv(
        self, option_data_with_stock, stock_data_long_history
    ):
        """ATR signal should use real high/low from stock_data when available.

        With OHLCV stock_data, atr_above(14, 1.0) passes all 4 entries → 18 rows.
        With close-only stock_data, bar 160 is rejected → 15 rows.
        The intraday range from real high/low changes ATR values, causing
        different filtering.
        """
        sd_full = stock_data_long_history
        sd_close_only = sd_full.drop(columns=["high", "low"])

        entry_dates_ohlcv = apply_signal(sd_full, atr_above(period=14, multiplier=1.0))
        results_ohlcv = long_calls(
            option_data_with_stock,
            max_entry_dte=365,
            exit_dte=0,
            entry_dates=entry_dates_ohlcv,
            raw=True,
        )

        entry_dates_close = apply_signal(
            sd_close_only, atr_above(period=14, multiplier=1.0)
        )
        results_close = long_calls(
            option_data_with_stock,
            max_entry_dte=365,
            exit_dte=0,
            entry_dates=entry_dates_close,
            raw=True,
        )

        assert len(results_ohlcv) == 18
        assert len(results_close) == 15

        # OHLCV includes bar 160 that close-only misses
        ohlcv_dates = set(results_ohlcv["quote_date_entry"].unique())
        close_dates = set(results_close["quote_date_entry"].unique())
        assert (
            close_dates < ohlcv_dates
        ), "Expected close-only to be a strict subset of OHLCV dates"
