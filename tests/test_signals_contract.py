"""Parametrized contract tests for all signal functions.

Validates the universal signal contract (bool series, length match,
insufficient data, mutual exclusivity) for all signals via
``@pytest.mark.parametrize``, replacing duplicated boilerplate tests
across test_signals_trend.py, test_signals_volatility.py, etc.
"""

import pandas as pd
import pytest

from optopsy.signals import (
    # Volume
    ad_cross_above_sma,
    ad_cross_below_sma,
    # Trend
    adx_above,
    adx_below,
    # Overlap
    alma_cross_above,
    alma_cross_below,
    # Momentum
    ao_above,
    ao_below,
    aroon_cross_above,
    aroon_cross_below,
    # Volatility
    atr_above,
    atr_below,
    bb_above_upper,
    bb_below_lower,
    cci_above,
    cci_below,
    chop_above,
    chop_below,
    cmf_above,
    cmf_below,
    cmo_above,
    cmo_below,
    dema_cross_above,
    dema_cross_below,
    donchian_above_upper,
    donchian_below_lower,
    ema_cross_above,
    ema_cross_below,
    fisher_cross_above,
    fisher_cross_below,
    hma_cross_above,
    hma_cross_below,
    kama_cross_above,
    kama_cross_below,
    kc_above_upper,
    kc_below_lower,
    kst_cross_above,
    kst_cross_below,
    macd_cross_above,
    macd_cross_below,
    massi_above,
    massi_below,
    mfi_above,
    mfi_below,
    natr_above,
    natr_below,
    obv_cross_above_sma,
    obv_cross_below_sma,
    ppo_cross_above,
    ppo_cross_below,
    psar_buy,
    psar_sell,
    roc_above,
    roc_below,
    rsi_above,
    rsi_below,
    sma_above,
    sma_below,
    smi_cross_above,
    smi_cross_below,
    squeeze_off,
    squeeze_on,
    stoch_above,
    stoch_below,
    stochrsi_above,
    stochrsi_below,
    supertrend_buy,
    supertrend_sell,
    tema_cross_above,
    tema_cross_below,
    tsi_cross_above,
    tsi_cross_below,
    uo_above,
    uo_below,
    vhf_above,
    vhf_below,
    willr_above,
    willr_below,
    wma_cross_above,
    wma_cross_below,
    zlma_cross_above,
    zlma_cross_below,
)


def _make_insufficient_data(periods=3):
    """Create a small DataFrame for testing insufficient-data behaviour."""
    dates = pd.date_range("2018-01-01", periods=periods, freq="B")
    return pd.DataFrame(
        {
            "underlying_symbol": "SPX",
            "quote_date": dates,
            "underlying_price": [100.0 + i for i in range(periods)],
        }
    )


# ============================================================================
# Signal registry: (signal_factory, fixture_name)
#
# Each entry creates a zero-arg signal via the factory (e.g. adx_above())
# and names the conftest fixture that provides appropriate test data.
# ============================================================================

