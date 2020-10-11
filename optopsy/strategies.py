from .core import _calls, _puts, _process_strategy
from .definitions import (
    single_strike_external_cols,
    single_strike_internal_cols,
    double_strike_external_cols,
    double_strike_internal_cols,
    straddle_internal_cols,
)
from .rules import _rule_non_overlapping_strike
from enum import Enum

default_kwargs = {
    "dte_interval": 7,
    "max_entry_dte": 90,
    "exit_dte": 0,
    "otm_pct_interval": 0.05,
    "max_otm_pct": 0.5,
    "min_bid_ask": 0.05,
    "drop_nan": True,
    "raw": False,
}


class Side(Enum):
    long = 1
    short = -1


def _singles(data, leg_def, **kwargs):
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=single_strike_internal_cols,
        external_cols=single_strike_external_cols,
        leg_def=leg_def,
        params=params,
    )


def _straddles(data, leg_def, **kwargs):
    params = {**default_kwargs, **kwargs}

    return _process_strategy(
        data,
        internal_cols=straddle_internal_cols,
        external_cols=single_strike_external_cols,
        leg_def=leg_def,
        join_on=[
            "underlying_symbol",
            "expiration",
            "strike",
            "dte_entry",
            "dte_range",
            "otm_pct_range",
            "underlying_price_entry",
        ],
        params=params,
    )


def _strangles(data, leg_def, **kwargs):
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=double_strike_internal_cols,
        external_cols=double_strike_external_cols,
        leg_def=leg_def,
        rules=_rule_non_overlapping_strike,
        join_on=["underlying_symbol", "expiration", "dte_entry", "dte_range"],
        params=params,
    )


def _call_spread(data, leg_def, **kwargs):
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=double_strike_internal_cols,
        external_cols=double_strike_external_cols,
        leg_def=leg_def,
        rules=_rule_non_overlapping_strike,
        join_on=["underlying_symbol", "expiration", "dte_entry", "dte_range"],
        params=params,
    )


def _put_spread(data, leg_def, **kwargs):
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=double_strike_internal_cols,
        external_cols=double_strike_external_cols,
        leg_def=leg_def,
        rules=_rule_non_overlapping_strike,
        join_on=["underlying_symbol", "expiration", "dte_entry", "dte_range"],
        params=params,
    )


def long_calls(data, **kwargs):
    return _singles(data, [(Side.long, _calls)], **kwargs)


def long_puts(data, **kwargs):
    return _singles(data, [(Side.long, _puts)], **kwargs)


def short_calls(data, **kwargs):
    return _singles(data, [(Side.short, _calls)], **kwargs)


def short_puts(data, **kwargs):
    return _singles(data, [(Side.short, _puts)], **kwargs)


def long_straddles(data, **kwargs):
    return _straddles(data, [(Side.long, _puts), (Side.long, _calls)], **kwargs)


def short_straddles(data, **kwargs):
    return _straddles(data, [(Side.short, _puts), (Side.short, _calls)], **kwargs)


def long_strangles(data, **kwargs):
    return _strangles(data, [(Side.long, _puts), (Side.long, _calls)], **kwargs)


def short_strangles(data, **kwargs):
    return _strangles(data, [(Side.short, _puts), (Side.short, _calls)], **kwargs)


def long_call_spread(data, **kwargs):
    return _call_spread(data, [(Side.long, _calls), (Side.short, _calls)], **kwargs)


def short_call_spread(data, **kwargs):
    return _call_spread(data, [(Side.short, _calls), (Side.long, _calls)], **kwargs)


def long_put_spread(data, **kwargs):
    return _put_spread(data, [(Side.short, _puts), (Side.long, _puts)], **kwargs)


def short_put_spread(data, **kwargs):
    return _put_spread(data, [(Side.long, _puts), (Side.short, _puts)], **kwargs)
