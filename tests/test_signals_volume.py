"""Tests for volume-based signal functions."""

import pandas as pd
import pytest

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
# Local fixtures
# ============================================================================


@pytest.fixture
def ohlcv_with_volume_60bars():
    """60 bars of OHLCV+volume data for volume-based signals."""
    dates = pd.date_range("2018-01-01", periods=60, freq="B")
    close = [100.0 + i * 0.5 for i in range(60)]
    return pd.DataFrame(
        {
            "underlying_symbol": "SPX",
            "quote_date": dates,
            "underlying_price": close,
            "high": [c + 2.0 for c in close],
            "low": [c - 2.0 for c in close],
            "volume": [1_000_000 + i * 5000 for i in range(60)],
        }
    )


@pytest.fixture
def ohlcv_with_volume_100bars():
    """100 bars of OHLCV+volume data: declining then recovering."""
    dates = pd.date_range("2018-01-01", periods=100, freq="B")
    close = [100.0 - i * 0.3 for i in range(50)] + [85.0 + i * 0.4 for i in range(50)]
    return pd.DataFrame(
        {
            "underlying_symbol": "SPX",
            "quote_date": dates,
            "underlying_price": close,
            "high": [c + 2.0 for c in close],
            "low": [c - 2.0 for c in close],
            "volume": [1_000_000 + i * 3000 for i in range(100)],
        }
    )


# ============================================================================
# MFI
# ============================================================================


class TestMFISignals:
    def test_mfi_above_returns_bool_series(self, ohlcv_with_volume_60bars):
        result = mfi_above()(ohlcv_with_volume_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_mfi_below_returns_bool_series(self, ohlcv_with_volume_60bars):
        result = mfi_below()(ohlcv_with_volume_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_mfi_above_length_matches_input(self, ohlcv_with_volume_60bars):
        assert len(mfi_above()(ohlcv_with_volume_60bars)) == len(
            ohlcv_with_volume_60bars
        )

    def test_mfi_below_length_matches_input(self, ohlcv_with_volume_60bars):
        assert len(mfi_below()(ohlcv_with_volume_60bars)) == len(
            ohlcv_with_volume_60bars
        )

    def test_mfi_no_volume_returns_all_false(self, ohlcv_60bars):
        assert not mfi_above()(ohlcv_60bars).any()
        assert not mfi_below()(ohlcv_60bars).any()

    def test_mfi_insufficient_data_returns_all_false(self):
        dates = pd.date_range("2018-01-01", periods=3, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0, 101.0, 102.0],
                "high": [101.0, 102.0, 103.0],
                "low": [99.0, 100.0, 101.0],
                "volume": [1000, 1100, 1200],
            }
        )
        assert not mfi_above()(data).any()
        assert not mfi_below()(data).any()

    def test_mfi_above_below_not_simultaneously_true(self, ohlcv_with_volume_60bars):
        assert not (
            mfi_above()(ohlcv_with_volume_60bars)
            & mfi_below()(ohlcv_with_volume_60bars)
        ).any()


# ============================================================================
# OBV
# ============================================================================


class TestOBVSignals:
    def test_obv_cross_above_sma_returns_bool_series(self, ohlcv_with_volume_60bars):
        result = obv_cross_above_sma()(ohlcv_with_volume_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_obv_cross_below_sma_returns_bool_series(self, ohlcv_with_volume_60bars):
        result = obv_cross_below_sma()(ohlcv_with_volume_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_obv_cross_above_sma_length_matches_input(self, ohlcv_with_volume_60bars):
        assert len(obv_cross_above_sma()(ohlcv_with_volume_60bars)) == len(
            ohlcv_with_volume_60bars
        )

    def test_obv_cross_below_sma_length_matches_input(self, ohlcv_with_volume_60bars):
        assert len(obv_cross_below_sma()(ohlcv_with_volume_60bars)) == len(
            ohlcv_with_volume_60bars
        )

    def test_obv_no_volume_returns_all_false(self, ohlcv_60bars):
        assert not obv_cross_above_sma()(ohlcv_60bars).any()
        assert not obv_cross_below_sma()(ohlcv_60bars).any()

    def test_obv_insufficient_data_returns_all_false(self):
        dates = pd.date_range("2018-01-01", periods=3, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0, 101.0, 102.0],
                "volume": [1000, 1100, 1200],
            }
        )
        assert not obv_cross_above_sma()(data).any()
        assert not obv_cross_below_sma()(data).any()

    def test_obv_above_below_mutually_exclusive(self, ohlcv_with_volume_100bars):
        assert not (
            obv_cross_above_sma()(ohlcv_with_volume_100bars)
            & obv_cross_below_sma()(ohlcv_with_volume_100bars)
        ).any()


