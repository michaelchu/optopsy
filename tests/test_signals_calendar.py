"""Tests for calendar-based signal functions."""

import pandas as pd

from optopsy.signals import day_of_week


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
