"""Strategy, signal, and tool schema registries.

This module is the single source of truth for:

- ``STRATEGIES`` — maps strategy name to ``(function, description, is_calendar)``
- ``SIGNAL_REGISTRY`` — maps signal name to a factory lambda returning a ``SignalFunc``
- ``STRATEGY_OPTION_TYPE`` — maps strategy name to required option type for data fetching
- ``get_tool_schemas()`` — generates OpenAI-compatible function schemas from Pydantic models
"""

import logging
from typing import Any

import optopsy as op
import optopsy.signals as _signals
from optopsy.plugins import get_plugin_signals, get_plugin_strategies, get_plugin_tools

from ..providers import get_all_provider_tool_schemas

_log = logging.getLogger(__name__)

# Set of calendar-specific parameter names, used by _executor.py to filter
# non-calendar strategies.
CALENDAR_EXTRA_PARAMS = frozenset(
    {"front_dte_min", "front_dte_max", "back_dte_min", "back_dte_max"}
)

# Maps strategy name -> (function, description, is_calendar)
STRATEGIES = {
    "long_calls": (op.long_calls, "Buy calls — bullish directional bet", False),
    "long_puts": (op.long_puts, "Buy puts — bearish directional bet", False),
    "short_calls": (op.short_calls, "Sell calls — bearish/neutral income", False),
    "short_puts": (op.short_puts, "Sell puts — bullish/neutral income", False),
    "long_straddles": (
        op.long_straddles,
        "Buy call + put at same strike — bet on large move in either direction",
        False,
    ),
    "short_straddles": (
        op.short_straddles,
        "Sell call + put at same strike — bet on low volatility",
        False,
    ),
    "long_strangles": (
        op.long_strangles,
        "Buy call + put at different strikes — cheaper volatility bet",
        False,
    ),
    "short_strangles": (
        op.short_strangles,
        "Sell call + put at different strikes — wider neutral income",
        False,
    ),
    "long_call_spread": (
        op.long_call_spread,
        "Bull call spread — capped-risk bullish trade",
        False,
    ),
    "short_call_spread": (
        op.short_call_spread,
        "Bear call spread — bearish credit spread",
        False,
    ),
    "long_put_spread": (
        op.long_put_spread,
        "Bear put spread — capped-risk bearish trade",
        False,
    ),
    "short_put_spread": (
        op.short_put_spread,
        "Bull put spread — bullish credit spread",
        False,
    ),
    "long_call_butterfly": (
        op.long_call_butterfly,
        "Long call butterfly — neutral, profits near middle strike",
        False,
    ),
    "short_call_butterfly": (
        op.short_call_butterfly,
        "Short call butterfly — profits from large move",
        False,
    ),
    "long_put_butterfly": (
        op.long_put_butterfly,
        "Long put butterfly — neutral, profits near middle strike",
        False,
    ),
    "short_put_butterfly": (
        op.short_put_butterfly,
        "Short put butterfly — profits from large move",
        False,
    ),
    "iron_condor": (
        op.iron_condor,
        "Iron condor — neutral income, profits when underlying stays in range",
        False,
    ),
    "reverse_iron_condor": (
        op.reverse_iron_condor,
        "Reverse iron condor — profits from large move in either direction",
        False,
    ),
    "iron_butterfly": (
        op.iron_butterfly,
        "Iron butterfly — neutral income, narrower range than iron condor",
        False,
    ),
    "reverse_iron_butterfly": (
        op.reverse_iron_butterfly,
        "Reverse iron butterfly — profits from large move",
        False,
    ),
    "covered_call": (
        op.covered_call,
        "Covered call — long stock + short call for income",
        False,
    ),
    "protective_put": (
        op.protective_put,
        "Protective put — long stock + long put for downside protection",
        False,
    ),
    "collar": (
        op.collar,
        "Collar — long stock + short OTM call + long OTM put for hedged income",
        False,
    ),
    "cash_secured_put": (
        op.cash_secured_put,
        "Cash-secured put — sell put with cash reserve, bullish/neutral income",
        False,
    ),
    "call_back_spread": (
        op.call_back_spread,
        "Call back spread — short 1 ITM call + long 2 OTM calls, bullish ratio",
        False,
    ),
    "put_back_spread": (
        op.put_back_spread,
        "Put back spread — short 1 ITM put + long 2 OTM puts, bearish ratio",
        False,
    ),
    "call_front_spread": (
        op.call_front_spread,
        "Call front spread — long 1 ITM call + short 2 OTM calls, neutral ratio",
        False,
    ),
    "put_front_spread": (
        op.put_front_spread,
        "Put front spread — long 1 ITM put + short 2 OTM puts, neutral ratio",
        False,
    ),
    "long_call_condor": (
        op.long_call_condor,
        "Long call condor — buy wings, sell body with all calls, neutral",
        False,
    ),
    "short_call_condor": (
        op.short_call_condor,
        "Short call condor — sell wings, buy body with all calls, volatile",
        False,
    ),
    "long_put_condor": (
        op.long_put_condor,
        "Long put condor — buy wings, sell body with all puts, neutral",
        False,
    ),
    "short_put_condor": (
        op.short_put_condor,
        "Short put condor — sell wings, buy body with all puts, volatile",
        False,
    ),
    "long_call_calendar": (
        op.long_call_calendar,
        "Long call calendar — short front-month, long back-month call at same strike",
        True,
    ),
    "short_call_calendar": (
        op.short_call_calendar,
        "Short call calendar — long front-month, short back-month call at same strike",
        True,
    ),
    "long_put_calendar": (
        op.long_put_calendar,
        "Long put calendar — short front-month, long back-month put at same strike",
        True,
    ),
    "short_put_calendar": (
        op.short_put_calendar,
        "Short put calendar — long front-month, short back-month put at same strike",
        True,
    ),
    "long_call_diagonal": (
        op.long_call_diagonal,
        "Long call diagonal — short front-month, long back-month call at different strikes",
        True,
    ),
    "short_call_diagonal": (
        op.short_call_diagonal,
        "Short call diagonal — long front-month, short back-month call at different strikes",
        True,
    ),
    "long_put_diagonal": (
        op.long_put_diagonal,
        "Long put diagonal — short front-month, long back-month put at different strikes",
        True,
    ),
    "short_put_diagonal": (
        op.short_put_diagonal,
        "Short put diagonal — long front-month, short back-month put at different strikes",
        True,
    ),
}

