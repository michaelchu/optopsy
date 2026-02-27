"""Volume-based signals: MFI, OBV, CMF, AD."""

import pandas as pd
import pandas_ta_classic as ta

from ._helpers import (
    SignalFunc,
    _get_close,
    _get_ohlc,
    _get_volume,
    _ohlcv_signal,
)

# ---------------------------------------------------------------------------
# MFI (Money Flow Index)
# ---------------------------------------------------------------------------


def mfi_above(period: int = 14, threshold: float = 80) -> SignalFunc:
    """True when MFI is above threshold (overbought / strong buying pressure)."""

    def _indicator(group: pd.DataFrame) -> "pd.Series | None":
        ohlc = _get_ohlc(group)
        if ohlc is None:
            return None
        high, low, close = ohlc
        volume = _get_volume(group)
        if volume is None:
            return None
        return ta.mfi(high, low, close, volume, length=period)

    return _ohlcv_signal(_indicator, lambda ind: ind > threshold)


def mfi_below(period: int = 14, threshold: float = 20) -> SignalFunc:
    """True when MFI is below threshold (oversold / strong selling pressure)."""

    def _indicator(group: pd.DataFrame) -> "pd.Series | None":
        ohlc = _get_ohlc(group)
        if ohlc is None:
            return None
        high, low, close = ohlc
        volume = _get_volume(group)
        if volume is None:
            return None
        return ta.mfi(high, low, close, volume, length=period)

    return _ohlcv_signal(_indicator, lambda ind: ind < threshold)


# ---------------------------------------------------------------------------
# OBV (On Balance Volume) crossover with SMA
# ---------------------------------------------------------------------------


def _obv_sma_lines(sma_period: int):
    """Compute (OBV, SMA_of_OBV) per symbol."""

    def _compute(
        group: pd.DataFrame,
    ) -> tuple["pd.Series | None", "pd.Series | None"]:
        close = _get_close(group)
        if close is None:
            return None, None
        volume = _get_volume(group)
        if volume is None:
            return None, None
        obv = ta.obv(close, volume)
        if obv is None:
            return None, None
        obv_sma = ta.sma(obv, length=sma_period)
        if obv_sma is None:
            return None, None
        return obv, obv_sma

    return _compute


def obv_cross_above_sma(sma_period: int = 20) -> SignalFunc:
    """True when OBV crosses above its SMA (bullish volume trend)."""

    from ._helpers import _ohlcv_crossover_signal

    return _ohlcv_crossover_signal(_obv_sma_lines(sma_period), above=True)


def obv_cross_below_sma(sma_period: int = 20) -> SignalFunc:
    """True when OBV crosses below its SMA (bearish volume trend)."""
    from ._helpers import _ohlcv_crossover_signal

    return _ohlcv_crossover_signal(_obv_sma_lines(sma_period), above=False)


# ---------------------------------------------------------------------------
# CMF (Chaikin Money Flow)
# ---------------------------------------------------------------------------


def cmf_above(period: int = 20, threshold: float = 0.05) -> SignalFunc:
    """True when CMF is above threshold (buying pressure)."""

    def _indicator(group: pd.DataFrame) -> "pd.Series | None":
        ohlc = _get_ohlc(group)
        if ohlc is None:
            return None
        high, low, close = ohlc
        volume = _get_volume(group)
        if volume is None:
            return None
        return ta.cmf(high, low, close, volume, length=period)

    return _ohlcv_signal(_indicator, lambda ind: ind > threshold)


def cmf_below(period: int = 20, threshold: float = -0.05) -> SignalFunc:
    """True when CMF is below threshold (selling pressure)."""

    def _indicator(group: pd.DataFrame) -> "pd.Series | None":
        ohlc = _get_ohlc(group)
        if ohlc is None:
            return None
        high, low, close = ohlc
        volume = _get_volume(group)
        if volume is None:
            return None
        return ta.cmf(high, low, close, volume, length=period)

    return _ohlcv_signal(_indicator, lambda ind: ind < threshold)


# ---------------------------------------------------------------------------
# AD (Accumulation/Distribution) crossover with SMA
# ---------------------------------------------------------------------------


def _ad_sma_lines(sma_period: int):
    """Compute (AD, SMA_of_AD) per symbol."""

    def _compute(
        group: pd.DataFrame,
    ) -> tuple["pd.Series | None", "pd.Series | None"]:
        ohlc = _get_ohlc(group)
        if ohlc is None:
            return None, None
        high, low, close = ohlc
        volume = _get_volume(group)
        if volume is None:
            return None, None
        ad = ta.ad(high, low, close, volume)
        if ad is None:
            return None, None
        ad_sma = ta.sma(ad, length=sma_period)
        if ad_sma is None:
            return None, None
        return ad, ad_sma

    return _compute


def ad_cross_above_sma(sma_period: int = 20) -> SignalFunc:
    """True when A/D line crosses above its SMA (bullish accumulation)."""
    from ._helpers import _ohlcv_crossover_signal

    return _ohlcv_crossover_signal(_ad_sma_lines(sma_period), above=True)


def ad_cross_below_sma(sma_period: int = 20) -> SignalFunc:
    """True when A/D line crosses below its SMA (bearish distribution)."""
    from ._helpers import _ohlcv_crossover_signal

    return _ohlcv_crossover_signal(_ad_sma_lines(sma_period), above=False)
