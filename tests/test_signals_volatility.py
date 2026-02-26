"""Tests for volatility-based signal functions."""

import pandas as pd
import pytest

from optopsy.signals import (
    atr_above,
    atr_below,
    bb_above_upper,
    bb_below_lower,
    donchian_above_upper,
    donchian_below_lower,
    kc_above_upper,
    kc_below_lower,
    massi_above,
    massi_below,
    natr_above,
    natr_below,
)

# ============================================================================
# Local fixtures
# ============================================================================


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


# ============================================================================
# Bollinger Bands
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
        assert result.any(), (
            "Expected bb_above_upper to fire when price spikes far above bands"
        )
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
# ATR
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
        assert not (above == below).all(), (
            "Expected above and below to disagree on some bars"
        )

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
# Keltner Channel
# ============================================================================


class TestKeltnerChannelSignals:
    def test_kc_above_upper_returns_bool_series(self, ohlcv_60bars):
        result = kc_above_upper()(ohlcv_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_kc_below_lower_returns_bool_series(self, ohlcv_60bars):
        result = kc_below_lower()(ohlcv_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_kc_above_upper_length_matches_input(self, ohlcv_60bars):
        assert len(kc_above_upper()(ohlcv_60bars)) == len(ohlcv_60bars)

    def test_kc_below_lower_length_matches_input(self, ohlcv_60bars):
        assert len(kc_below_lower()(ohlcv_60bars)) == len(ohlcv_60bars)

    def test_kc_insufficient_data_returns_all_false(self):
        dates = pd.date_range("2018-01-01", periods=3, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0, 101.0, 102.0],
            }
        )
        assert not kc_above_upper()(data).any()
        assert not kc_below_lower()(data).any()

    def test_kc_above_below_not_simultaneously_true(self, ohlcv_60bars):
        assert not (
            kc_above_upper()(ohlcv_60bars) & kc_below_lower()(ohlcv_60bars)
        ).any()

    def test_kc_above_upper_fires_on_extreme_spike(self):
        dates = pd.date_range("2018-01-01", periods=30, freq="B")
        close = [100.0] * 25 + [300.0, 301.0, 302.0, 303.0, 304.0]
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": close,
                "high": [c + 1.0 for c in close],
                "low": [c - 1.0 for c in close],
            }
        )
        assert kc_above_upper()(data).any()


# ============================================================================
# Donchian Channel
# ============================================================================


class TestDonchianChannelSignals:
    def test_donchian_above_upper_returns_bool_series(self, ohlcv_60bars):
        result = donchian_above_upper()(ohlcv_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_donchian_below_lower_returns_bool_series(self, ohlcv_60bars):
        result = donchian_below_lower()(ohlcv_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_donchian_above_upper_length_matches_input(self, ohlcv_60bars):
        assert len(donchian_above_upper()(ohlcv_60bars)) == len(ohlcv_60bars)

    def test_donchian_below_lower_length_matches_input(self, ohlcv_60bars):
        assert len(donchian_below_lower()(ohlcv_60bars)) == len(ohlcv_60bars)

    def test_donchian_insufficient_data_returns_all_false(self):
        dates = pd.date_range("2018-01-01", periods=3, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0, 101.0, 102.0],
            }
        )
        assert not donchian_above_upper()(data).any()
        assert not donchian_below_lower()(data).any()

    def test_donchian_above_below_not_simultaneously_true(self, ohlcv_60bars):
        assert not (
            donchian_above_upper()(ohlcv_60bars) & donchian_below_lower()(ohlcv_60bars)
        ).any()


# ============================================================================
# NATR
# ============================================================================


class TestNATRSignals:
    def test_natr_above_returns_bool_series(self, ohlcv_60bars):
        result = natr_above()(ohlcv_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_natr_below_returns_bool_series(self, ohlcv_60bars):
        result = natr_below()(ohlcv_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_natr_above_length_matches_input(self, ohlcv_60bars):
        assert len(natr_above()(ohlcv_60bars)) == len(ohlcv_60bars)

    def test_natr_below_length_matches_input(self, ohlcv_60bars):
        assert len(natr_below()(ohlcv_60bars)) == len(ohlcv_60bars)

    def test_natr_insufficient_data_returns_all_false(self):
        dates = pd.date_range("2018-01-01", periods=3, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0, 101.0, 102.0],
            }
        )
        assert not natr_above()(data).any()
        assert not natr_below()(data).any()

    def test_natr_above_below_not_simultaneously_true(self, ohlcv_60bars):
        assert not (
            natr_above(threshold=2.0)(ohlcv_60bars)
            & natr_below(threshold=2.0)(ohlcv_60bars)
        ).any()

    def test_natr_below_high_threshold_fires(self, ohlcv_60bars):
        assert natr_below(threshold=100)(ohlcv_60bars).any()


# ============================================================================
# Mass Index
# ============================================================================


class TestMassIndexSignals:
    def test_massi_above_returns_bool_series(self, ohlcv_60bars):
        result = massi_above()(ohlcv_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_massi_below_returns_bool_series(self, ohlcv_60bars):
        result = massi_below()(ohlcv_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_massi_above_length_matches_input(self, ohlcv_60bars):
        assert len(massi_above()(ohlcv_60bars)) == len(ohlcv_60bars)

    def test_massi_below_length_matches_input(self, ohlcv_60bars):
        assert len(massi_below()(ohlcv_60bars)) == len(ohlcv_60bars)

    def test_massi_insufficient_data_returns_all_false(self):
        dates = pd.date_range("2018-01-01", periods=5, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0, 101.0, 102.0, 101.0, 100.0],
            }
        )
        assert not massi_above()(data).any()
        assert not massi_below()(data).any()

    def test_massi_below_very_high_threshold_fires(self, ohlcv_60bars):
        assert massi_below(threshold=1000)(ohlcv_60bars).any()