# ---------------------------------------------------------------------------
# Signal registry
# ---------------------------------------------------------------------------
# Maps a flat string identifier -> factory lambda that returns a SignalFunc.
# Defaults are baked in so the LLM only needs to pick a name.
# Factories are called at execution time to avoid shared state between runs.


def _normalize_days_param(days):
    """
    Convert days parameter to list format.

    Args:
        days (int or list[int]): Day index or list of day indices (0=Monday, 6=Sunday).

    Returns:
        list[int]: Days parameter as a list.

    Raises:
        TypeError: If days is neither an int nor a list, or if list contains non-integers.
        ValueError: If days is an empty list or contains out-of-range values (not 0-6).
    """
    if isinstance(days, list):
        if not days:
            raise ValueError("days parameter cannot be an empty list")
        if not all(isinstance(day, int) for day in days):
            raise TypeError("all elements in days list must be integers")
        invalid_days = [d for d in days if d < 0 or d > 6]
        if invalid_days:
            raise ValueError(
                f"day values must be 0-6 (Monday-Sunday), got invalid values: {invalid_days}"
            )
        return days
    elif isinstance(days, int):
        if days < 0 or days > 6:
            raise ValueError(f"day value must be 0-6 (Monday-Sunday), got {days}")
        return [days]
    else:
        raise TypeError(
            f"days parameter must be an int or list[int], got {type(days).__name__}"
        )


