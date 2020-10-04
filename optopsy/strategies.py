from .core import (
    _evaluate_all_options,
    _calls,
    _puts,
    _group_by_intervals,
    _calculate_profit_loss_pct,
    _select_final_output_column,
)

from .definitions import *

default_kwargs = {
    "dte_interval": 7,
    "max_entry_dte": 180,
    "exit_dte": 0,
    "otm_pct_interval": 0.05,
    "max_otm_pct": 1,
    "min_bid_ask": 0.05,
    "side": "long",
    "drop_nan": True,
    "raw": False,
    "on": None,
}


def _process_strategy(data, internal_cols, external_cols, _strategy_func, params):
    return (
        _evaluate_all_options(
            data,
            dte_interval=params["dte_interval"],
            max_entry_dte=params["max_entry_dte"],
            exit_dte=params["exit_dte"],
            otm_pct_interval=params["otm_pct_interval"],
            max_otm_pct=params["max_otm_pct"],
            min_bid_ask=params["min_bid_ask"],
        )
        .pipe(_strategy_func, params["on"])
        .pipe(_calculate_profit_loss_pct)
        .pipe(_format_output, params, internal_cols, external_cols)
    )


def _format_output(data, params, internal_cols, external_cols):
    if params["raw"]:
        return data[internal_cols]

    return (
        data.pipe(_group_by_intervals, external_cols, params["drop_nan"])
        .reset_index()
        .pipe(
            _select_final_output_column,
            external_cols,
            params["side"],
        )
    )


def _straddles(data, on):
    calls = _calls(data)
    puts = _puts(data)

    return (
        puts.merge(
            right=calls,
            on=on,
            suffixes=("_leg1", "_leg2"),
        )
        .assign(long_profit=lambda r: (r["long_profit_leg1"] + r["long_profit_leg2"]))
        .assign(
            short_profit=lambda r: (r["short_profit_leg1"] + r["short_profit_leg2"])
        )
        .assign(entry=lambda r: (r["entry_leg1"] + r["entry_leg2"]))
        .assign(exit=lambda r: (r["exit_leg1"] + r["exit_leg2"]))
    )


def _strangles(data, on):
    calls = _calls(data)
    puts = _puts(data)

    def _apply_strangle_rules(d):
        # apply rules to filter for valid strangles only
        return d.loc[d["strike_leg2"] > d["strike_leg1"]]

    return (
        puts.merge(
            right=calls,
            on=on,
            suffixes=("_leg1", "_leg2"),
        )
        .pipe(_apply_strangle_rules)
        .assign(long_profit=lambda r: (r["long_profit_leg1"] + r["long_profit_leg2"]))
        .assign(
            short_profit=lambda r: (r["short_profit_leg1"] + r["short_profit_leg2"])
        )
        .assign(entry=lambda r: (r["entry_leg1"] + r["entry_leg2"]))
        .assign(exit=lambda r: (r["exit_leg1"] + r["exit_leg2"]))
    )


def singles_calls(data, **kwargs):
    params = {**default_kwargs, **kwargs}
    return data.pipe(_calls).pipe(
        _process_strategy,
        single_strike_internal_cols,
        single_strike_external_cols,
        lambda d, o: d,
        params,
    )


def singles_puts(data, **kwargs):
    params = {**default_kwargs, **kwargs}
    return data.pipe(_puts).pipe(
        _process_strategy,
        single_strike_internal_cols,
        single_strike_external_cols,
        lambda d, o: d,
        params,
    )


def straddles(data, **kwargs):
    # join conditions to generate straddles
    kwargs["on"] = [
        "underlying_symbol",
        "expiration",
        "strike",
        "dte_entry",
        "dte_range",
        "otm_pct_range",
        "underlying_price_entry",
        "underlying_price_exit",
    ]
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        straddle_internal_cols,
        single_strike_external_cols,
        _straddles,
        params,
    )


def strangles(data, **kwargs):
    # join conditions to generate strangles
    kwargs["on"] = [
        "underlying_symbol",
        "expiration",
        "dte_entry",
        "dte_range",
        "underlying_price_entry",
        "underlying_price_exit",
    ]
    params = {**default_kwargs, **kwargs}
    return _process_strategy(
        data,
        double_strike_internal_cols,
        double_strike_external_cols,
        _strangles,
        params,
    )
