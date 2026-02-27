"""Trend signals: ADX, Aroon, Supertrend, PSAR, Choppiness, VHF."""

import pandas as pd
import pandas_ta_classic as ta

from ._helpers import (
    SignalFunc,
    _direction_signal,
    _get_close,
    _get_high,
    _get_low,
    _ohlcv_crossover_signal,
    _ohlcv_signal,
)

# ---------------------------------------------------------------------------
# ADX (Average Directional Index)
# ---------------------------------------------------------------------------


def adx_above(period: int = 14, threshold: float = 25) -> SignalFunc:
    """True when ADX is above threshold (strong trend regardless of direction)."""

    def _indicator(group: pd.DataFrame) -> "pd.Series | None":
        high, low, close = _get_high(group), _get_low(group), _get_close(group)
        if close is None:
            return None
        result = ta.adx(high, low, close, length=period)
        if result is None:
            return None
        col = f"ADX_{period}"
        if col not in result.columns:
            for c in result.columns:
                if c.startswith("ADX_"):
                    return result[c]
            return None
        return result[col]

    return _ohlcv_signal(_indicator, lambda ind: ind > threshold)


def adx_below(period: int = 14, threshold: float = 20) -> SignalFunc:
    """True when ADX is below threshold (weak/no trend, range-bound)."""

    def _indicator(group: pd.DataFrame) -> "pd.Series | None":
        high, low, close = _get_high(group), _get_low(group), _get_close(group)
        if close is None:
            return None
        result = ta.adx(high, low, close, length=period)
        if result is None:
            return None
        col = f"ADX_{period}"
        if col not in result.columns:
            for c in result.columns:
                if c.startswith("ADX_"):
                    return result[c]
            return None
        return result[col]

    return _ohlcv_signal(_indicator, lambda ind: ind < threshold)


# ---------------------------------------------------------------------------
# Aroon crossover
# ---------------------------------------------------------------------------


def _aroon_lines(
    period: int,
):
    def _compute(
        group: pd.DataFrame,
    ) -> tuple["pd.Series | None", "pd.Series | None"]:
        high, low = _get_high(group), _get_low(group)
        if high is None or low is None:
            return None, None
        result = ta.aroon(high, low, length=period)
        if result is None:
            return None, None
        up = dn = None
        for col in result.columns:
            if col.startswith("AROONU"):
                up = result[col]
            elif col.startswith("AROOND"):
                dn = result[col]
        return up, dn

    return _compute


def aroon_cross_above(period: int = 25) -> SignalFunc:
    """True when Aroon Up crosses above Aroon Down (bullish trend)."""
    return _ohlcv_crossover_signal(_aroon_lines(period), above=True)


def aroon_cross_below(period: int = 25) -> SignalFunc:
    """True when Aroon Up crosses below Aroon Down (bearish trend)."""
    return _ohlcv_crossover_signal(_aroon_lines(period), above=False)


# ---------------------------------------------------------------------------
# Supertrend
# ---------------------------------------------------------------------------


def _supertrend_direction(period: int, multiplier: float):
    def _compute(group: pd.DataFrame) -> "pd.Series | None":
        high, low, close = _get_high(group), _get_low(group), _get_close(group)
        if close is None:
            return None
        result = ta.supertrend(high, low, close, length=period, multiplier=multiplier)
        if result is None:
            return None
        # Direction column: SUPERTd_{period}_{multiplier}
        for col in result.columns:
            if col.startswith("SUPERTd"):
                return result[col]
        return None

    return _compute


def supertrend_buy(period: int = 7, multiplier: float = 3.0) -> SignalFunc:
    """True when Supertrend flips to bullish (direction changes to 1)."""
    return _direction_signal(_supertrend_direction(period, multiplier), buy=True)


def supertrend_sell(period: int = 7, multiplier: float = 3.0) -> SignalFunc:
    """True when Supertrend flips to bearish (direction changes to -1)."""
    return _direction_signal(_supertrend_direction(period, multiplier), buy=False)


# ---------------------------------------------------------------------------
# Parabolic SAR
# ---------------------------------------------------------------------------


def _psar_direction(af0: float, af: float, max_af: float):
    def _compute(group: pd.DataFrame) -> "pd.Series | None":
        high, low, close = _get_high(group), _get_low(group), _get_close(group)
        if close is None:
            return None
        result = ta.psar(high, low, close, af0=af0, af=af, max_af=max_af)
        if result is None:
            return None
        # PSAR has PSARl (long) and PSARs (short) columns
        # When PSARl is not NaN, trend is bullish (1); when PSARs is not NaN, bearish (-1)
        psar_long = psar_short = None
        for col in result.columns:
            if col.startswith("PSARl"):
                psar_long = result[col]
            elif col.startswith("PSARs"):
                psar_short = result[col]
        if psar_long is None and psar_short is None:
            return None
        # Build direction: 1 when long SAR is active, -1 when short SAR is active
        direction = pd.Series(0, index=group.index, dtype=int)
        if psar_long is not None:
            direction = direction.where(psar_long.isna(), 1)
        if psar_short is not None:
            direction = direction.where(psar_short.isna(), -1)
        return direction

    return _compute


def psar_buy(af0: float = 0.02, af: float = 0.02, max_af: float = 0.2) -> SignalFunc:
    """True when PSAR flips to bullish (long SAR appears)."""
    return _direction_signal(_psar_direction(af0, af, max_af), buy=True)


def psar_sell(af0: float = 0.02, af: float = 0.02, max_af: float = 0.2) -> SignalFunc:
    """True when PSAR flips to bearish (short SAR appears)."""
    return _direction_signal(_psar_direction(af0, af, max_af), buy=False)


# ---------------------------------------------------------------------------
# Choppiness Index
# ---------------------------------------------------------------------------


def chop_above(period: int = 14, threshold: float = 61.8) -> SignalFunc:
    """True when Choppiness Index is above threshold (choppy / range-bound)."""

    def _indicator(group: pd.DataFrame) -> "pd.Series | None":
        high, low, close = _get_high(group), _get_low(group), _get_close(group)
        if close is None:
            return None
        return ta.chop(high, low, close, length=period)

    return _ohlcv_signal(_indicator, lambda ind: ind > threshold)


def chop_below(period: int = 14, threshold: float = 38.2) -> SignalFunc:
    """True when Choppiness Index is below threshold (trending)."""

    def _indicator(group: pd.DataFrame) -> "pd.Series | None":
        high, low, close = _get_high(group), _get_low(group), _get_close(group)
        if close is None:
            return None
        return ta.chop(high, low, close, length=period)

    return _ohlcv_signal(_indicator, lambda ind: ind < threshold)


# ---------------------------------------------------------------------------
# VHF (Vertical Horizontal Filter)
# ---------------------------------------------------------------------------


def vhf_above(period: int = 28, threshold: float = 0.4) -> SignalFunc:
    """True when VHF is above threshold (trending market)."""

    def _indicator(group: pd.DataFrame) -> "pd.Series | None":
        close = _get_close(group)
        if close is None:
            return None
        return ta.vhf(close, length=period)

    return _ohlcv_signal(_indicator, lambda ind: ind > threshold)


def vhf_below(period: int = 28, threshold: float = 0.4) -> SignalFunc:
    """True when VHF is below threshold (ranging market)."""

    def _indicator(group: pd.DataFrame) -> "pd.Series | None":
        close = _get_close(group)
        if close is None:
            return None
        return ta.vhf(close, length=period)

    return _ohlcv_signal(_indicator, lambda ind: ind < threshold)