SIGNAL_REGISTRY: dict[str, Any] = {
    # --- Momentum ---
    # RSI — defaults: period=14, threshold=30 (below) / 70 (above)
    "rsi_below": lambda **kw: _signals.rsi_below(
        kw.get("period", 14), kw.get("threshold", 30)
    ),
    "rsi_above": lambda **kw: _signals.rsi_above(
        kw.get("period", 14), kw.get("threshold", 70)
    ),
    # MACD — defaults: fast=12, slow=26, signal_period=9
    "macd_cross_above": lambda **kw: _signals.macd_cross_above(
        kw.get("fast", 12), kw.get("slow", 26), kw.get("signal_period", 9)
    ),
    "macd_cross_below": lambda **kw: _signals.macd_cross_below(
        kw.get("fast", 12), kw.get("slow", 26), kw.get("signal_period", 9)
    ),
    # Stochastic — defaults: k_period=14, d_period=3
    "stoch_below": lambda **kw: _signals.stoch_below(
        kw.get("k_period", 14), kw.get("d_period", 3), kw.get("threshold", 20)
    ),
    "stoch_above": lambda **kw: _signals.stoch_above(
        kw.get("k_period", 14), kw.get("d_period", 3), kw.get("threshold", 80)
    ),
    # StochRSI — defaults: period=14, rsi_period=14
    "stochrsi_below": lambda **kw: _signals.stochrsi_below(
        period=kw.get("period", 14),
        rsi_period=kw.get("rsi_period", 14),
        k_smooth=kw.get("k_smooth", 3),
        d_smooth=kw.get("d_smooth", 3),
        threshold=kw.get("threshold", 20),
    ),
    "stochrsi_above": lambda **kw: _signals.stochrsi_above(
        period=kw.get("period", 14),
        rsi_period=kw.get("rsi_period", 14),
        k_smooth=kw.get("k_smooth", 3),
        d_smooth=kw.get("d_smooth", 3),
        threshold=kw.get("threshold", 80),
    ),
    # Williams %R — defaults: period=14
    "willr_below": lambda **kw: _signals.willr_below(
        kw.get("period", 14), kw.get("threshold", -80)
    ),
    "willr_above": lambda **kw: _signals.willr_above(
        kw.get("period", 14), kw.get("threshold", -20)
    ),
    # CCI — defaults: period=20
    "cci_below": lambda **kw: _signals.cci_below(
        kw.get("period", 20), kw.get("threshold", -100)
    ),
    "cci_above": lambda **kw: _signals.cci_above(
        kw.get("period", 20), kw.get("threshold", 100)
    ),
    # ROC — defaults: period=10
    "roc_above": lambda **kw: _signals.roc_above(
        kw.get("period", 10), kw.get("threshold", 0)
    ),
    "roc_below": lambda **kw: _signals.roc_below(
        kw.get("period", 10), kw.get("threshold", 0)
    ),
    # PPO crossover — defaults: fast=12, slow=26, signal_period=9
    "ppo_cross_above": lambda **kw: _signals.ppo_cross_above(
        kw.get("fast", 12), kw.get("slow", 26), kw.get("signal_period", 9)
    ),
    "ppo_cross_below": lambda **kw: _signals.ppo_cross_below(
        kw.get("fast", 12), kw.get("slow", 26), kw.get("signal_period", 9)
    ),
    # TSI crossover — defaults: long=25, short=13, signal_period=13
    "tsi_cross_above": lambda **kw: _signals.tsi_cross_above(
        kw.get("long", 25), kw.get("short", 13), kw.get("signal_period", 13)
    ),
    "tsi_cross_below": lambda **kw: _signals.tsi_cross_below(
        kw.get("long", 25), kw.get("short", 13), kw.get("signal_period", 13)
    ),
    # CMO — defaults: period=14
    "cmo_above": lambda **kw: _signals.cmo_above(
        kw.get("period", 14), kw.get("threshold", 50)
    ),
    "cmo_below": lambda **kw: _signals.cmo_below(
        kw.get("period", 14), kw.get("threshold", -50)
    ),
    # UO — defaults: fast=7, medium=14, slow=28
    "uo_above": lambda **kw: _signals.uo_above(
        kw.get("fast", 7),
        kw.get("medium", 14),
        kw.get("slow", 28),
        kw.get("threshold", 70),
    ),
    "uo_below": lambda **kw: _signals.uo_below(
        kw.get("fast", 7),
        kw.get("medium", 14),
        kw.get("slow", 28),
        kw.get("threshold", 30),
    ),
    # Squeeze
    "squeeze_on": lambda **kw: _signals.squeeze_on(
        kw.get("bb_length", 20),
        kw.get("bb_std", 2.0),
        kw.get("kc_length", 20),
        kw.get("kc_scalar", 1.5),
    ),
    "squeeze_off": lambda **kw: _signals.squeeze_off(
        kw.get("bb_length", 20),
        kw.get("bb_std", 2.0),
        kw.get("kc_length", 20),
        kw.get("kc_scalar", 1.5),
    ),
    # Awesome Oscillator
    "ao_above": lambda **kw: _signals.ao_above(
        kw.get("fast", 5), kw.get("slow", 34), kw.get("threshold", 0)
    ),
    "ao_below": lambda **kw: _signals.ao_below(
        kw.get("fast", 5), kw.get("slow", 34), kw.get("threshold", 0)
    ),
    # SMI crossover
    "smi_cross_above": lambda **kw: _signals.smi_cross_above(
        kw.get("fast", 5), kw.get("slow", 20), kw.get("signal_period", 5)
    ),
    "smi_cross_below": lambda **kw: _signals.smi_cross_below(
        kw.get("fast", 5), kw.get("slow", 20), kw.get("signal_period", 5)
    ),
    # KST crossover
    "kst_cross_above": lambda **kw: _signals.kst_cross_above(),
    "kst_cross_below": lambda **kw: _signals.kst_cross_below(),
    # Fisher Transform crossover
    "fisher_cross_above": lambda **kw: _signals.fisher_cross_above(kw.get("period", 9)),
    "fisher_cross_below": lambda **kw: _signals.fisher_cross_below(kw.get("period", 9)),
    # --- Overlap / Moving Averages ---
    # SMA — default: period=50
    "sma_below": lambda **kw: _signals.sma_below(kw.get("period", 50)),
    "sma_above": lambda **kw: _signals.sma_above(kw.get("period", 50)),
    # EMA crossover — defaults: fast=10, slow=50
    "ema_cross_above": lambda **kw: _signals.ema_cross_above(
        kw.get("fast", 10), kw.get("slow", 50)
    ),
    "ema_cross_below": lambda **kw: _signals.ema_cross_below(
        kw.get("fast", 10), kw.get("slow", 50)
    ),
    # DEMA crossover
    "dema_cross_above": lambda **kw: _signals.dema_cross_above(
        kw.get("fast", 10), kw.get("slow", 50)
    ),
    "dema_cross_below": lambda **kw: _signals.dema_cross_below(
        kw.get("fast", 10), kw.get("slow", 50)
    ),
    # TEMA crossover
    "tema_cross_above": lambda **kw: _signals.tema_cross_above(
        kw.get("fast", 10), kw.get("slow", 50)
    ),
    "tema_cross_below": lambda **kw: _signals.tema_cross_below(
        kw.get("fast", 10), kw.get("slow", 50)
    ),
    # HMA crossover
    "hma_cross_above": lambda **kw: _signals.hma_cross_above(
        kw.get("fast", 10), kw.get("slow", 50)
    ),
    "hma_cross_below": lambda **kw: _signals.hma_cross_below(
        kw.get("fast", 10), kw.get("slow", 50)
    ),
    # KAMA crossover
    "kama_cross_above": lambda **kw: _signals.kama_cross_above(
        kw.get("fast", 10), kw.get("slow", 50)
    ),
    "kama_cross_below": lambda **kw: _signals.kama_cross_below(
        kw.get("fast", 10), kw.get("slow", 50)
    ),
    # WMA crossover
    "wma_cross_above": lambda **kw: _signals.wma_cross_above(
        kw.get("fast", 10), kw.get("slow", 50)
    ),
    "wma_cross_below": lambda **kw: _signals.wma_cross_below(
        kw.get("fast", 10), kw.get("slow", 50)
    ),
    # ZLMA crossover
    "zlma_cross_above": lambda **kw: _signals.zlma_cross_above(
        kw.get("fast", 10), kw.get("slow", 50)
    ),
    "zlma_cross_below": lambda **kw: _signals.zlma_cross_below(
        kw.get("fast", 10), kw.get("slow", 50)
    ),
    # ALMA crossover
    "alma_cross_above": lambda **kw: _signals.alma_cross_above(
        kw.get("fast", 10), kw.get("slow", 50)
    ),
    "alma_cross_below": lambda **kw: _signals.alma_cross_below(
        kw.get("fast", 10), kw.get("slow", 50)
    ),
    # --- Volatility ---
    # Bollinger Bands — defaults: length=20, std=2.0
    "bb_above_upper": lambda **kw: _signals.bb_above_upper(
        kw.get("length", 20), kw.get("std", 2.0)
    ),
    "bb_below_lower": lambda **kw: _signals.bb_below_lower(
        kw.get("length", 20), kw.get("std", 2.0)
    ),
    # ATR volatility regime — defaults: period=14, multiplier=1.5 (above) / 0.75 (below)
    "atr_above": lambda **kw: _signals.atr_above(
        kw.get("period", 14), kw.get("multiplier", 1.5)
    ),
    "atr_below": lambda **kw: _signals.atr_below(
        kw.get("period", 14), kw.get("multiplier", 0.75)
    ),
    # Keltner Channel
    "kc_above_upper": lambda **kw: _signals.kc_above_upper(
        kw.get("length", 20), kw.get("scalar", 1.5)
    ),
    "kc_below_lower": lambda **kw: _signals.kc_below_lower(
        kw.get("length", 20), kw.get("scalar", 1.5)
    ),
    # Donchian Channel
    "donchian_above_upper": lambda **kw: _signals.donchian_above_upper(
        kw.get("lower_length", 20), kw.get("upper_length", 20)
    ),
    "donchian_below_lower": lambda **kw: _signals.donchian_below_lower(
        kw.get("lower_length", 20), kw.get("upper_length", 20)
    ),
    # NATR
    "natr_above": lambda **kw: _signals.natr_above(
        kw.get("period", 14), kw.get("threshold", 2.0)
    ),
    "natr_below": lambda **kw: _signals.natr_below(
        kw.get("period", 14), kw.get("threshold", 1.0)
    ),
    # Mass Index
    "massi_above": lambda **kw: _signals.massi_above(
        kw.get("fast", 9), kw.get("slow", 25), kw.get("threshold", 27)
    ),
    "massi_below": lambda **kw: _signals.massi_below(
        kw.get("fast", 9), kw.get("slow", 25), kw.get("threshold", 26.5)
    ),
    # --- Trend ---
    # ADX
    "adx_above": lambda **kw: _signals.adx_above(
        kw.get("period", 14), kw.get("threshold", 25)
    ),
    "adx_below": lambda **kw: _signals.adx_below(
        kw.get("period", 14), kw.get("threshold", 20)
    ),
    # Aroon crossover
    "aroon_cross_above": lambda **kw: _signals.aroon_cross_above(kw.get("period", 25)),
    "aroon_cross_below": lambda **kw: _signals.aroon_cross_below(kw.get("period", 25)),
    # Supertrend
    "supertrend_buy": lambda **kw: _signals.supertrend_buy(
        kw.get("period", 7), kw.get("multiplier", 3.0)
    ),
    "supertrend_sell": lambda **kw: _signals.supertrend_sell(
        kw.get("period", 7), kw.get("multiplier", 3.0)
    ),
    # PSAR
    "psar_buy": lambda **kw: _signals.psar_buy(
        kw.get("af0", 0.02), kw.get("af", 0.02), kw.get("max_af", 0.2)
    ),
    "psar_sell": lambda **kw: _signals.psar_sell(
        kw.get("af0", 0.02), kw.get("af", 0.02), kw.get("max_af", 0.2)
    ),
    # Choppiness
    "chop_above": lambda **kw: _signals.chop_above(
        kw.get("period", 14), kw.get("threshold", 61.8)
    ),
    "chop_below": lambda **kw: _signals.chop_below(
        kw.get("period", 14), kw.get("threshold", 38.2)
    ),
    # VHF
    "vhf_above": lambda **kw: _signals.vhf_above(
        kw.get("period", 28), kw.get("threshold", 0.4)
    ),
    "vhf_below": lambda **kw: _signals.vhf_below(
        kw.get("period", 28), kw.get("threshold", 0.4)
    ),
    # --- Volume ---
    # MFI
    "mfi_above": lambda **kw: _signals.mfi_above(
        kw.get("period", 14), kw.get("threshold", 80)
    ),
    "mfi_below": lambda **kw: _signals.mfi_below(
        kw.get("period", 14), kw.get("threshold", 20)
    ),
    # OBV crossover with SMA
    "obv_cross_above_sma": lambda **kw: _signals.obv_cross_above_sma(
        kw.get("sma_period", 20)
    ),
    "obv_cross_below_sma": lambda **kw: _signals.obv_cross_below_sma(
        kw.get("sma_period", 20)
    ),
    # CMF
    "cmf_above": lambda **kw: _signals.cmf_above(
        kw.get("period", 20), kw.get("threshold", 0.05)
    ),
    "cmf_below": lambda **kw: _signals.cmf_below(
        kw.get("period", 20), kw.get("threshold", -0.05)
    ),
    # AD crossover with SMA
    "ad_cross_above_sma": lambda **kw: _signals.ad_cross_above_sma(
        kw.get("sma_period", 20)
    ),
    "ad_cross_below_sma": lambda **kw: _signals.ad_cross_below_sma(
        kw.get("sma_period", 20)
    ),
    # --- Calendar ---
    # Day-of-week — default: days=[4] (Friday); pass days=[0,1,2,3,4] for any weekday
    "day_of_week": lambda **kw: _signals.day_of_week(
        *_normalize_days_param(kw.get("days", [4]))
    ),
    # --- IV Rank ---
    # Require options data with implied_volatility column
    "iv_rank_above": lambda **kw: _signals.iv_rank_above(
        kw.get("threshold", 0.5), kw.get("window", 252)
    ),
    "iv_rank_below": lambda **kw: _signals.iv_rank_below(
        kw.get("threshold", 0.5), kw.get("window", 252)
    ),
}

