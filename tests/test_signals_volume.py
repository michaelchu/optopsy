"""Tests for volume-based signal functions."""

from optopsy.signals import (
    ad_cross_above_sma,
    ad_cross_below_sma,
    cmf_above,
    cmf_below,
    mfi_above,
    mfi_below,
    obv_cross_above_sma,
    obv_cross_below_sma,
)

# ============================================================================
# MFI
# ============================================================================


class TestMFISignals:
    def test_mfi_no_volume_returns_all_false(self, ohlcv_60bars):
        assert not mfi_above()(ohlcv_60bars).any()
        assert not mfi_below()(ohlcv_60bars).any()


# ============================================================================
# OBV
# ============================================================================


class TestOBVSignals:
    def test_obv_no_volume_returns_all_false(self, ohlcv_60bars):
        assert not obv_cross_above_sma()(ohlcv_60bars).any()
        assert not obv_cross_below_sma()(ohlcv_60bars).any()


# ============================================================================
# CMF
# ============================================================================


class TestCMFSignals:
    def test_cmf_no_volume_returns_all_false(self, ohlcv_60bars):
        assert not cmf_above()(ohlcv_60bars).any()
        assert not cmf_below()(ohlcv_60bars).any()


# ============================================================================
# AD
# ============================================================================


class TestADSignals:
    def test_ad_no_volume_returns_all_false(self, ohlcv_60bars):
        assert not ad_cross_above_sma()(ohlcv_60bars).any()
        assert not ad_cross_below_sma()(ohlcv_60bars).any()
