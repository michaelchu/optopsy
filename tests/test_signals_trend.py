"""Tests for trend-based signal functions."""

import pandas as pd

from optopsy.signals import (
    adx_above,
    adx_below,
    psar_buy,
    psar_sell,
)

# ============================================================================
# ADX
# ============================================================================


class TestADXSignals:
    def test_adx_below_very_high_threshold_fires(self, ohlcv_100bars):
        assert adx_below(threshold=100)(ohlcv_100bars).any()

    def test_adx_above_fires_on_strong_trend(self):
        dates = pd.date_range("2018-01-01", periods=60, freq="B")
        close = [100.0 + i * 5 for i in range(60)]
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "close": close,
                "high": [c + 1.0 for c in close],
                "low": [c - 1.0 for c in close],
            }
        )
        assert adx_above(threshold=1)(data).any()


# ============================================================================
# PSAR
# ============================================================================


class TestPSARSignals:
    def test_psar_fires_on_v_shaped_data(self):
        dates = pd.date_range("2018-01-01", periods=60, freq="B")
        close = [100.0 - i * 0.5 for i in range(30)] + [
            85.0 + i * 0.8 for i in range(30)
        ]
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "close": close,
                "high": [c + 1.0 for c in close],
                "low": [c - 1.0 for c in close],
            }
        )
        assert psar_buy()(data).any() or psar_sell()(data).any()