_SIGNALS_WITH_FIXTURE = [
    # --- Trend ---
    (adx_above, "ohlcv_60bars"),
    (adx_below, "ohlcv_60bars"),
    (aroon_cross_above, "ohlcv_60bars"),
    (aroon_cross_below, "ohlcv_60bars"),
    (supertrend_buy, "ohlcv_60bars"),
    (supertrend_sell, "ohlcv_60bars"),
    (psar_buy, "ohlcv_60bars"),
    (psar_sell, "ohlcv_60bars"),
    (chop_above, "ohlcv_60bars"),
    (chop_below, "ohlcv_60bars"),
    (vhf_above, "price_data_100bars"),
    (vhf_below, "price_data_100bars"),
    # --- Volatility ---
    (bb_above_upper, "ohlcv_60bars"),
    (bb_below_lower, "ohlcv_60bars"),
    (atr_above, "ohlcv_60bars"),
    (atr_below, "ohlcv_60bars"),
    (kc_above_upper, "ohlcv_60bars"),
    (kc_below_lower, "ohlcv_60bars"),
    (donchian_above_upper, "ohlcv_60bars"),
    (donchian_below_lower, "ohlcv_60bars"),
    (natr_above, "ohlcv_60bars"),
    (natr_below, "ohlcv_60bars"),
    (massi_above, "ohlcv_60bars"),
    (massi_below, "ohlcv_60bars"),
    # --- Momentum ---
    (macd_cross_above, "price_data_100bars"),
    (macd_cross_below, "price_data_100bars"),
    (stoch_above, "ohlcv_60bars"),
    (stoch_below, "ohlcv_60bars"),
    (stochrsi_above, "price_data_100bars"),
    (stochrsi_below, "price_data_100bars"),
    (willr_above, "ohlcv_60bars"),
    (willr_below, "ohlcv_60bars"),
    (cci_above, "ohlcv_60bars"),
    (cci_below, "ohlcv_60bars"),
    (roc_above, "price_data_100bars"),
    (roc_below, "price_data_100bars"),
    (ppo_cross_above, "price_data_100bars"),
    (ppo_cross_below, "price_data_100bars"),
    (tsi_cross_above, "price_data_100bars"),
    (tsi_cross_below, "price_data_100bars"),
    (cmo_above, "price_data_100bars"),
    (cmo_below, "price_data_100bars"),
    (uo_above, "ohlcv_60bars"),
    (uo_below, "ohlcv_60bars"),
    (squeeze_on, "ohlcv_60bars"),
    (squeeze_off, "ohlcv_60bars"),
    (ao_above, "ohlcv_60bars"),
    (ao_below, "ohlcv_60bars"),
    (smi_cross_above, "price_data_100bars"),
    (smi_cross_below, "price_data_100bars"),
    (kst_cross_above, "price_data_100bars"),
    (kst_cross_below, "price_data_100bars"),
    (fisher_cross_above, "price_data_100bars"),
    (fisher_cross_below, "price_data_100bars"),
    (rsi_above, "price_data_100bars"),
    (rsi_below, "price_data_100bars"),
    # --- Overlap ---
    (sma_above, "price_data_100bars"),
    (sma_below, "price_data_100bars"),
    (ema_cross_above, "cross_price_data"),
    (ema_cross_below, "cross_price_data"),
    (dema_cross_above, "cross_price_data"),
    (dema_cross_below, "cross_price_data"),
    (tema_cross_above, "cross_price_data"),
    (tema_cross_below, "cross_price_data"),
    (hma_cross_above, "cross_price_data"),
    (hma_cross_below, "cross_price_data"),
    (kama_cross_above, "cross_price_data"),
    (kama_cross_below, "cross_price_data"),
    (wma_cross_above, "cross_price_data"),
    (wma_cross_below, "cross_price_data"),
    (zlma_cross_above, "cross_price_data"),
    (zlma_cross_below, "cross_price_data"),
    (alma_cross_above, "cross_price_data"),
    (alma_cross_below, "cross_price_data"),
    # --- Volume ---
    (mfi_above, "ohlcv_with_volume_60bars"),
    (mfi_below, "ohlcv_with_volume_60bars"),
    (obv_cross_above_sma, "ohlcv_with_volume_60bars"),
    (obv_cross_below_sma, "ohlcv_with_volume_60bars"),
    (cmf_above, "ohlcv_with_volume_60bars"),
    (cmf_below, "ohlcv_with_volume_60bars"),
    (ad_cross_above_sma, "ohlcv_with_volume_60bars"),
    (ad_cross_below_sma, "ohlcv_with_volume_60bars"),
]

_IDS = [fn.__name__ for fn, _ in _SIGNALS_WITH_FIXTURE]


# ============================================================================
# Contract: returns bool Series
# ============================================================================


@pytest.mark.parametrize("signal_fn,fixture_name", _SIGNALS_WITH_FIXTURE, ids=_IDS)
def test_signal_returns_bool_series(signal_fn, fixture_name, request):
    data = request.getfixturevalue(fixture_name)
    result = signal_fn()(data)
    assert isinstance(result, pd.Series) and result.dtype == bool