# ============================================================================
# CMF
# ============================================================================


class TestCMFSignals:
    def test_cmf_above_returns_bool_series(self, ohlcv_with_volume_60bars):
        result = cmf_above()(ohlcv_with_volume_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_cmf_below_returns_bool_series(self, ohlcv_with_volume_60bars):
        result = cmf_below()(ohlcv_with_volume_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_cmf_above_length_matches_input(self, ohlcv_with_volume_60bars):
        assert len(cmf_above()(ohlcv_with_volume_60bars)) == len(
            ohlcv_with_volume_60bars
        )

    def test_cmf_below_length_matches_input(self, ohlcv_with_volume_60bars):
        assert len(cmf_below()(ohlcv_with_volume_60bars)) == len(
            ohlcv_with_volume_60bars
        )

    def test_cmf_no_volume_returns_all_false(self, ohlcv_60bars):
        assert not cmf_above()(ohlcv_60bars).any()
        assert not cmf_below()(ohlcv_60bars).any()

    def test_cmf_insufficient_data_returns_all_false(self):
        dates = pd.date_range("2018-01-01", periods=3, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0, 101.0, 102.0],
                "high": [101.0, 102.0, 103.0],
                "low": [99.0, 100.0, 101.0],
                "volume": [1000, 1100, 1200],
            }
        )
        assert not cmf_above()(data).any()
        assert not cmf_below()(data).any()


# ============================================================================
# AD
# ============================================================================


class TestADSignals:
    def test_ad_cross_above_sma_returns_bool_series(self, ohlcv_with_volume_60bars):
        result = ad_cross_above_sma()(ohlcv_with_volume_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_ad_cross_below_sma_returns_bool_series(self, ohlcv_with_volume_60bars):
        result = ad_cross_below_sma()(ohlcv_with_volume_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_ad_cross_above_sma_length_matches_input(self, ohlcv_with_volume_60bars):
        assert len(ad_cross_above_sma()(ohlcv_with_volume_60bars)) == len(
            ohlcv_with_volume_60bars
        )

    def test_ad_cross_below_sma_length_matches_input(self, ohlcv_with_volume_60bars):
        assert len(ad_cross_below_sma()(ohlcv_with_volume_60bars)) == len(
            ohlcv_with_volume_60bars
        )

    def test_ad_no_volume_returns_all_false(self, ohlcv_60bars):
        assert not ad_cross_above_sma()(ohlcv_60bars).any()
        assert not ad_cross_below_sma()(ohlcv_60bars).any()

    def test_ad_insufficient_data_returns_all_false(self):
        dates = pd.date_range("2018-01-01", periods=3, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0, 101.0, 102.0],
                "high": [101.0, 102.0, 103.0],
                "low": [99.0, 100.0, 101.0],
                "volume": [1000, 1100, 1200],
            }
        )
        assert not ad_cross_above_sma()(data).any()
        assert not ad_cross_below_sma()(data).any()

    def test_ad_above_below_mutually_exclusive(self, ohlcv_with_volume_100bars):
        assert not (
            ad_cross_above_sma()(ohlcv_with_volume_100bars)
            & ad_cross_below_sma()(ohlcv_with_volume_100bars)
        ).any()
