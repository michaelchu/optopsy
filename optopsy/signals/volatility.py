"""Volatility signals: ATR, Bollinger Bands, Keltner Channel, Donchian, NATR, Mass Index."""

import operator

import pandas as pd
import pandas_ta_classic as ta

from ._helpers import (
    SignalFunc,
    _band_signal,
    _get_close,
    _get_high,
    _get_low,
    _groupby_symbol,
    _ohlcv_signal,
)

# ---------------------------------------------------------------------------
# ATR (Average True Range) volatility regime
# ---------------------------------------------------------------------------


def _compute_atr(
    close: pd.Series,
    period: int,
    high: pd.Series | None = None,
    low: pd.Series | None = None,
) -> pd.Series:
    """Compute ATR using real OHLC when available, or close-only proxy."""
    hi = high if high is not None else close
    lo = low if low is not None else close
    result = ta.atr(high=hi, low=lo, close=close, length=period)
    if result is None:
        return pd.Series(float("nan"), index=close.index)
    return result


def _atr_signal(period: int, multiplier: float, above: bool) -> SignalFunc:
    """Shared ATR regime signal logic."""
    period = int(period)
    cmp = operator.gt if above else operator.lt

    def _signal(data: pd.DataFrame) -> "pd.Series[bool]":
        has_ohlcv = "high" in data.columns and "low" in data.columns

        def _compute_group(group: pd.DataFrame) -> "pd.Series[bool]":
            prices = _get_close(group)
            if prices is None:
                return pd.Series(False, index=group.index)
            high = group["high"] if has_ohlcv else None
            low = group["low"] if has_ohlcv else None
            atr = _compute_atr(prices, period, high=high, low=low)
            median_atr = atr.median()
            if pd.isna(median_atr):
                return pd.Series(False, index=group.index)
            return cmp(atr, multiplier * median_atr).fillna(False)

        return _groupby_symbol(data, _compute_group)

    return _signal


def atr_above(period: int = 14, multiplier: float = 1.0) -> SignalFunc:
    """True when ATR exceeds ``multiplier`` times the full-history median ATR."""
    return _atr_signal(period, multiplier, above=True)


def atr_below(period: int = 14, multiplier: float = 1.0) -> SignalFunc:
    """True when ATR is below ``multiplier`` times the full-history median ATR."""
    return _atr_signal(period, multiplier, above=False)


# ---------------------------------------------------------------------------
# Bollinger Bands
# ---------------------------------------------------------------------------


def _bb_signal(length: int, std: float, above: bool) -> SignalFunc:
    """Shared Bollinger Band signal logic."""
    length, std = int(length), float(std)
    if above:
        band_col = f"BBU_{length}_{std}"
        fill_val = float("inf")
        cmp = operator.gt
    else:
        band_col = f"BBL_{length}_{std}"
        fill_val = float("-inf")
        cmp = operator.lt

    def _signal(data: pd.DataFrame) -> "pd.Series[bool]":
        def _compute_group(group: pd.DataFrame) -> "pd.Series[bool]":
            prices = _get_close(group)
            if prices is None:
                return pd.Series(False, index=group.index)
            bb = ta.bbands(prices, length=length, std=std)
            if bb is None:
                return pd.Series(False, index=group.index)
            band = bb[band_col].fillna(fill_val)
            return cmp(prices, band).fillna(False)

        return _groupby_symbol(data, _compute_group)

    return _signal


def bb_above_upper(length: int = 20, std: float = 2.0) -> SignalFunc:
    """True when the underlying price is above the upper Bollinger Band."""
    return _bb_signal(length, std, above=True)


def bb_below_lower(length: int = 20, std: float = 2.0) -> SignalFunc:
    """True when the underlying price is below the lower Bollinger Band."""
    return _bb_signal(length, std, above=False)


# ---------------------------------------------------------------------------
# Keltner Channel
# ---------------------------------------------------------------------------


