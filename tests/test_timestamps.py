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


class TestNormalizeDates:
    """Unit tests for the normalize_dates utility."""

    def test_passthrough(self):
        """Naive midnight timestamps are unchanged."""
        s = pd.Series(pd.to_datetime(["2024-01-15", "2024-01-16"]))
        result = normalize_dates(s)
        pd.testing.assert_series_equal(result, s)

    def test_strips_tz_and_time(self):
        """Timezone-aware timestamps with time components become naive midnight."""
        s = pd.Series(
            pd.to_datetime(["2024-01-15 16:30:00", "2024-01-16 09:30:00"]).tz_localize(
                "UTC"
            )
        )
        result = normalize_dates(s)
        assert result.dt.tz is None
        expected = pd.Series(pd.to_datetime(["2024-01-15", "2024-01-16"]))
        pd.testing.assert_series_equal(result, expected)

    def test_does_not_mutate_input(self):
        """Input Series is not modified in place."""
        s = pd.Series(pd.to_datetime(["2024-01-15 16:30:00"]).tz_localize("UTC"))
        original = s.copy()
        normalize_dates(s)
        pd.testing.assert_series_equal(s, original)


class TestCrossSourceDateMatching:
    """Integration tests: signal dates from one source match option chain
    dates from a different source when run through the full pipeline."""

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

    def test_naive_signals_match(self, option_data):
        """Baseline: naive midnight signals match naive midnight options."""
        signal_data = self._make_signal_data()
        entry_dates = apply_signal(signal_data, day_of_week(3))
        result = long_calls(option_data, entry_dates=entry_dates, raw=True)
        assert len(result) > 0

    def test_tz_aware_with_time_signals_match(self, option_data):
        """UTC tz-aware signals at market close match naive midnight options."""
        signal_data = self._make_signal_data(tz="UTC", hour=16, minute=30)
        entry_dates = apply_signal(signal_data, day_of_week(3))
        result = long_calls(option_data, entry_dates=entry_dates, raw=True)
        assert len(result) > 0


class TestApplySignalNormalization:
    """apply_signal output is always normalized."""

    def test_normalizes_tz_and_time(self):
        """apply_signal strips timezone and time from output dates."""
        data = pd.DataFrame(
            {
                "underlying_symbol": ["SPX"] * 3,
                "quote_date": pd.to_datetime(
                    [
                        "2024-01-15 16:30:00",
                        "2024-01-16 16:30:00",
                        "2024-01-17 16:30:00",
                    ]
                ).tz_localize("UTC"),
                "close": [100, 101, 102],
            }
        )
        result = apply_signal(data, lambda df: pd.Series(True, index=df.index))
        assert result["quote_date"].dt.tz is None
        assert all(result["quote_date"].dt.hour == 0)
