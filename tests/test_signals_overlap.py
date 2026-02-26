"""Tests for overlap / moving-average crossover signal functions."""

import pandas as pd
import pytest

from optopsy.signals import (
    alma_cross_above,
    alma_cross_below,
    dema_cross_above,
    dema_cross_below,
    ema_cross_above,
    ema_cross_below,
    hma_cross_above,
    hma_cross_below,
    kama_cross_above,
    kama_cross_below,
    sma_above,
    sma_below,
    tema_cross_above,
    tema_cross_below,
    wma_cross_above,
    wma_cross_below,
    zlma_cross_above,
    zlma_cross_below,
)

# ============================================================================
# Local fixtures
# ============================================================================


@pytest.fixture
def ema_cross_data():
    """60 bars: flat then sharply rising to force fast EMA above slow EMA."""
    dates = pd.date_range("2018-01-01", periods=60, freq="B")
    prices = [100.0] * 30 + [100.0 + i * 2 for i in range(30)]
    return pd.DataFrame(
        {
            "underlying_symbol": "SPX",
            "quote_date": dates,
            "underlying_price": prices,
        }
    )


@pytest.fixture
def cross_price_data():
    """60 bars: flat then sharply rising to force fast MA above slow MA."""
    dates = pd.date_range("2018-01-01", periods=60, freq="B")
    prices = [100.0] * 30 + [100.0 + i * 2 for i in range(30)]
    return pd.DataFrame(
        {
            "underlying_symbol": "SPX",
            "quote_date": dates,
            "underlying_price": prices,
        }
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
    def test_ema_cross_above_returns_bool_series(self, ema_cross_data):
        result = ema_cross_above(fast=5, slow=20)(ema_cross_data)
        assert isinstance(result, pd.Series)
        assert result.dtype == bool

    def test_ema_cross_below_returns_bool_series(self, ema_cross_data):
        result = ema_cross_below(fast=5, slow=20)(ema_cross_data)
        assert isinstance(result, pd.Series)
        assert result.dtype == bool

    def test_ema_cross_above_fires_on_rising_trend(self, ema_cross_data):
        """Fast EMA should cross above slow EMA when trend turns bullish."""
        result = ema_cross_above(fast=5, slow=20)(ema_cross_data)
        assert result.any(), "Expected at least one EMA golden cross"

    def test_ema_cross_above_not_always_true(self, ema_cross_data):
        result = ema_cross_above(fast=5, slow=20)(ema_cross_data)
        assert not result.all()

    def test_ema_cross_above_below_mutually_exclusive(self, ema_cross_data):
        above = ema_cross_above(fast=5, slow=20)(ema_cross_data)
        below = ema_cross_below(fast=5, slow=20)(ema_cross_data)
        assert not (above & below).any()

    def test_ema_cross_insufficient_data_returns_all_false(self):
        """With fewer bars than slow period, EMA cross should return all False."""
        dates = pd.date_range("2018-01-01", periods=5, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0 + i for i in range(5)],
            }
        )
        result = ema_cross_above(fast=5, slow=50)(data)
        assert not result.any()

    def test_ema_cross_length_matches_input(self, ema_cross_data):
        assert len(ema_cross_above(fast=5, slow=20)(ema_cross_data)) == len(
            ema_cross_data
        )


# ============================================================================
# DEMA / TEMA / HMA / KAMA / WMA / ZLMA / ALMA crossovers
# ============================================================================


