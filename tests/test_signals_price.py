"""Tests for price signal functions."""

import pandas as pd
import pytest

from optopsy.signals import (
    consecutive_down,
    consecutive_up,
    daily_return_above,
    daily_return_below,
    drawdown_from_high,
    gap_down,
    gap_up,
    high_of_n_days,
    low_of_n_days,
    price_above,
    price_below,
    price_cross_above,
    price_cross_below,
    rally_from_low,
)


@pytest.fixture()
def price_data():
    """Simple price data that crosses the 100 level."""
    dates = pd.date_range("2024-01-01", periods=10, freq="B")
    #                   0     1     2     3     4     5     6     7     8     9
    closes = [95.0, 97.0, 99.0, 101.0, 103.0, 102.0, 98.0, 96.0, 101.0, 105.0]
    return pd.DataFrame(
        {
            "underlying_symbol": "SPX",
            "quote_date": dates,
            "close": closes,
        }
    )


@pytest.fixture()
def ohlcv_data():
    """OHLCV data with gaps and breakouts."""
    dates = pd.date_range("2024-01-01", periods=8, freq="B")
    return pd.DataFrame(
        {
            "underlying_symbol": "SPX",
            "quote_date": dates,
            "open": [100, 102, 101, 105, 99, 98, 100, 103],
            "high": [103, 104, 103, 106, 101, 100, 102, 107],
            "low": [99, 101, 100, 103, 97, 96, 99, 102],
            "close": [102, 103, 101, 104, 98, 97, 101, 106],
            "volume": [1000] * 8,
        }
    )


# ============================================================================
# price_above / price_below
# ============================================================================


class TestPriceAboveBelow:
    def test_price_above_state(self, price_data):
        """price_above should be True on every bar where close > level."""
        result = price_above(100)(price_data)
        # bars 3,4,5,8,9 have close > 100
        expected = [False, False, False, True, True, True, False, False, True, True]
        assert list(result) == expected

    def test_price_below_state(self, price_data):
        """price_below should be True on every bar where close < level."""
        result = price_below(100)(price_data)
        # bars 0,1,2,6,7 have close < 100
        expected = [True, True, True, False, False, False, True, True, False, False]
        assert list(result) == expected

    def test_price_above_empty_df(self):
        """Should return empty Series on empty DataFrame."""
        df = pd.DataFrame(columns=["underlying_symbol", "quote_date", "close"])
        result = price_above(100)(df)
        assert len(result) == 0

    def test_price_above_multi_symbol(self):
        """Should work independently per symbol."""
        dates = pd.date_range("2024-01-01", periods=3, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": ["SPX"] * 3 + ["NDX"] * 3,
                "quote_date": list(dates) * 2,
                "close": [95, 105, 95, 105, 95, 105],
            }
        )
        result = price_above(100)(data)
        expected = [False, True, False, True, False, True]
        assert list(result) == expected


# ============================================================================
# price_cross_above / price_cross_below
# ============================================================================


class TestPriceCrossover:
    def test_cross_above_fires_once(self, price_data):
        """price_cross_above should fire only on the bar where close crosses above."""
        result = price_cross_above(100)(price_data)
        # Cross above at bar 3 (prev=99, cur=101) and bar 8 (prev=96, cur=101)
        cross_indices = [i for i, v in enumerate(result) if v]
        assert cross_indices == [3, 8]

    def test_cross_below_fires_once(self, price_data):
        """price_cross_below should fire only on the bar where close crosses below."""
        result = price_cross_below(100)(price_data)
        # Cross below at bar 6 (prev=102, cur=98)
        cross_indices = [i for i, v in enumerate(result) if v]
        assert cross_indices == [6]

    def test_cross_above_not_sustained(self, price_data):
        """Should NOT fire on subsequent bars above level."""
        result = price_cross_above(100)(price_data)
        # Bar 4 (103) is above level but not a crossover
        assert result.iloc[4] == False

    def test_cross_above_empty_df(self):
        df = pd.DataFrame(columns=["underlying_symbol", "quote_date", "close"])
        result = price_cross_above(100)(df)
        assert len(result) == 0


# ============================================================================
# gap_up / gap_down
# ============================================================================


