from .core import _calls, _puts, _process_strategy


from .definitions import (
    single_strike_external_cols,
    single_strike_internal_cols,
    double_strike_external_cols,
    double_strike_internal_cols,
    straddle_internal_cols,
)
from .rules import _rule_non_overlapping_strike

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


def long_calls(data, **kwargs):
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=single_strike_internal_cols,
        external_cols=single_strike_external_cols,
        leg_def=[("long", _calls)],
        params=params,
    )


def long_puts(data, **kwargs):
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=single_strike_internal_cols,
        external_cols=single_strike_external_cols,
        leg_def=[("long", _puts)],
        params=params,
    )


def short_calls(data, **kwargs):
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=single_strike_internal_cols,
        external_cols=single_strike_external_cols,
        leg_def=[("short", _calls)],
        params=params,
    )


def short_puts(data, **kwargs):
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=single_strike_internal_cols,
        external_cols=single_strike_external_cols,
        leg_def=[("short", _puts)],
        params=params,
    )


def long_straddles(data, **kwargs):
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=straddle_internal_cols,
        external_cols=single_strike_external_cols,
        leg_def=[("long", _puts), ("long", _calls)],
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


def short_straddles(data, **kwargs):
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=straddle_internal_cols,
        external_cols=single_strike_external_cols,
        leg_def=[("short", _puts), ("short", _calls)],
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


def long_strangles(data, **kwargs):
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=double_strike_internal_cols,
        external_cols=double_strike_external_cols,
        leg_def=[("long", _puts), ("long", _calls)],
        rules=_rule_non_overlapping_strike,
        join_on=["underlying_symbol", "expiration", "dte_entry", "dte_range"],
        params=params,
    )


def short_strangles(data, **kwargs):
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=double_strike_internal_cols,
        external_cols=double_strike_external_cols,
        leg_def=[("short", _puts), ("short", _calls)],
        rules=_rule_non_overlapping_strike,
        join_on=["underlying_symbol", "expiration", "dte_entry", "dte_range"],
        params=params,
    )


def long_call_spread(data, **kwargs):
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=double_strike_internal_cols,
        external_cols=double_strike_external_cols,
        leg_def=[("long", _calls), ("short", _calls)],
        rules=_rule_non_overlapping_strike,
        join_on=["underlying_symbol", "expiration", "dte_entry", "dte_range"],
        params=params,
    )


def long_put_spread(data, **kwargs):
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=double_strike_internal_cols,
        external_cols=double_strike_external_cols,
        leg_def=[("short", _puts), ("long", _puts)],
        rules=_rule_non_overlapping_strike,
        join_on=["underlying_symbol", "expiration", "dte_entry", "dte_range"],
        params=params,
    )


def short_call_spread(data, **kwargs):
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=double_strike_internal_cols,
        external_cols=double_strike_external_cols,
        leg_def=[("short", _calls), ("long", _calls)],
        rules=_rule_non_overlapping_strike,
        join_on=["underlying_symbol", "expiration", "dte_entry", "dte_range"],
        params=params,
    )


def short_put_spread(data, **kwargs):
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        internal_cols=double_strike_internal_cols,
        external_cols=double_strike_external_cols,
        leg_def=[("long", _puts), ("short", _puts)],
        rules=_rule_non_overlapping_strike,
        join_on=["underlying_symbol", "expiration", "dte_entry", "dte_range"],
        params=params,
    )
