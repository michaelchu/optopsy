"""Tests for cross-source date normalization.

Verifies that signal dates from one provider (e.g. yfinance) reliably match
option chain dates from another provider (e.g. EODHD, CSV) regardless of
timezone awareness or time-of-day differences.
"""

import datetime

import pandas as pd
import pytest

from optopsy.timestamps import normalize_dates
from optopsy.signals import apply_signal, day_of_week
from optopsy.strategies import long_calls

# ============================================================================
# normalize_dates unit tests
# ============================================================================


class TestNormalizeDates:
    """Unit tests for the normalize_dates utility."""

    def test_naive_midnight_passthrough(self):
        """Naive midnight timestamps are unchanged."""
        s = pd.Series(pd.to_datetime(["2024-01-15", "2024-01-16"]))
        result = normalize_dates(s)
        pd.testing.assert_series_equal(result, s)

    def test_strips_timezone(self):
        """Timezone-aware timestamps are converted to naive."""
        s = pd.Series(pd.to_datetime(["2024-01-15", "2024-01-16"]).tz_localize("UTC"))
        result = normalize_dates(s)
        assert result.dt.tz is None
        expected = pd.Series(pd.to_datetime(["2024-01-15", "2024-01-16"]))
        pd.testing.assert_series_equal(result, expected)

    def test_strips_non_utc_timezone(self):
        """Non-UTC timezone-aware timestamps are stripped."""
        s = pd.Series(pd.to_datetime(["2024-01-15 10:00:00"]).tz_localize("Etc/GMT+5"))
        result = normalize_dates(s)
        assert result.dt.tz is None
        expected = pd.Series(pd.to_datetime(["2024-01-15"]))
        pd.testing.assert_series_equal(result, expected)

    def test_floors_time_component(self):
        """Sub-day time components are removed."""
        s = pd.Series(pd.to_datetime(["2024-01-15 16:30:00", "2024-01-16 09:30:00"]))
        result = normalize_dates(s)
        expected = pd.Series(pd.to_datetime(["2024-01-15", "2024-01-16"]))
        pd.testing.assert_series_equal(result, expected)

    def test_combined_tz_and_time_component(self):
        """Timezone + time component: both are handled together."""
        s = pd.Series(pd.to_datetime(["2024-01-15 16:30:00"]).tz_localize("UTC"))
        result = normalize_dates(s)
        assert result.dt.tz is None
        expected = pd.Series(pd.to_datetime(["2024-01-15"]))
        pd.testing.assert_series_equal(result, expected)

    def test_does_not_mutate_input(self):
        """Input Series is not modified in place."""
        s = pd.Series(pd.to_datetime(["2024-01-15 16:30:00"]).tz_localize("UTC"))
        original = s.copy()
        normalize_dates(s)
        pd.testing.assert_series_equal(s, original)


# ============================================================================
# Cross-source integration tests
# ============================================================================