class TestGapSignals:
    def test_gap_up_detects_gap(self, ohlcv_data):
        """gap_up should fire when open > prev close * (1 + pct/100)."""
        # prev close: [-, 102, 103, 101, 104, 98, 97, 101]
        # open:       [100, 102, 101, 105, 99, 98, 100, 103]
        # gap pct:    [-, 0, -1.9%, +3.96%, -4.8%, 0%, +3.1%, +1.98%]
        # At 1% threshold: bar 3 (105 > 101*1.01=102.01) and bar 7 (103 > 101*1.01=102.01)
        result = gap_up(pct=1.0)(ohlcv_data)
        gap_indices = [i for i, v in enumerate(result) if v]
        assert 3 in gap_indices  # 105 vs prev close 101
        assert 7 in gap_indices  # 103 vs prev close 101

    def test_gap_down_detects_gap(self, ohlcv_data):
        """gap_down should fire when open < prev close * (1 - pct/100)."""
        # At 1% threshold: bar 4 (open=99, prev_close=104, 104*0.99=102.96) → 99 < 102.96
        result = gap_down(pct=1.0)(ohlcv_data)
        gap_indices = [i for i, v in enumerate(result) if v]
        assert 4 in gap_indices

    def test_gap_up_no_open_column(self):
        """gap_up should return all-False when open column is missing."""
        dates = pd.date_range("2024-01-01", periods=3, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "close": [100, 105, 110],
            }
        )
        result = gap_up()(data)
        assert not result.any()

    def test_gap_first_bar_is_false(self, ohlcv_data):
        """First bar has no previous close, so gap should not fire."""
        result = gap_up(pct=0.0)(ohlcv_data)
        assert result.iloc[0] == False


# ============================================================================
# high_of_n_days / low_of_n_days
# ============================================================================


class TestNPeriodHighLow:
    def test_high_of_n_days_breakout(self):
        """Should fire when close reaches N-bar rolling high."""
        dates = pd.date_range("2024-01-01", periods=10, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "high": [100, 102, 101, 103, 99, 98, 100, 104, 103, 105],
                "low": [98, 100, 99, 101, 97, 96, 98, 102, 101, 103],
                "close": [99, 101, 100, 102, 98, 97, 99, 103, 102, 105],
            }
        )
        result = high_of_n_days(period=5)(data)
        # Bar 7: close=103, prev 5-bar high max = max(103,99,98,100,104)
        # Wait — rolling high is on the high column, shifted by 1
        # Bar 7 rolling(5).max().shift(1) = max of bars 2-6 highs = max(101,103,99,98,100) = 103
        # close=103 >= 103 → True
        assert result.iloc[7] == True
        # Bar 9: close=105, prev 5-bar high = max of bars 4-8 = max(99,98,100,104,103) = 104
        # 105 >= 104 → True
        assert result.iloc[9] == True

    def test_low_of_n_days_breakdown(self):
        """Should fire when close reaches N-bar rolling low."""
        dates = pd.date_range("2024-01-01", periods=10, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "high": [100, 102, 101, 103, 99, 98, 100, 97, 96, 95],
                "low": [98, 100, 99, 101, 97, 96, 98, 95, 94, 93],
                "close": [99, 101, 100, 102, 98, 97, 99, 96, 95, 93],
            }
        )
        result = low_of_n_days(period=5)(data)
        # Bar 7: close=96, prev 5-bar low = min of bars 2-6 lows = min(99,101,97,96,98) = 96
        # 96 <= 96 → True
        assert result.iloc[7] == True

    def test_high_of_n_days_no_high_column(self):
        """Should fall back to close when high column is missing."""
        dates = pd.date_range("2024-01-01", periods=5, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "close": [100, 101, 102, 103, 104],
            }
        )
        # _get_high falls back to close, so this should still work
        result = high_of_n_days(period=3)(data)
        # Each bar has rising close, so every bar after warmup reaches a new high
        assert result.any()

    def test_first_bar_is_false(self):
        """First bar has no prior history, should not fire."""
        dates = pd.date_range("2024-01-01", periods=3, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "high": [100, 200, 99],
                "low": [98, 98, 97],
                "close": [99, 199, 98],
            }
        )
        result = high_of_n_days(period=3)(data)
        # Bar 0: shifted rolling high is NaN → False
        assert result.iloc[0] == False

    def test_empty_df(self):
        df = pd.DataFrame(
            columns=["underlying_symbol", "quote_date", "high", "low", "close"]
        )
        assert len(high_of_n_days(5)(df)) == 0
        assert len(low_of_n_days(5)(df)) == 0


# ============================================================================
# daily_return_above / daily_return_below
# ============================================================================