# --- Plugin signals ---
for _sig_name, _factory in get_plugin_signals().items():
    if _sig_name in SIGNAL_REGISTRY:
        _log.warning("Plugin overrides built-in signal: %s", _sig_name)
    SIGNAL_REGISTRY[_sig_name] = _factory

SIGNAL_NAMES = sorted(SIGNAL_REGISTRY.keys())

# Signals that only need quote_date (no OHLCV data / yfinance fetch).
_DATE_ONLY_SIGNALS = frozenset({"day_of_week"})

# Signals that require options data (with implied_volatility column)
# rather than stock OHLCV data.
_IV_SIGNALS = frozenset({"iv_rank_above", "iv_rank_below"})

# Signals that require OHLC data (high, low, close) — need stock data fetch.
_OHLC_SIGNALS = frozenset(
    {
        "stoch_below",
        "stoch_above",
        "willr_below",
        "willr_above",
        "cci_below",
        "cci_above",
        "uo_above",
        "uo_below",
        "squeeze_on",
        "squeeze_off",
        "ao_above",
        "ao_below",
        "kc_above_upper",
        "kc_below_lower",
        "donchian_above_upper",
        "donchian_below_lower",
        "natr_above",
        "natr_below",
        "massi_above",
        "massi_below",
        "adx_above",
        "adx_below",
        "aroon_cross_above",
        "aroon_cross_below",
        "supertrend_buy",
        "supertrend_sell",
        "psar_buy",
        "psar_sell",
        "chop_above",
        "chop_below",
    }
)

