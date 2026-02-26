"""Tests for trend-based signal functions."""

import pandas as pd
import pytest

from optopsy.signals import (
    adx_above,
    adx_below,
    aroon_cross_above,
    aroon_cross_below,
    chop_above,
    chop_below,
    psar_buy,
    psar_sell,
    supertrend_buy,
    supertrend_sell,
    vhf_above,
    vhf_below,
)

# ============================================================================
# Local fixtures
# ============================================================================


@pytest.fixture
def ohlcv_100bars():
    """100 bars of OHLCV data: declining then recovering."""
    dates = pd.date_range("2018-01-01", periods=100, freq="B")
    close = [100.0 - i * 0.3 for i in range(50)] + [85.0 + i * 0.4 for i in range(50)]
    return pd.DataFrame(
        {
            "underlying_symbol": "SPX",
            "quote_date": dates,
            "underlying_price": close,
            "high": [c + 2.0 for c in close],
            "low": [c - 2.0 for c in close],
        }
    )


# ============================================================================
# ADX
# ============================================================================


class TestADXSignals:
    def test_adx_above_returns_bool_series(self, ohlcv_60bars):
        result = adx_above()(ohlcv_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_adx_below_returns_bool_series(self, ohlcv_60bars):
        result = adx_below()(ohlcv_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_adx_above_length_matches_input(self, ohlcv_60bars):
        assert len(adx_above()(ohlcv_60bars)) == len(ohlcv_60bars)

    def test_adx_below_length_matches_input(self, ohlcv_60bars):
        assert len(adx_below()(ohlcv_60bars)) == len(ohlcv_60bars)

    def test_adx_insufficient_data_returns_all_false(self):
        dates = pd.date_range("2018-01-01", periods=3, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0, 101.0, 102.0],
            }
        )
        assert not adx_above()(data).any()
        assert not adx_below()(data).any()

    def test_adx_above_below_not_simultaneously_true(self, ohlcv_60bars):
        assert not (
            adx_above(threshold=25)(ohlcv_60bars)
            & adx_below(threshold=25)(ohlcv_60bars)
        ).any()

    def test_adx_below_very_high_threshold_fires(self, ohlcv_100bars):
        assert adx_below(threshold=100)(ohlcv_100bars).any()

    def test_adx_above_fires_on_strong_trend(self):
        dates = pd.date_range("2018-01-01", periods=60, freq="B")
        close = [100.0 + i * 5 for i in range(60)]
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": close,
                "high": [c + 1.0 for c in close],
                "low": [c - 1.0 for c in close],
            }
        )
        assert adx_above(threshold=1)(data).any()


# ============================================================================
# Aroon
# ============================================================================


class TestAroonSignals:
    def test_aroon_cross_above_returns_bool_series(self, ohlcv_60bars):
        result = aroon_cross_above()(ohlcv_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_aroon_cross_below_returns_bool_series(self, ohlcv_60bars):
        result = aroon_cross_below()(ohlcv_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_aroon_cross_above_length_matches_input(self, ohlcv_60bars):
        assert len(aroon_cross_above()(ohlcv_60bars)) == len(ohlcv_60bars)

    def test_aroon_cross_below_length_matches_input(self, ohlcv_60bars):
        assert len(aroon_cross_below()(ohlcv_60bars)) == len(ohlcv_60bars)

    def test_aroon_insufficient_data_returns_all_false(self):
        dates = pd.date_range("2018-01-01", periods=5, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0, 101.0, 102.0, 101.0, 100.0],
            }
        )
        assert not aroon_cross_above()(data).any()
        assert not aroon_cross_below()(data).any()

    def test_aroon_above_below_mutually_exclusive(self, ohlcv_100bars):
        assert not (
            aroon_cross_above()(ohlcv_100bars) & aroon_cross_below()(ohlcv_100bars)
        ).any()


# ============================================================================
# Supertrend
# ============================================================================