# ============================================================================
# Contract: output length matches input
# ============================================================================


@pytest.mark.parametrize("signal_fn,fixture_name", _SIGNALS_WITH_FIXTURE, ids=_IDS)
def test_signal_length_matches_input(signal_fn, fixture_name, request):
    data = request.getfixturevalue(fixture_name)
    assert len(signal_fn()(data)) == len(data)


# ============================================================================
# Contract: insufficient data returns all False
# ============================================================================

# Signals that need fewer than 3 bars to be tested as "insufficient"
_INSUF_PERIODS_OVERRIDE = {
    psar_buy: 1,
    psar_sell: 1,
}

_INSUFFICIENT_DATA_SIGNALS = [
    (fn, _INSUF_PERIODS_OVERRIDE.get(fn, 3)) for fn, _ in _SIGNALS_WITH_FIXTURE
]

_INSUF_IDS = [fn.__name__ for fn, _ in _INSUFFICIENT_DATA_SIGNALS]


@pytest.mark.parametrize(
    "signal_fn,min_periods", _INSUFFICIENT_DATA_SIGNALS, ids=_INSUF_IDS
)
def test_signal_insufficient_data_returns_all_false(signal_fn, min_periods):
    data = _make_insufficient_data(min_periods)
    assert not signal_fn()(data).any()


# ============================================================================
# Contract: paired above/below signals are mutually exclusive
# ============================================================================

_EXCLUSIVE_PAIRS = [
    # Trend
    (adx_above, adx_below, "ohlcv_60bars"),
    (aroon_cross_above, aroon_cross_below, "ohlcv_100bars"),
    (supertrend_buy, supertrend_sell, "ohlcv_100bars"),
    (psar_buy, psar_sell, "ohlcv_100bars"),
    (chop_above, chop_below, "ohlcv_60bars"),
    (vhf_above, vhf_below, "price_data_100bars"),
    # Volatility
    (bb_above_upper, bb_below_lower, "ohlcv_60bars"),
    (kc_above_upper, kc_below_lower, "ohlcv_60bars"),
    (donchian_above_upper, donchian_below_lower, "ohlcv_60bars"),
    (natr_above, natr_below, "ohlcv_60bars"),
    # Momentum
    (macd_cross_above, macd_cross_below, "price_data_100bars"),
    (stoch_above, stoch_below, "ohlcv_60bars"),
    (willr_above, willr_below, "ohlcv_60bars"),
    (cci_above, cci_below, "ohlcv_60bars"),
    (ppo_cross_above, ppo_cross_below, "price_data_100bars"),
    (tsi_cross_above, tsi_cross_below, "price_data_100bars"),
    (cmo_above, cmo_below, "price_data_100bars"),
    (uo_above, uo_below, "ohlcv_60bars"),
    (smi_cross_above, smi_cross_below, "price_data_100bars"),
    (kst_cross_above, kst_cross_below, "price_data_100bars"),
    (fisher_cross_above, fisher_cross_below, "price_data_100bars"),
    # Overlap
    (sma_above, sma_below, "price_data_100bars"),
    (ema_cross_above, ema_cross_below, "cross_price_data"),
    (dema_cross_above, dema_cross_below, "cross_price_data"),
    # Volume
    (mfi_above, mfi_below, "ohlcv_with_volume_60bars"),
    (obv_cross_above_sma, obv_cross_below_sma, "ohlcv_with_volume_100bars"),
    (ad_cross_above_sma, ad_cross_below_sma, "ohlcv_with_volume_100bars"),
]

_PAIR_IDS = [f"{a.__name__}_vs_{b.__name__}" for a, b, _ in _EXCLUSIVE_PAIRS]


@pytest.mark.parametrize(
    "above_fn,below_fn,fixture_name", _EXCLUSIVE_PAIRS, ids=_PAIR_IDS
)
def test_signals_mutually_exclusive(above_fn, below_fn, fixture_name, request):
    data = request.getfixturevalue(fixture_name)
    assert not (above_fn()(data) & below_fn()(data)).any()