# Signals that require OHLCV data (high, low, close, volume).
_VOLUME_SIGNALS = frozenset(
    {
        "mfi_above",
        "mfi_below",
        "obv_cross_above_sma",
        "obv_cross_below_sma",
        "cmf_above",
        "cmf_below",
        "ad_cross_above_sma",
        "ad_cross_below_sma",
    }
)

# Maps strategy name -> required option_type for data fetching.
# "call"/"put" means only that type is needed; None means both are needed.
STRATEGY_OPTION_TYPE: dict[str, str | None] = {
    "long_calls": "call",
    "short_calls": "call",
    "long_call_spread": "call",
    "short_call_spread": "call",
    "long_call_butterfly": "call",
    "short_call_butterfly": "call",
    "long_call_calendar": "call",
    "short_call_calendar": "call",
    "long_call_diagonal": "call",
    "short_call_diagonal": "call",
    "covered_call": "call",
    "long_puts": "put",
    "short_puts": "put",
    "long_put_spread": "put",
    "short_put_spread": "put",
    "long_put_butterfly": "put",
    "short_put_butterfly": "put",
    "long_put_calendar": "put",
    "short_put_calendar": "put",
    "long_put_diagonal": "put",
    "short_put_diagonal": "put",
    "long_straddles": None,
    "short_straddles": None,
    "long_strangles": None,
    "short_strangles": None,
    "iron_condor": None,
    "reverse_iron_condor": None,
    "iron_butterfly": None,
    "reverse_iron_butterfly": None,
    "protective_put": None,
    "collar": None,
    "cash_secured_put": "put",
    "call_back_spread": "call",
    "put_back_spread": "put",
    "call_front_spread": "call",
    "put_front_spread": "put",
    "long_call_condor": "call",
    "short_call_condor": "call",
    "long_put_condor": "put",
    "short_put_condor": "put",
}

