"""Tests for momentum-based signal functions."""

import numpy as np
import pandas as pd
import pytest

from optopsy.signals import (
    _compute_rsi,
    ao_above,
    macd_cross_above,
    roc_above,
    roc_below,
    rsi_above,
    rsi_below,
    stoch_below,
    stochrsi_below,
    willr_above,
    willr_below,
)

# ============================================================================
# Local fixtures
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


# ============================================================================
# RSI
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


# ============================================================================
# MACD
# ============================================================================


class TestMACDSignals:
    def test_macd_cross_above_fires_after_v_recovery(self, macd_price_data_bullish):
        """MACD cross above should fire at least once after a V-shaped recovery."""
        result = macd_cross_above()(macd_price_data_bullish)
        assert result.any(), (
            "Expected at least one bullish MACD crossover in V-recovery"
        )

    def test_macd_cross_above_not_always_true(self, macd_price_data_bullish):
        """Crossover is an event, not a state — should not be True on every bar."""
        result = macd_cross_above()(macd_price_data_bullish)
        assert not result.all()


# ============================================================================
# Stochastic
# ============================================================================


class TestStochSignals:
    def test_stoch_below_with_downtrend_fires(self):
        dates = pd.date_range("2018-01-01", periods=40, freq="B")
        close = [100.0 - i * 2 for i in range(40)]
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": close,
                "high": [c + 0.5 for c in close],
                "low": [c - 0.5 for c in close],
            }
        )
        assert stoch_below(threshold=20)(data).any()


# ============================================================================
# StochRSI
# ============================================================================


class TestStochRSISignals:
    def test_stochrsi_custom_smoothing_params(self, price_data_100bars):
        result = stochrsi_below(period=14, rsi_period=14, k_smooth=3, d_smooth=3)(
            price_data_100bars
        )
        assert isinstance(result, pd.Series) and result.dtype == bool


# ============================================================================
# Williams %R
# ============================================================================


class TestWillRSignals:
    def test_willr_below_fires_on_downtrend(self):
        dates = pd.date_range("2018-01-01", periods=30, freq="B")
        close = [100.0 - i * 3 for i in range(30)]
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": close,
                "high": [c + 0.5 for c in close],
                "low": [c - 0.5 for c in close],
            }
        )
        assert willr_below(threshold=-80)(data).any()

    def test_willr_above_fires_on_uptrend(self):
        dates = pd.date_range("2018-01-01", periods=30, freq="B")
        close = [100.0 + i * 3 for i in range(30)]
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": close,
                "high": [c + 0.5 for c in close],
                "low": [c - 0.5 for c in close],
            }
        )
        assert willr_above(threshold=-20)(data).any()


# ============================================================================
# ROC
# ============================================================================


class TestROCSignals:
    def test_roc_above_fires_on_rapid_uptrend(self):
        dates = pd.date_range("2018-01-01", periods=20, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0 + i * 2 for i in range(20)],
            }
        )
        assert roc_above(threshold=0)(data).any()

    def test_roc_below_fires_on_rapid_downtrend(self):
        dates = pd.date_range("2018-01-01", periods=20, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0 - i * 2 for i in range(20)],
            }
        )
        assert roc_below(threshold=0)(data).any()


# ============================================================================
# AO
# ============================================================================


class TestAOSignals:
    def test_ao_above_fires_on_rising_trend(self, ohlcv_60bars):
        assert ao_above(threshold=0)(ohlcv_60bars).any()
