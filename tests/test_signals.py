"""Tests for entry and exit signal filtering functionality."""

import datetime
import numpy as np
import pandas as pd
import pytest
from optopsy.signals import (
    _compute_rsi,
    rsi_below,
    rsi_above,
    day_of_week,
    sma_below,
    sma_above,
    and_signals,
    or_signals,
)
from optopsy.strategies import long_calls, short_puts, long_call_calendar

# ============================================================================
# Fixtures
# ============================================================================


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


@pytest.fixture
def option_data_entry_exit():
    """
    Option data with clear entry and exit dates for testing signal filtering.
    Entry date: 2018-01-04 (Thursday) with DTE=30
    Exit date: 2018-02-02 (expiration, DTE=0)

    Also includes 2018-01-03 (Wednesday) as an entry date that should be
    filtered out by day_of_week(3) (Thursday only).
    """
    entry_wed = datetime.datetime(2018, 1, 3)  # Wednesday
    entry_thu = datetime.datetime(2018, 1, 4)  # Thursday
    exp_date = datetime.datetime(2018, 2, 3)

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
        # Wednesday entry
        ["SPX", 213.93, "call", exp_date, entry_wed, 212.5, 7.35, 7.45],
        ["SPX", 213.93, "call", exp_date, entry_wed, 215.0, 6.00, 6.05],
        ["SPX", 213.93, "put", exp_date, entry_wed, 212.5, 5.70, 5.80],
        ["SPX", 213.93, "put", exp_date, entry_wed, 215.0, 7.10, 7.20],
        # Thursday entry
        ["SPX", 214.50, "call", exp_date, entry_thu, 212.5, 7.55, 7.65],
        ["SPX", 214.50, "call", exp_date, entry_thu, 215.0, 6.10, 6.20],
        ["SPX", 214.50, "put", exp_date, entry_thu, 212.5, 5.50, 5.60],
        ["SPX", 214.50, "put", exp_date, entry_thu, 215.0, 6.90, 7.00],
        # Exit (expiration)
        ["SPX", 220, "call", exp_date, exp_date, 212.5, 7.45, 7.55],
        ["SPX", 220, "call", exp_date, exp_date, 215.0, 4.96, 5.05],
        ["SPX", 220, "put", exp_date, exp_date, 212.5, 0.0, 0.05],
        ["SPX", 220, "put", exp_date, exp_date, 215.0, 0.0, 0.05],
    ]
    return pd.DataFrame(data=d, columns=cols)


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
    def test_and_signals(self, price_data):
        """and_signals should require all signals to be True."""
        always_true = lambda data: pd.Series(True, index=data.index)
        always_false = lambda data: pd.Series(False, index=data.index)

        result = and_signals(always_true, always_true)(price_data)
        assert result.all()

        result = and_signals(always_true, always_false)(price_data)
        assert not result.any()

    def test_or_signals(self, price_data):
        """or_signals should require at least one signal to be True."""
        always_true = lambda data: pd.Series(True, index=data.index)
        always_false = lambda data: pd.Series(False, index=data.index)

        result = or_signals(always_true, always_false)(price_data)
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
        """entry_signal=day_of_week(3) should only include Thursday entries."""
        # Without signal - should include both Wednesday and Thursday entries
        results_all = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            raw=True,
        )

        # With Thursday-only signal
        results_thu = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            entry_signal=day_of_week(3),  # Thursday
            raw=True,
        )

        # Thursday results should be a subset of all results
        assert len(results_thu) <= len(results_all)
        assert len(results_thu) > 0

    def test_signal_filters_no_match_returns_empty(self, option_data_entry_exit):
        """entry_signal that matches nothing should return empty DataFrame."""
        # Saturday signal on weekday data -> no matches
        results = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            entry_signal=day_of_week(5),  # Saturday
            raw=True,
        )
        assert len(results) == 0

    def test_always_true_signal_same_as_no_signal(self, option_data_entry_exit):
        """A signal that always returns True should give same results as no signal."""
        always_true = lambda data: pd.Series(True, index=data.index)

        results_no_signal = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            raw=True,
        )

        results_true_signal = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            entry_signal=always_true,
            raw=True,
        )

        pd.testing.assert_frame_equal(results_no_signal, results_true_signal)

    def test_entry_signal_with_short_puts(self, option_data_entry_exit):
        """entry_signal should work with short put strategies too."""
        results = short_puts(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            entry_signal=day_of_week(3),  # Thursday
            raw=True,
        )
        # Should return results (Thursday has put data)
        assert isinstance(results, pd.DataFrame)

    def test_invalid_entry_signal_raises(self, option_data_entry_exit):
        """Non-callable entry_signal should raise ValueError."""
        with pytest.raises(ValueError, match="entry_signal"):
            long_calls(
                option_data_entry_exit,
                max_entry_dte=90,
                exit_dte=0,
                entry_signal="not_a_callable",
                raw=True,
            )

    def test_combined_signal_integration(self, option_data_entry_exit):
        """Combined signals should work end-to-end with strategies."""
        # Combine Thursday + always True (effectively just Thursday)
        always_true = lambda data: pd.Series(True, index=data.index)
        combined = and_signals(day_of_week(3), always_true)

        results_combined = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            entry_signal=combined,
            raw=True,
        )

        results_thu = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            entry_signal=day_of_week(3),
            raw=True,
        )

        pd.testing.assert_frame_equal(results_combined, results_thu)