# --- Plugin strategies ---
for _name, _entry in get_plugin_strategies().items():
    if _name in STRATEGIES:
        _log.warning("Plugin overrides built-in strategy: %s", _name)
    _func, _desc, _is_cal, _opt_type = _entry
    STRATEGIES[_name] = (_func, _desc, _is_cal)
    STRATEGY_OPTION_TYPE[_name] = _opt_type

# Rebuild derived sets to include plugin strategies
CALENDAR_STRATEGIES = {name for name, (_, _, is_cal) in STRATEGIES.items() if is_cal}
STRATEGY_NAMES = sorted(STRATEGIES.keys())


def get_required_option_type(strategy_name: str) -> str | None:
    """Return 'call', 'put', or None (both) for a given strategy name."""
    return STRATEGY_OPTION_TYPE.get(strategy_name)


_TOOL_DESCRIPTIONS: dict[str, str] = {
    "load_csv_data": (
        "Load a CSV file as an optopsy dataset with explicit column index "
        "mapping. Use this to load user-uploaded CSV files. Inspect the "
        "column headers provided in the upload context to determine the "
        "correct index for each field. The defaults assume an 8-column "
        "layout: underlying_symbol(0), option_type(1), expiration(2), "
        "quote_date(3), strike(4), bid(5), ask(6), delta(7). "
        "Pass underlying_price if the CSV includes that column."
    ),
    "preview_data": (
        "Show shape, columns, date range, and sample rows of a dataset. "
        "Omit dataset_name to inspect the most-recently-loaded dataset."
    ),
    "describe_data": (
        "Show summary statistics, data types, missing values, and "
        "distributions for a dataset. Use for data quality checks "
        "and debugging."
    ),
    "check_data_quality": (
        "Run an integrity check on a loaded dataset against the columns "
        "and data quality the backtesting engine requires. Reports "
        "missing/mistyped required columns (including delta), "
        "optional column availability "
        "(Greeks, volume, IV), null analysis on critical columns, bid/ask "
        "quality (zero bids, crossed markets, spread stats), date coverage "
        "and gaps, monthly row distribution, duplicate rows, and negative "
        "bid/ask/strike values. Optionally pass strategy_name for "
        "strategy-specific checks: option type balance (e.g. iron condors "
        "need both calls and puts), strike density (butterflies need ≥3 "
        "strikes per date), and expiration coverage (calendar strategies "
        "need ≥2 expirations per date). Returns actionable "
        "recommendations. Use this after loading data and before running "
        "strategies to make informed parameter choices."
    ),
    "suggest_strategy_params": (
        "Analyze a loaded dataset and suggest good starting parameters "
        "(max_entry_dte, exit_dte, and per-leg delta targets) based on the actual DTE "
        "and delta distributions. Call this before running a strategy when "
        "the user has not specified explicit parameters, to avoid guessing "
        "values the data can't satisfy. Returns percentile tables, per-leg "
        "delta target recommendations for the given strategy, and a "
        "JSON block of recommended parameter values ready to pass to "
        "run_strategy; the DTE-related values can also be reused with scan_strategies."
    ),
    "run_strategy": (
        "Run an options strategy backtest on the loaded dataset. "
        "Strikes are selected by per-leg delta targeting (leg1_delta, leg2_delta, etc.) — "
        "each leg picks the option closest to the target |delta| within [min, max]. "
        "All strategies have sensible delta defaults; only override when the user specifies "
        "explicit delta values. Supports stop_loss, take_profit, max_hold_days for early exits "
        "and commission for per-contract fees. "
        "Calendar/diagonal strategies also accept front_dte_min, "
        "front_dte_max, back_dte_min, back_dte_max."
    ),
    "scan_strategies": (
        "Run multiple strategy/parameter combinations in one call and "
        "return a ranked leaderboard. Use this instead of calling "
        "run_strategy repeatedly when the user wants to compare DTE values "
        "or multiple strategies on the same dataset. "
        "Does NOT support signals or calendar strategies — use run_strategy "
        "for those."
    ),
    "list_results": (
        "List all strategy runs already executed in this session. "
        "Call this before running a strategy to check whether the same "
        "combination has already been run and avoid redundant calls. "
        "Returns a table sorted by mean_return descending."
    ),
    "compare_results": (
        "Compare multiple strategy results side-by-side. Produces a "
        "structured comparison table with metrics (mean return, win rate, "
        "Sharpe ratio, max drawdown, profit factor) and highlights the "
        "best performer on each metric. Use this after running multiple "
        "strategies to get a clear comparison instead of describing "
        "differences in prose. Optionally includes a grouped bar chart."
    ),
    "build_custom_signal": (
        "Build a custom signal from arbitrary pandas/numpy code. Use when no "
        "built-in signal matches the user's condition (gap ups, volume spikes, "
        "price crossing N-day highs, etc.). Write Python code that computes a "
        "boolean Series named `signal` from OHLCV DataFrame `df`. The result "
        "is stored as a signal slot for use with run_strategy."
    ),
    "build_signal": (
        "Build a TA signal (or compose multiple signals) and store the "
        "resulting valid dates under a named slot. Use this to create "
        "composite signals (e.g. RSI < 30 AND price above SMA 200) that "
        "can then be passed to run_strategy via entry_signal_slot / "
        "exit_signal_slot. Requires data to be loaded first."
    ),
    "preview_signal": (
        "Show the valid dates stored in a named signal slot. "
        "Use after build_signal to inspect how many dates matched."
    ),
    "list_signals": (
        "List all named signal slots built in this session. "
        "Shows slot names, date counts, and date ranges."
    ),
    "inspect_cache": (
        "List all locally cached datasets and their date ranges without "
        "making any network requests. Use this to discover what data is "
        "already available before deciding whether to fetch more. "
        "Optionally filter by symbol."
    ),
    "clear_cache": (
        "Delete cached datasets (options chains, stock prices). "
        "Optionally filter by symbol."
    ),
    "fetch_stock_data": (
        "Fetch all available daily OHLCV (open/high/low/close/volume) "
        "stock price data for a symbol via yfinance. Always fetches the "
        "full history and caches it locally. Use this to inspect price "
        "history, verify signal dates, or prime the cache before running "
        "strategies with TA signals."
    ),
    "simulate": (
        "Run a chronological simulation of an options strategy. "
        "Walks through trades sequentially with capital tracking, "
        "position limits, and equity curve generation. Returns "
        "trade log, equity curve, and summary stats (win rate, "
        "max drawdown, profit factor, etc.)."
    ),
    "get_simulation_trades": (
        "Show the full trade log from a previous simulation. "
        "Use after 'simulate' when the user asks to see "
        "detailed trades."
    ),
    "create_chart": (
        "Create an interactive Plotly chart from strategy results, "
        "simulation trade logs, datasets, or signals. Supports "
        "multi-series charts via y_columns (multiple metrics) or "
        "group_by (split by category). Use data_source='results' to "
        "chart all session results as a comparison. Supports grouped "
        "and stacked bar charts via bar_mode."
    ),
    "plot_vol_surface": (
        "Plot a volatility surface (heatmap of implied volatility by "
        "strike and expiration) for a given date. Requires a dataset "
        "with implied_volatility column (e.g. from EODHD)."
    ),
    "iv_term_structure": (
        "Plot the IV term structure (ATM implied volatility across "
        "expirations) for a given date. Shows how IV varies by "
        "time to expiration. Requires implied_volatility in the dataset."
    ),
    "query_results": (
        "Query, sort, filter, and slice the full data from a previous "
        "strategy run or simulation. Results are cached globally — use "
        "this instead of re-running strategies to answer follow-up "
        "questions about results (e.g. 'sort by returns', 'show the top "
        "5 buckets', 'filter to DTE > 30'). Omit result_key to list "
        "all available result keys."
    ),
    "summarize_session": (
        "Generate a full summary of the current session: datasets loaded, "
        "strategy backtests run (with key metrics), signals built, and "
        "simulations executed. Call this when the user asks for a recap, "
        "summary, or overview of what has been done in the session."
    ),
}

