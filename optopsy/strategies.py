import pandas as pd
from functools import reduce
from .core import (
    _evaluate_all_options,
    _calls,
    _puts,
    _group_by_intervals,
)
from .checks import _run_checks
from .definitions import (
    single_strike_external_cols,
    single_strike_internal_cols,
    double_strike_external_cols,
    double_strike_internal_cols,
    straddle_internal_cols,
)

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


def _rule_non_overlapping_strike(d):
    return d.loc[d["strike_leg2"] > d["strike_leg1"]]


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


def _assign_profit(data, leg_def, suffixes):
    entry_cols = ["entry" + s for s in suffixes]
    exit_cols = ["exit" + s for s in suffixes]

    data["total_entry"] = data.loc[:, entry_cols].sum(axis=1)
    data["total_exit"] = data.loc[:, exit_cols].sum(axis=1)

    # apply leg ratio to entry/exit cols by leg
    profit_cols = [
        f"{leg_def[idx][0]}_profit_leg{idx+1}" for idx in range(0, len(leg_def))
    ]
    data["total_profit"] = data.loc[:, profit_cols].sum(axis=1)

    # profit_pct = total_profit / total_entry
    data["profit_pct"] = data["total_profit"] / data["total_entry"]

    return data


# noinspection PyTypeChecker
def _strategy_engine(data, leg_def, join_on=None, rules=None):
    if len(leg_def) == 1:
        data["profit_pct"] = data[f"{leg_def[0][0]}_profit"] / data["entry"]
        return leg_def[0][1](data)

    def _rule_func(d, r):
        return d if r is None else r(d)

    partials = [leg[1](data) for leg in leg_def]
    suffixes = [f"_leg{idx}" for idx in range(1, len(leg_def) + 1)]

    return (
        reduce(
            lambda left, right: pd.merge(
                left, right, on=join_on, how="inner", suffixes=suffixes
            ),
            partials,
        )
        .pipe(_rule_func, rules)
        .pipe(_assign_profit, leg_def, suffixes)
    )


def _process_strategy(data, **context):
    _run_checks(context["params"], data)
    return (
        _evaluate_all_options(
            data,
            dte_interval=context["params"]["dte_interval"],
            max_entry_dte=context["params"]["max_entry_dte"],
            exit_dte=context["params"]["exit_dte"],
            otm_pct_interval=context["params"]["otm_pct_interval"],
            max_otm_pct=context["params"]["max_otm_pct"],
            min_bid_ask=context["params"]["min_bid_ask"],
        )
        .pipe(
            _strategy_engine,
            context["leg_def"],
            context.get("join_on"),
            context.get("rules"),
        )
        .pipe(
            _format_output,
            context["params"],
            context["internal_cols"],
            context["external_cols"],
        )
    )


def _format_output(data, params, internal_cols, external_cols):
    if params["raw"]:
        return data[internal_cols].reset_index(drop=True)

    return data.pipe(
        _group_by_intervals, external_cols, params["drop_nan"]
    ).reset_index()