def _kc_bands(length: int, scalar: float):
    def _compute(group: pd.DataFrame) -> tuple["pd.Series | None", "pd.Series | None"]:
        high, low, close = _get_high(group), _get_low(group), _get_close(group)
        if close is None:
            return None, None
        result = ta.kc(high, low, close, length=length, scalar=scalar)
        if result is None:
            return None, None
        upper = lower = None
        for col in result.columns:
            if col.startswith("KCU"):
                upper = result[col]
            elif col.startswith("KCL"):
                lower = result[col]
        return upper, lower

    return _compute


def kc_above_upper(length: int = 20, scalar: float = 1.5) -> SignalFunc:
    """True when price is above the upper Keltner Channel."""
    return _band_signal(_kc_bands(length, scalar), above=True)


def kc_below_lower(length: int = 20, scalar: float = 1.5) -> SignalFunc:
    """True when price is below the lower Keltner Channel."""
    return _band_signal(_kc_bands(length, scalar), above=False)


# ---------------------------------------------------------------------------
# Donchian Channel
# ---------------------------------------------------------------------------


def _donchian_bands(lower_length: int, upper_length: int):
    def _compute(group: pd.DataFrame) -> tuple["pd.Series | None", "pd.Series | None"]:
        high, low = _get_high(group), _get_low(group)
        if high is None or low is None:
            return None, None
        result = ta.donchian(
            high, low, lower_length=lower_length, upper_length=upper_length
        )
        if result is None:
            return None, None
        upper = lower = None
        for col in result.columns:
            if col.startswith("DCU"):
                upper = result[col]
            elif col.startswith("DCL"):
                lower = result[col]
        return upper, lower

    return _compute


def donchian_above_upper(lower_length: int = 20, upper_length: int = 20) -> SignalFunc:
    """True when price is above the upper Donchian Channel (breakout)."""
    return _band_signal(_donchian_bands(lower_length, upper_length), above=True)


def donchian_below_lower(lower_length: int = 20, upper_length: int = 20) -> SignalFunc:
    """True when price is below the lower Donchian Channel (breakdown)."""
    return _band_signal(_donchian_bands(lower_length, upper_length), above=False)


# ---------------------------------------------------------------------------
# NATR (Normalized Average True Range)
# ---------------------------------------------------------------------------


def natr_above(period: int = 14, threshold: float = 2.0) -> SignalFunc:
    """True when NATR is above threshold (high volatility as % of price)."""

    def _indicator(group: pd.DataFrame) -> "pd.Series | None":
        high, low, close = _get_high(group), _get_low(group), _get_close(group)
        if close is None:
            return None
        return ta.natr(high, low, close, length=period)

    return _ohlcv_signal(_indicator, lambda ind: ind > threshold)


def natr_below(period: int = 14, threshold: float = 1.0) -> SignalFunc:
    """True when NATR is below threshold (low volatility as % of price)."""

    def _indicator(group: pd.DataFrame) -> "pd.Series | None":
        high, low, close = _get_high(group), _get_low(group), _get_close(group)
        if close is None:
            return None
        return ta.natr(high, low, close, length=period)

    return _ohlcv_signal(_indicator, lambda ind: ind < threshold)


# ---------------------------------------------------------------------------
# Mass Index
# ---------------------------------------------------------------------------


def massi_above(fast: int = 9, slow: int = 25, threshold: float = 27) -> SignalFunc:
    """True when Mass Index is above threshold (potential reversal)."""

    def _indicator(group: pd.DataFrame) -> "pd.Series | None":
        high, low = _get_high(group), _get_low(group)
        if high is None or low is None:
            return None
        return ta.massi(high, low, fast=fast, slow=slow)

    return _ohlcv_signal(_indicator, lambda ind: ind > threshold)


def massi_below(fast: int = 9, slow: int = 25, threshold: float = 26.5) -> SignalFunc:
    """True when Mass Index is below threshold."""

    def _indicator(group: pd.DataFrame) -> "pd.Series | None":
        high, low = _get_high(group), _get_low(group)
        if high is None or low is None:
            return None
        return ta.massi(high, low, fast=fast, slow=slow)

    return _ohlcv_signal(_indicator, lambda ind: ind < threshold)
