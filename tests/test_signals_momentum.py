"""Tests for momentum-based signal functions."""

import numpy as np
import pandas as pd
import pytest

from optopsy.signals import (
    _compute_rsi,
    ao_above,
    ao_below,
    cci_above,
    cci_below,
    cmo_above,
    cmo_below,
    fisher_cross_above,
    fisher_cross_below,
    kst_cross_above,
    kst_cross_below,
    macd_cross_above,
    macd_cross_below,
    ppo_cross_above,
    ppo_cross_below,
    roc_above,
    roc_below,
    rsi_above,
    rsi_below,
    smi_cross_above,
    smi_cross_below,
    squeeze_off,
    squeeze_on,
    stoch_above,
    stoch_below,
    stochrsi_above,
    stochrsi_below,
    tsi_cross_above,
    tsi_cross_below,
    uo_above,
    uo_below,
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
        assert result.any(), (
            "Expected at least one bullish MACD crossover in V-recovery"
        )

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
# Stochastic
# ============================================================================


class TestStochSignals:
    def test_stoch_below_returns_bool_series(self, ohlcv_60bars):
        result = stoch_below()(ohlcv_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_stoch_above_returns_bool_series(self, ohlcv_60bars):
        result = stoch_above()(ohlcv_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_stoch_below_length_matches_input(self, ohlcv_60bars):
        assert len(stoch_below()(ohlcv_60bars)) == len(ohlcv_60bars)

    def test_stoch_above_length_matches_input(self, ohlcv_60bars):
        assert len(stoch_above()(ohlcv_60bars)) == len(ohlcv_60bars)

    def test_stoch_insufficient_data_returns_all_false(self):
        dates = pd.date_range("2018-01-01", periods=3, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0, 99.0, 98.0],
            }
        )
        assert not stoch_below()(data).any()
        assert not stoch_above()(data).any()

    def test_stoch_above_below_not_simultaneously_true(self, ohlcv_60bars):
        assert not (stoch_above()(ohlcv_60bars) & stoch_below()(ohlcv_60bars)).any()

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
    def test_stochrsi_below_returns_bool_series(self, price_data_100bars):
        result = stochrsi_below()(price_data_100bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_stochrsi_above_returns_bool_series(self, price_data_100bars):
        result = stochrsi_above()(price_data_100bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_stochrsi_below_length_matches_input(self, price_data_100bars):
        assert len(stochrsi_below()(price_data_100bars)) == len(price_data_100bars)

    def test_stochrsi_above_length_matches_input(self, price_data_100bars):
        assert len(stochrsi_above()(price_data_100bars)) == len(price_data_100bars)

    def test_stochrsi_insufficient_data_returns_all_false(self):
        dates = pd.date_range("2018-01-01", periods=5, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0, 99.0, 98.0, 97.0, 96.0],
            }
        )
        assert not stochrsi_below()(data).any()
        assert not stochrsi_above()(data).any()

    def test_stochrsi_custom_smoothing_params(self, price_data_100bars):
        result = stochrsi_below(period=14, rsi_period=14, k_smooth=3, d_smooth=3)(
            price_data_100bars
        )
        assert isinstance(result, pd.Series) and result.dtype == bool


# ============================================================================
# Williams %R
# ============================================================================


class TestWillRSignals:
    def test_willr_below_returns_bool_series(self, ohlcv_60bars):
        result = willr_below()(ohlcv_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_willr_above_returns_bool_series(self, ohlcv_60bars):
        result = willr_above()(ohlcv_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_willr_below_length_matches_input(self, ohlcv_60bars):
        assert len(willr_below()(ohlcv_60bars)) == len(ohlcv_60bars)

    def test_willr_above_length_matches_input(self, ohlcv_60bars):
        assert len(willr_above()(ohlcv_60bars)) == len(ohlcv_60bars)

    def test_willr_insufficient_data_returns_all_false(self):
        dates = pd.date_range("2018-01-01", periods=3, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0, 99.0, 98.0],
            }
        )
        assert not willr_below()(data).any()
        assert not willr_above()(data).any()

    def test_willr_above_below_not_simultaneously_true(self, ohlcv_60bars):
        assert not (willr_above()(ohlcv_60bars) & willr_below()(ohlcv_60bars)).any()

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
# CCI
# ============================================================================


class TestCCISignals:
    def test_cci_below_returns_bool_series(self, ohlcv_60bars):
        result = cci_below()(ohlcv_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_cci_above_returns_bool_series(self, ohlcv_60bars):
        result = cci_above()(ohlcv_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_cci_below_length_matches_input(self, ohlcv_60bars):
        assert len(cci_below()(ohlcv_60bars)) == len(ohlcv_60bars)

    def test_cci_above_length_matches_input(self, ohlcv_60bars):
        assert len(cci_above()(ohlcv_60bars)) == len(ohlcv_60bars)

    def test_cci_insufficient_data_returns_all_false(self):
        dates = pd.date_range("2018-01-01", periods=5, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0] * 5,
            }
        )
        assert not cci_below()(data).any()
        assert not cci_above()(data).any()

    def test_cci_above_below_not_simultaneously_true(self, ohlcv_60bars):
        assert not (cci_above()(ohlcv_60bars) & cci_below()(ohlcv_60bars)).any()


# ============================================================================
# ROC
# ============================================================================


class TestROCSignals:
    def test_roc_above_returns_bool_series(self, price_data_100bars):
        result = roc_above()(price_data_100bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_roc_below_returns_bool_series(self, price_data_100bars):
        result = roc_below()(price_data_100bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_roc_above_length_matches_input(self, price_data_100bars):
        assert len(roc_above()(price_data_100bars)) == len(price_data_100bars)

    def test_roc_below_length_matches_input(self, price_data_100bars):
        assert len(roc_below()(price_data_100bars)) == len(price_data_100bars)

    def test_roc_insufficient_data_returns_all_false(self):
        dates = pd.date_range("2018-01-01", periods=3, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0, 101.0, 102.0],
            }
        )
        assert not roc_above()(data).any()
        assert not roc_below()(data).any()

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
# PPO
# ============================================================================


class TestPPOSignals:
    def test_ppo_cross_above_returns_bool_series(self, price_data_100bars):
        result = ppo_cross_above()(price_data_100bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_ppo_cross_below_returns_bool_series(self, price_data_100bars):
        result = ppo_cross_below()(price_data_100bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_ppo_cross_above_length_matches_input(self, price_data_100bars):
        assert len(ppo_cross_above()(price_data_100bars)) == len(price_data_100bars)

    def test_ppo_cross_below_length_matches_input(self, price_data_100bars):
        assert len(ppo_cross_below()(price_data_100bars)) == len(price_data_100bars)

    def test_ppo_insufficient_data_returns_all_false(self):
        dates = pd.date_range("2018-01-01", periods=5, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0] * 5,
            }
        )
        assert not ppo_cross_above()(data).any()
        assert not ppo_cross_below()(data).any()

    def test_ppo_above_below_mutually_exclusive(self, price_data_100bars):
        assert not (
            ppo_cross_above()(price_data_100bars)
            & ppo_cross_below()(price_data_100bars)
        ).any()


# ============================================================================
# TSI
# ============================================================================


class TestTSISignals:
    def test_tsi_cross_above_returns_bool_series(self, price_data_100bars):
        result = tsi_cross_above()(price_data_100bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_tsi_cross_below_returns_bool_series(self, price_data_100bars):
        result = tsi_cross_below()(price_data_100bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_tsi_cross_above_length_matches_input(self, price_data_100bars):
        assert len(tsi_cross_above()(price_data_100bars)) == len(price_data_100bars)

    def test_tsi_cross_below_length_matches_input(self, price_data_100bars):
        assert len(tsi_cross_below()(price_data_100bars)) == len(price_data_100bars)

    def test_tsi_insufficient_data_returns_all_false(self):
        dates = pd.date_range("2018-01-01", periods=5, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0, 101.0, 102.0, 101.0, 100.0],
            }
        )
        assert not tsi_cross_above()(data).any()
        assert not tsi_cross_below()(data).any()

    def test_tsi_above_below_mutually_exclusive(self, price_data_100bars):
        assert not (
            tsi_cross_above()(price_data_100bars)
            & tsi_cross_below()(price_data_100bars)
        ).any()


# ============================================================================
# CMO
# ============================================================================


class TestCMOSignals:
    def test_cmo_above_returns_bool_series(self, price_data_100bars):
        result = cmo_above()(price_data_100bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_cmo_below_returns_bool_series(self, price_data_100bars):
        result = cmo_below()(price_data_100bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_cmo_above_length_matches_input(self, price_data_100bars):
        assert len(cmo_above()(price_data_100bars)) == len(price_data_100bars)

    def test_cmo_below_length_matches_input(self, price_data_100bars):
        assert len(cmo_below()(price_data_100bars)) == len(price_data_100bars)

    def test_cmo_insufficient_data_returns_all_false(self):
        dates = pd.date_range("2018-01-01", periods=3, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0, 101.0, 102.0],
            }
        )
        assert not cmo_above()(data).any()
        assert not cmo_below()(data).any()

    def test_cmo_above_below_not_simultaneously_true(self, price_data_100bars):
        assert not (
            cmo_above()(price_data_100bars) & cmo_below()(price_data_100bars)
        ).any()


# ============================================================================
# UO
# ============================================================================


class TestUOSignals:
    def test_uo_above_returns_bool_series(self, ohlcv_60bars):
        result = uo_above()(ohlcv_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_uo_below_returns_bool_series(self, ohlcv_60bars):
        result = uo_below()(ohlcv_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_uo_above_length_matches_input(self, ohlcv_60bars):
        assert len(uo_above()(ohlcv_60bars)) == len(ohlcv_60bars)

    def test_uo_below_length_matches_input(self, ohlcv_60bars):
        assert len(uo_below()(ohlcv_60bars)) == len(ohlcv_60bars)

    def test_uo_insufficient_data_returns_all_false(self):
        dates = pd.date_range("2018-01-01", periods=3, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0, 99.0, 98.0],
            }
        )
        assert not uo_above()(data).any()
        assert not uo_below()(data).any()

    def test_uo_above_below_not_simultaneously_true(self, ohlcv_60bars):
        assert not (uo_above()(ohlcv_60bars) & uo_below()(ohlcv_60bars)).any()


# ============================================================================
# Squeeze
# ============================================================================


class TestSqueezeSignals:
    def test_squeeze_on_returns_bool_series(self, ohlcv_60bars):
        result = squeeze_on()(ohlcv_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_squeeze_off_returns_bool_series(self, ohlcv_60bars):
        result = squeeze_off()(ohlcv_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_squeeze_on_length_matches_input(self, ohlcv_60bars):
        assert len(squeeze_on()(ohlcv_60bars)) == len(ohlcv_60bars)

    def test_squeeze_off_length_matches_input(self, ohlcv_60bars):
        assert len(squeeze_off()(ohlcv_60bars)) == len(ohlcv_60bars)

    def test_squeeze_insufficient_data_returns_all_false(self):
        dates = pd.date_range("2018-01-01", periods=5, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0] * 5,
            }
        )
        assert not squeeze_on()(data).any()
        assert not squeeze_off()(data).any()


# ============================================================================
# AO
# ============================================================================


class TestAOSignals:
    def test_ao_above_returns_bool_series(self, ohlcv_60bars):
        result = ao_above()(ohlcv_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_ao_below_returns_bool_series(self, ohlcv_60bars):
        result = ao_below()(ohlcv_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_ao_above_length_matches_input(self, ohlcv_60bars):
        assert len(ao_above()(ohlcv_60bars)) == len(ohlcv_60bars)

    def test_ao_below_length_matches_input(self, ohlcv_60bars):
        assert len(ao_below()(ohlcv_60bars)) == len(ohlcv_60bars)

    def test_ao_insufficient_data_returns_all_false(self):
        dates = pd.date_range("2018-01-01", periods=5, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0, 101.0, 102.0, 101.0, 100.0],
            }
        )
        assert not ao_above()(data).any()
        assert not ao_below()(data).any()

    def test_ao_above_fires_on_rising_trend(self, ohlcv_60bars):
        assert ao_above(threshold=0)(ohlcv_60bars).any()


# ============================================================================
# SMI
# ============================================================================


class TestSMISignals:
    def test_smi_cross_above_returns_bool_series(self, price_data_100bars):
        result = smi_cross_above()(price_data_100bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_smi_cross_below_returns_bool_series(self, price_data_100bars):
        result = smi_cross_below()(price_data_100bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_smi_cross_above_length_matches_input(self, price_data_100bars):
        assert len(smi_cross_above()(price_data_100bars)) == len(price_data_100bars)

    def test_smi_cross_below_length_matches_input(self, price_data_100bars):
        assert len(smi_cross_below()(price_data_100bars)) == len(price_data_100bars)

    def test_smi_insufficient_data_returns_all_false(self):
        dates = pd.date_range("2018-01-01", periods=5, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0, 101.0, 102.0, 101.0, 100.0],
            }
        )
        assert not smi_cross_above()(data).any()
        assert not smi_cross_below()(data).any()

    def test_smi_above_below_mutually_exclusive(self, price_data_100bars):
        assert not (
            smi_cross_above()(price_data_100bars)
            & smi_cross_below()(price_data_100bars)
        ).any()


# ============================================================================
# KST
# ============================================================================


class TestKSTSignals:
    def test_kst_cross_above_returns_bool_series(self, price_data_100bars):
        result = kst_cross_above()(price_data_100bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_kst_cross_below_returns_bool_series(self, price_data_100bars):
        result = kst_cross_below()(price_data_100bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_kst_cross_above_length_matches_input(self, price_data_100bars):
        assert len(kst_cross_above()(price_data_100bars)) == len(price_data_100bars)

    def test_kst_cross_below_length_matches_input(self, price_data_100bars):
        assert len(kst_cross_below()(price_data_100bars)) == len(price_data_100bars)

    def test_kst_insufficient_data_returns_all_false(self):
        dates = pd.date_range("2018-01-01", periods=5, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0, 101.0, 102.0, 101.0, 100.0],
            }
        )
        assert not kst_cross_above()(data).any()
        assert not kst_cross_below()(data).any()

    def test_kst_above_below_mutually_exclusive(self, price_data_100bars):
        assert not (
            kst_cross_above()(price_data_100bars)
            & kst_cross_below()(price_data_100bars)
        ).any()


# ============================================================================
# Fisher Transform
# ============================================================================


class TestFisherSignals:
    def test_fisher_cross_above_returns_bool_series(self, price_data_100bars):
        result = fisher_cross_above()(price_data_100bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_fisher_cross_below_returns_bool_series(self, price_data_100bars):
        result = fisher_cross_below()(price_data_100bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_fisher_cross_above_length_matches_input(self, price_data_100bars):
        assert len(fisher_cross_above()(price_data_100bars)) == len(price_data_100bars)

    def test_fisher_cross_below_length_matches_input(self, price_data_100bars):
        assert len(fisher_cross_below()(price_data_100bars)) == len(price_data_100bars)

    def test_fisher_insufficient_data_returns_all_false(self):
        dates = pd.date_range("2018-01-01", periods=3, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0, 101.0, 102.0],
            }
        )
        assert not fisher_cross_above()(data).any()
        assert not fisher_cross_below()(data).any()

    def test_fisher_above_below_mutually_exclusive(self, price_data_100bars):
        assert not (
            fisher_cross_above()(price_data_100bars)
            & fisher_cross_below()(price_data_100bars)
        ).any()