class TestDailyReturn:
    def test_return_above_detects_big_gain(self):
        """daily_return_above should fire on bars with large positive returns."""
        dates = pd.date_range("2024-01-01", periods=5, freq="B")
        # Returns: -, +5%, -1%, +0.5%, +3%
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "close": [100, 105, 103.95, 104.47, 107.60],
            }
        )
        result = daily_return_above(2.0)(data)
        # Bar 1: +5% > 2% → True, Bar 4: +3% > 2% → True
        assert result.iloc[0] == False  # no prior bar
        assert result.iloc[1] == True  # +5%
        assert result.iloc[2] == False  # -1%
        assert result.iloc[4] == True  # +3%

    def test_return_below_detects_drop(self):
        """daily_return_below should fire on bars with large negative returns."""
        dates = pd.date_range("2024-01-01", periods=4, freq="B")
        # Returns: -, -5%, +2%, -0.5%
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "close": [100, 95, 96.9, 96.42],
            }
        )
        result = daily_return_below(-3.0)(data)
        assert result.iloc[1] == True  # -5% < -3%
        assert result.iloc[2] == False  # +2%

    def test_return_first_bar_false(self):
        dates = pd.date_range("2024-01-01", periods=2, freq="B")
        data = pd.DataFrame(
            {"underlying_symbol": "SPX", "quote_date": dates, "close": [100, 110]}
        )
        result = daily_return_above(0.0)(data)
        assert result.iloc[0] == False

    def test_return_empty_df(self):
        df = pd.DataFrame(columns=["underlying_symbol", "quote_date", "close"])
        assert len(daily_return_above(1.0)(df)) == 0


# ============================================================================
# drawdown_from_high / rally_from_low
# ============================================================================


class TestDrawdownRally:
    def test_drawdown_fires_when_down_from_high(self):
        """drawdown_from_high should be True when close drops pct% from rolling high."""
        dates = pd.date_range("2024-01-01", periods=6, freq="B")
        # Rolling 5-bar high includes current bar
        # Bars: 100, 105, 103, 100, 95, 94
        # Rolling high(5): 100, 105, 105, 105, 105, 105
        # DD%: 0, 0, -1.9%, -4.8%, -9.5%, -10.5%
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "close": [100, 105, 103, 100, 95, 94],
            }
        )
        result = drawdown_from_high(period=5, pct=5.0)(data)
        assert result.iloc[3] == False  # -4.8% < 5% threshold
        assert result.iloc[4] == True  # -9.5% >= 5%
        assert result.iloc[5] == True  # -10.5% >= 5%

    def test_rally_fires_when_up_from_low(self):
        """rally_from_low should be True when close rises pct% from rolling low."""
        dates = pd.date_range("2024-01-01", periods=6, freq="B")
        # Bars: 100, 95, 93, 95, 100, 102
        # Rolling low(5): 100, 95, 93, 93, 93, 93
        # Rally%: 0, 0, 0, 2.15%, 7.5%, 9.7%
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "close": [100, 95, 93, 95, 100, 102],
            }
        )
        result = rally_from_low(period=5, pct=5.0)(data)
        assert result.iloc[3] == False  # +2.15% < 5%
        assert result.iloc[4] == True  # +7.5% >= 5%
        assert result.iloc[5] == True  # +9.7% >= 5%

    def test_drawdown_empty_df(self):
        df = pd.DataFrame(columns=["underlying_symbol", "quote_date", "close"])
        assert len(drawdown_from_high(20, 5.0)(df)) == 0
        assert len(rally_from_low(20, 5.0)(df)) == 0


# ============================================================================
# consecutive_up / consecutive_down
# ============================================================================


class TestConsecutiveUpDown:
    def test_consecutive_up_3_days(self):
        """consecutive_up(3) should fire after 3 straight up-closes."""
        dates = pd.date_range("2024-01-01", periods=8, freq="B")
        # Up pattern: -, up, up, up, down, up, up, up
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "close": [100, 101, 102, 103, 100, 101, 102, 103],
            }
        )
        result = consecutive_up(3)(data)
        fire_indices = [i for i, v in enumerate(result) if v]
        # Bar 3: 3 consecutive up (101>100, 102>101, 103>102) → True
        # Bar 7: 3 consecutive up (101>100, 102>101, 103>102) → True
        assert 3 in fire_indices
        assert 7 in fire_indices
        # Bar 2 should NOT fire (only 2 up)
        assert 2 not in fire_indices

    def test_consecutive_down_3_days(self):
        """consecutive_down(3) should fire after 3 straight down-closes."""
        dates = pd.date_range("2024-01-01", periods=6, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "close": [100, 99, 98, 97, 98, 97],
            }
        )
        result = consecutive_down(3)(data)
        fire_indices = [i for i, v in enumerate(result) if v]
        # Bar 3: 3 consecutive down (99<100, 98<99, 97<98) → True
        assert 3 in fire_indices
        # Bars 4-5: broken streak
        assert 4 not in fire_indices

    def test_consecutive_up_1_day(self):
        """consecutive_up(1) should fire on every up bar."""
        dates = pd.date_range("2024-01-01", periods=4, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "close": [100, 101, 100, 102],
            }
        )
        result = consecutive_up(1)(data)
        assert result.iloc[1] == True
        assert result.iloc[2] == False
        assert result.iloc[3] == True

    def test_consecutive_empty_df(self):
        df = pd.DataFrame(columns=["underlying_symbol", "quote_date", "close"])
        assert len(consecutive_up(3)(df)) == 0
        assert len(consecutive_down(3)(df)) == 0