class TestOverlapMASignals:
    def test_dema_cross_above_returns_bool_series(self, cross_price_data):
        assert dema_cross_above()(cross_price_data).dtype == bool

    def test_dema_cross_below_returns_bool_series(self, cross_price_data):
        assert dema_cross_below()(cross_price_data).dtype == bool

    def test_dema_cross_length_matches_input(self, cross_price_data):
        assert len(dema_cross_above()(cross_price_data)) == len(cross_price_data)
        assert len(dema_cross_below()(cross_price_data)) == len(cross_price_data)

    def test_dema_insufficient_data_returns_all_false(self):
        dates = pd.date_range("2018-01-01", periods=5, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0] * 5,
            }
        )
        assert not dema_cross_above()(data).any()
        assert not dema_cross_below()(data).any()

    def test_dema_above_below_mutually_exclusive(self, cross_price_data):
        assert not (
            dema_cross_above()(cross_price_data) & dema_cross_below()(cross_price_data)
        ).any()

    def test_tema_cross_above_returns_bool_series(self, cross_price_data):
        assert tema_cross_above()(cross_price_data).dtype == bool

    def test_tema_cross_below_returns_bool_series(self, cross_price_data):
        assert tema_cross_below()(cross_price_data).dtype == bool

    def test_tema_cross_length_matches_input(self, cross_price_data):
        assert len(tema_cross_above()(cross_price_data)) == len(cross_price_data)
        assert len(tema_cross_below()(cross_price_data)) == len(cross_price_data)

    def test_tema_insufficient_data_returns_all_false(self):
        dates = pd.date_range("2018-01-01", periods=5, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0] * 5,
            }
        )
        assert not tema_cross_above()(data).any()
        assert not tema_cross_below()(data).any()

    def test_hma_cross_above_returns_bool_series(self, cross_price_data):
        assert hma_cross_above()(cross_price_data).dtype == bool

    def test_hma_cross_below_returns_bool_series(self, cross_price_data):
        assert hma_cross_below()(cross_price_data).dtype == bool

    def test_hma_cross_length_matches_input(self, cross_price_data):
        assert len(hma_cross_above()(cross_price_data)) == len(cross_price_data)
        assert len(hma_cross_below()(cross_price_data)) == len(cross_price_data)

    def test_hma_insufficient_data_returns_all_false(self):
        dates = pd.date_range("2018-01-01", periods=5, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0] * 5,
            }
        )
        assert not hma_cross_above()(data).any()
        assert not hma_cross_below()(data).any()

    def test_kama_cross_above_returns_bool_series(self, cross_price_data):
        assert kama_cross_above()(cross_price_data).dtype == bool

    def test_kama_cross_below_returns_bool_series(self, cross_price_data):
        assert kama_cross_below()(cross_price_data).dtype == bool

    def test_kama_cross_length_matches_input(self, cross_price_data):
        assert len(kama_cross_above()(cross_price_data)) == len(cross_price_data)
        assert len(kama_cross_below()(cross_price_data)) == len(cross_price_data)

    def test_kama_insufficient_data_returns_all_false(self):
        dates = pd.date_range("2018-01-01", periods=3, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0, 101.0, 102.0],
            }
        )
        assert not kama_cross_above()(data).any()
        assert not kama_cross_below()(data).any()

    def test_wma_cross_above_returns_bool_series(self, cross_price_data):
        assert wma_cross_above()(cross_price_data).dtype == bool

    def test_wma_cross_below_returns_bool_series(self, cross_price_data):
        assert wma_cross_below()(cross_price_data).dtype == bool

    def test_wma_cross_length_matches_input(self, cross_price_data):
        assert len(wma_cross_above()(cross_price_data)) == len(cross_price_data)
        assert len(wma_cross_below()(cross_price_data)) == len(cross_price_data)

    def test_wma_insufficient_data_returns_all_false(self):
        dates = pd.date_range("2018-01-01", periods=3, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0, 101.0, 102.0],
            }
        )
        assert not wma_cross_above()(data).any()
        assert not wma_cross_below()(data).any()

    def test_zlma_cross_above_returns_bool_series(self, cross_price_data):
        assert zlma_cross_above()(cross_price_data).dtype == bool

    def test_zlma_cross_below_returns_bool_series(self, cross_price_data):
        assert zlma_cross_below()(cross_price_data).dtype == bool

    def test_zlma_cross_length_matches_input(self, cross_price_data):
        assert len(zlma_cross_above()(cross_price_data)) == len(cross_price_data)
        assert len(zlma_cross_below()(cross_price_data)) == len(cross_price_data)

    def test_zlma_insufficient_data_returns_all_false(self):
        dates = pd.date_range("2018-01-01", periods=3, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0, 101.0, 102.0],
            }
        )
        assert not zlma_cross_above()(data).any()
        assert not zlma_cross_below()(data).any()

    def test_alma_cross_above_returns_bool_series(self, cross_price_data):
        assert alma_cross_above()(cross_price_data).dtype == bool

    def test_alma_cross_below_returns_bool_series(self, cross_price_data):
        assert alma_cross_below()(cross_price_data).dtype == bool

    def test_alma_cross_length_matches_input(self, cross_price_data):
        assert len(alma_cross_above()(cross_price_data)) == len(cross_price_data)
        assert len(alma_cross_below()(cross_price_data)) == len(cross_price_data)

    def test_alma_insufficient_data_returns_all_false(self):
        dates = pd.date_range("2018-01-01", periods=3, freq="B")
        data = pd.DataFrame(
            {
                "underlying_symbol": "SPX",
                "quote_date": dates,
                "underlying_price": [100.0, 101.0, 102.0],
            }
        )
        assert not alma_cross_above()(data).any()
        assert not alma_cross_below()(data).any()

    def test_ma_crossovers_fire_on_rising_trend(self, cross_price_data):
        for fn in [
            dema_cross_above,
            tema_cross_above,
            hma_cross_above,
            wma_cross_above,
        ]:
            result = fn(fast=5, slow=20)(cross_price_data)
            assert result.any(), f"{fn.__name__} should fire on rising trend"