# ============================================================================
# Integration tests: exit_signal with strategy functions
# ============================================================================


class TestExitSignalIntegration:
    def test_exit_signal_filters_exits(self, option_data_entry_exit):
        """exit_signal should filter which exit dates are valid."""
        # Without signal
        results_all = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            raw=True,
        )

        # With exit signal that matches the exit date (Saturday Feb 3 -> dayofweek=5)
        # The expiration date 2018-02-03 is a Saturday
        results_sat = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            exit_signal=day_of_week(5),  # Saturday
            raw=True,
        )

        # Saturday matches the exit date, so results should be the same
        assert len(results_sat) == len(results_all)

    def test_exit_signal_no_match_returns_empty(self, option_data_entry_exit):
        """exit_signal that matches nothing should return empty DataFrame."""
        # The exit date (2018-02-03) is Saturday. Filter for Monday exits only.
        results = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            exit_signal=day_of_week(0),  # Monday only
            raw=True,
        )
        assert len(results) == 0

    def test_always_true_exit_signal_same_as_no_signal(self, option_data_entry_exit):
        """An exit_signal that always returns True should give same results as no signal."""
        always_true = lambda data: pd.Series(True, index=data.index)

        results_no_signal = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            raw=True,
        )

        results_true_signal = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            exit_signal=always_true,
            raw=True,
        )

        pd.testing.assert_frame_equal(results_no_signal, results_true_signal)

    def test_entry_and_exit_signals_combined(self, option_data_entry_exit):
        """entry_signal and exit_signal should both be applied independently."""
        always_true = lambda data: pd.Series(True, index=data.index)

        # Entry on Thursday only, exit any time
        results_entry_only = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            entry_signal=day_of_week(3),  # Thursday
            raw=True,
        )

        # Entry on Thursday, exit signal always true (no additional filtering)
        results_both = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            entry_signal=day_of_week(3),
            exit_signal=always_true,
            raw=True,
        )

        pd.testing.assert_frame_equal(results_entry_only, results_both)

    def test_exit_signal_with_short_puts(self, option_data_entry_exit):
        """exit_signal should work with short put strategies."""
        always_true = lambda data: pd.Series(True, index=data.index)

        results_no_signal = short_puts(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            raw=True,
        )

        results_with_signal = short_puts(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            exit_signal=always_true,
            raw=True,
        )

        pd.testing.assert_frame_equal(results_no_signal, results_with_signal)

    def test_invalid_exit_signal_raises(self, option_data_entry_exit):
        """Non-callable exit_signal should raise ValueError."""
        with pytest.raises(ValueError, match="exit_signal"):
            long_calls(
                option_data_entry_exit,
                max_entry_dte=90,
                exit_dte=0,
                exit_signal="not_a_callable",
                raw=True,
            )

    def test_exit_signal_price_based(self, option_data_entry_exit):
        """exit_signal based on price threshold should filter correctly."""
        # Exit only when underlying price > 215
        # Exit date has underlying_price=220, so this should pass
        price_above_215 = lambda data: data["underlying_price"] > 215

        results = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            exit_signal=price_above_215,
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

    def test_exit_signal_price_based_filters_out(self, option_data_entry_exit):
        """exit_signal with price condition that fails should filter trades."""
        # Exit only when underlying price > 225
        # Exit date has underlying_price=220, so this should filter everything
        price_above_225 = lambda data: data["underlying_price"] > 225

        results = long_calls(
            option_data_entry_exit,
            max_entry_dte=90,
            exit_dte=0,
            exit_signal=price_above_225,
            raw=True,
        )

        assert len(results) == 0