# Tools owned by data providers — excluded from core tool schema generation.
_PROVIDER_TOOLS = frozenset({"download_options_data", "fetch_options_data"})


def get_tool_schemas() -> list[dict]:
    """Return OpenAI-compatible tool schemas for all optopsy functions.

    Generates parameter schemas from Pydantic models in ``_models.py``
    and pairs them with prompt-engineered descriptions from
    ``_TOOL_DESCRIPTIONS``.
    """
    from ._models import TOOL_ARG_MODELS, pydantic_to_openai_params

    tools = []
    for tool_name, model_cls in TOOL_ARG_MODELS.items():
        if tool_name in _PROVIDER_TOOLS:
            continue
        description = _TOOL_DESCRIPTIONS.get(tool_name, f"Execute {tool_name}")
        # Prepend dynamic strategy list to run_strategy description
        if tool_name == "run_strategy":
            description = (
                "Run an options strategy backtest on the loaded dataset. "
                "Strategies: " + ", ".join(STRATEGY_NAMES) + ". "
            ) + description.removeprefix(
                "Run an options strategy backtest on the loaded dataset. "
            )
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": description,
                    "parameters": pydantic_to_openai_params(model_cls),
                },
            }
        )

    # Data provider tools (only added when API keys are configured)
    tools.extend(get_all_provider_tool_schemas())

    # Plugin tools
    for reg in get_plugin_tools():
        try:
            schemas = reg.get("schemas", [])
            descriptions = reg.get("descriptions", {}) or {}
            if descriptions:
                for schema in schemas:
                    function_def = schema.get("function")
                    if not isinstance(function_def, dict):
                        continue
                    name = function_def.get("name")
                    if (
                        name
                        and not function_def.get("description")
                        and name in descriptions
                    ):
                        function_def["description"] = descriptions[name]
            tools.extend(schemas)
            _TOOL_DESCRIPTIONS.update(descriptions)
        except Exception:
            _log.warning("Failed to process plugin tool registration", exc_info=True)

    return tools
