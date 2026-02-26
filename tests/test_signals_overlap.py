"""Tests for overlap / moving-average crossover signal functions."""

import pandas as pd

from optopsy.signals import (
    dema_cross_above,
    ema_cross_above,
    hma_cross_above,
    sma_above,
    sma_below,
    tema_cross_above,
    wma_cross_above,
)

# ============================================================================
# SMA
# ============================================================================


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


# ============================================================================
# EMA crossover
# ============================================================================


class TestEMACrossoverSignals:
    def test_ema_cross_above_fires_on_rising_trend(self, cross_price_data):
        """Fast EMA should cross above slow EMA when trend turns bullish."""
        result = ema_cross_above(fast=5, slow=20)(cross_price_data)
        assert result.any(), "Expected at least one EMA golden cross"

    def test_ema_cross_above_not_always_true(self, cross_price_data):
        result = ema_cross_above(fast=5, slow=20)(cross_price_data)
        assert not result.all()


# ============================================================================
# DEMA / TEMA / HMA / KAMA / WMA / ZLMA / ALMA crossovers
# ============================================================================


class TestOverlapMASignals:
    def test_ma_crossovers_fire_on_rising_trend(self, cross_price_data):
        for fn in [
            dema_cross_above,
            tema_cross_above,
            hma_cross_above,
            wma_cross_above,
        ]:
            result = fn(fast=5, slow=20)(cross_price_data)
            assert result.any(), f"{fn.__name__} should fire on rising trend"