class TestCrossSourceDateMatching:
    """Integration tests verifying that signal dates from one source
    reliably match option chain dates from a different source."""

    @pytest.fixture
    def option_data(self):
        """Option chain with naive midnight dates (typical of CSV/EODHD)."""
        exp_date = datetime.datetime(2018, 2, 3)
        entry_wed = datetime.datetime(2018, 1, 3)
        entry_thu = datetime.datetime(2018, 1, 4)
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
            ["SPX", 213.93, "call", exp_date, entry_wed, 212.5, 7.35, 7.45],
            ["SPX", 213.93, "call", exp_date, entry_wed, 215.0, 6.00, 6.05],
            ["SPX", 213.93, "put", exp_date, entry_wed, 212.5, 5.70, 5.80],
            ["SPX", 213.93, "put", exp_date, entry_wed, 215.0, 7.10, 7.20],
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

    def _make_signal_data(self, tz=None, hour=0, minute=0):
        """Build signal data with configurable timezone and time component."""
        dates = pd.date_range("2018-01-01", periods=10, freq="B")
        if hour or minute:
            dates = dates + pd.Timedelta(hours=hour, minutes=minute)
        if tz:
            dates = dates.tz_localize(tz)
        return pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "close": [213.0 + i for i in range(len(dates))],
            }
        )

    def test_naive_midnight_matches_naive_midnight(self, option_data):
        """Baseline: matching sources still work after normalization."""
        signal_data = self._make_signal_data()
        entry_dates = apply_signal(signal_data, day_of_week(3))
        result = long_calls(option_data, entry_dates=entry_dates, raw=True)
        assert len(result) > 0

    def test_tz_aware_signal_matches_naive_options(self, option_data):
        """yfinance UTC dates match EODHD naive dates via normalization."""
        signal_data = self._make_signal_data(tz="UTC")
        entry_dates = apply_signal(signal_data, day_of_week(3))
        result = long_calls(option_data, entry_dates=entry_dates, raw=True)
        assert len(result) > 0

    def test_market_close_time_matches_midnight(self, option_data):
        """Signal data at 16:30 matches option data at midnight."""
        signal_data = self._make_signal_data(hour=16, minute=30)
        entry_dates = apply_signal(signal_data, day_of_week(3))
        result = long_calls(option_data, entry_dates=entry_dates, raw=True)
        assert len(result) > 0

    def test_tz_aware_with_time_matches_naive_midnight(self, option_data):
        """UTC + 16:30 signal data matches naive midnight option data."""
        signal_data = self._make_signal_data(tz="UTC", hour=16, minute=30)
        entry_dates = apply_signal(signal_data, day_of_week(3))
        result = long_calls(option_data, entry_dates=entry_dates, raw=True)
        assert len(result) > 0

    def test_non_utc_tz_matches_naive(self, option_data):
        """Non-UTC tz-aware signal data matches naive option data."""
        signal_data = self._make_signal_data(tz="Etc/GMT+5", hour=9, minute=30)
        entry_dates = apply_signal(signal_data, day_of_week(3))
        result = long_calls(option_data, entry_dates=entry_dates, raw=True)
        assert len(result) > 0

    def test_signal_filter_normalizes_both_sides(self):
        """_apply_signal_filter normalizes both data and signal dates."""
        from optopsy.core import _apply_signal_filter

        # Option-side dates at midnight
        data = pd.DataFrame(
            {
                "underlying_symbol": ["SPX", "SPX"],
                "quote_date": pd.to_datetime(
                    ["2024-01-15 00:00:00", "2024-01-16 00:00:00"]
                ),
                "value": [100, 200],
            }
        )
        # Signal-side dates at market close (16:30)
        signal_dates = pd.DataFrame(
            {
                "underlying_symbol": ["SPX"],
                "quote_date": pd.to_datetime(["2024-01-15 16:30:00"]),
            }
        )
        result = _apply_signal_filter(data, signal_dates)
        assert len(result) == 1
        assert result["value"].iloc[0] == 100


class TestApplySignalNormalization:
    """Tests for normalization within apply_signal itself."""

    def test_output_dates_are_normalized(self):
        """apply_signal output has normalized quote_date values."""
        data = pd.DataFrame(
            {
                "underlying_symbol": ["SPX"] * 5,
                "quote_date": pd.to_datetime(
                    [
                        "2024-01-15 16:30:00",
                        "2024-01-16 16:30:00",
                        "2024-01-17 16:30:00",
                        "2024-01-18 16:30:00",
                        "2024-01-19 16:30:00",
                    ]
                ),
                "close": [100, 101, 102, 103, 104],
            }
        )
        result = apply_signal(data, lambda df: pd.Series(True, index=df.index))
        # All times should be midnight
        assert all(result["quote_date"].dt.hour == 0)
        assert all(result["quote_date"].dt.minute == 0)

    def test_tz_aware_input_produces_naive_output(self):
        """apply_signal strips timezone from tz-aware input."""
        data = pd.DataFrame(
            {
                "underlying_symbol": ["SPX"] * 3,
                "quote_date": pd.to_datetime(
                    ["2024-01-15", "2024-01-16", "2024-01-17"]
                ).tz_localize("UTC"),
                "close": [100, 101, 102],
            }
        )
        result = apply_signal(data, lambda df: pd.Series(True, index=df.index))
        assert result["quote_date"].dt.tz is None