class TestSupertrendSignals:
    def test_supertrend_buy_returns_bool_series(self, ohlcv_60bars):
        result = supertrend_buy()(ohlcv_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_supertrend_sell_returns_bool_series(self, ohlcv_60bars):
        result = supertrend_sell()(ohlcv_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_supertrend_buy_length_matches_input(self, ohlcv_60bars):
        assert len(supertrend_buy()(ohlcv_60bars)) == len(ohlcv_60bars)

    def test_supertrend_sell_length_matches_input(self, ohlcv_60bars):
        assert len(supertrend_sell()(ohlcv_60bars)) == len(ohlcv_60bars)

    def test_supertrend_insufficient_data_returns_all_false(self):
        dates = pd.date_range("2018-01-01", periods=3, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0, 99.0, 98.0],
            }
        )
        assert not supertrend_buy()(data).any()
        assert not supertrend_sell()(data).any()

    def test_supertrend_buy_sell_mutually_exclusive(self, ohlcv_100bars):
        assert not (
            supertrend_buy()(ohlcv_100bars) & supertrend_sell()(ohlcv_100bars)
        ).any()


# ============================================================================
# PSAR
# ============================================================================


class TestPSARSignals:
    def test_psar_buy_returns_bool_series(self, ohlcv_60bars):
        result = psar_buy()(ohlcv_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_psar_sell_returns_bool_series(self, ohlcv_60bars):
        result = psar_sell()(ohlcv_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_psar_buy_length_matches_input(self, ohlcv_60bars):
        assert len(psar_buy()(ohlcv_60bars)) == len(ohlcv_60bars)

    def test_psar_sell_length_matches_input(self, ohlcv_60bars):
        assert len(psar_sell()(ohlcv_60bars)) == len(ohlcv_60bars)

    def test_psar_insufficient_data_returns_all_false(self):
        dates = pd.date_range("2018-01-01", periods=1, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0],
            }
        )
        assert not psar_buy()(data).any()
        assert not psar_sell()(data).any()

    def test_psar_buy_sell_mutually_exclusive(self, ohlcv_100bars):
        assert not (psar_buy()(ohlcv_100bars) & psar_sell()(ohlcv_100bars)).any()

    def test_psar_fires_on_v_shaped_data(self):
        dates = pd.date_range("2018-01-01", periods=60, freq="B")
        close = [100.0 - i * 0.5 for i in range(30)] + [
            85.0 + i * 0.8 for i in range(30)
        ]
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": close,
                "high": [c + 1.0 for c in close],
                "low": [c - 1.0 for c in close],
            }
        )
        assert psar_buy()(data).any() or psar_sell()(data).any()


# ============================================================================
# Choppiness Index
# ============================================================================


class TestChopSignals:
    def test_chop_above_returns_bool_series(self, ohlcv_60bars):
        result = chop_above()(ohlcv_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_chop_below_returns_bool_series(self, ohlcv_60bars):
        result = chop_below()(ohlcv_60bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_chop_above_length_matches_input(self, ohlcv_60bars):
        assert len(chop_above()(ohlcv_60bars)) == len(ohlcv_60bars)

    def test_chop_below_length_matches_input(self, ohlcv_60bars):
        assert len(chop_below()(ohlcv_60bars)) == len(ohlcv_60bars)

    def test_chop_insufficient_data_returns_all_false(self):
        dates = pd.date_range("2018-01-01", periods=3, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0, 101.0, 100.0],
            }
        )
        assert not chop_above()(data).any()
        assert not chop_below()(data).any()

    def test_chop_above_below_not_simultaneously_true(self, ohlcv_60bars):
        assert not (chop_above()(ohlcv_60bars) & chop_below()(ohlcv_60bars)).any()


# ============================================================================
# VHF
# ============================================================================


class TestVHFSignals:
    def test_vhf_above_returns_bool_series(self, price_data_100bars):
        result = vhf_above()(price_data_100bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_vhf_below_returns_bool_series(self, price_data_100bars):
        result = vhf_below()(price_data_100bars)
        assert isinstance(result, pd.Series) and result.dtype == bool

    def test_vhf_above_length_matches_input(self, price_data_100bars):
        assert len(vhf_above()(price_data_100bars)) == len(price_data_100bars)

    def test_vhf_below_length_matches_input(self, price_data_100bars):
        assert len(vhf_below()(price_data_100bars)) == len(price_data_100bars)

    def test_vhf_insufficient_data_returns_all_false(self):
        dates = pd.date_range("2018-01-01", periods=5, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0, 101.0, 102.0, 101.0, 100.0],
            }
        )
        assert not vhf_above()(data).any()
        assert not vhf_below()(data).any()

    def test_vhf_above_below_not_simultaneously_true(self, price_data_100bars):
        assert not (
            vhf_above()(price_data_100bars) & vhf_below()(price_data_100bars)
        ).any()
