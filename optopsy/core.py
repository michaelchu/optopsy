import pandas as pd
import numpy as np
from functools import reduce
from .definitions import *
from .checks import _run_checks

pd.set_option("expand_frame_repr", False)
pd.set_option("display.max_rows", None, "display.max_columns", None)


def _assign_dte(data):
    return data.assign(dte=lambda r: (r["expiration"] - r["quote_date"]).dt.days)


def _trim(data, col, lower, upper):
    return data.loc[(data[col] >= lower) & (data[col] <= upper)]


def _ltrim(data, col, lower):
    return data.loc[data[col] >= lower]


def _rtrim(data, col, upper):
    return data.loc[data[col] <= upper]


def _get(data, col, val):
    return data.loc[data[col] == val]


def _remove_min_bid_ask(data, min_bid_ask):
    return data.loc[(data["bid"] > min_bid_ask) & (data["ask"] > min_bid_ask)]


def _remove_invalid_evaluated_options(data):
    return data.loc[
        (data["dte_exit"] <= data["dte_entry"])
        & (data["dte_entry"] != data["dte_exit"])
    ]


def _cut_options_by_dte(data, dte_interval, max_entry_dte):
    dte_intervals = list(range(0, max_entry_dte, dte_interval))
    data["dte_range"] = pd.cut(data["dte_entry"], dte_intervals)
    return data


def _cut_options_by_otm(data, otm_pct_interval, max_otm_pct_interval):
    # consider using np.linspace in future
    otm_pct_intervals = [
        round(i, 2)
        for i in list(
            np.arange(
                max_otm_pct_interval * -1,
                max_otm_pct_interval,
                otm_pct_interval,
            )
        )
    ]
    data["otm_pct_range"] = pd.cut(data["otm_pct_entry"], otm_pct_intervals)
    return data


def _group_by_intervals(data, cols, drop_na):
    # this is a bottleneck, try to optimize
    grouped_dataset = data.groupby(cols)["pct_change"].describe()

    # if any non-count columns return NaN remove the row
    if drop_na:
        subset = [col for col in grouped_dataset.columns if "_count" not in col]
        grouped_dataset = grouped_dataset.dropna(subset=subset, how="all")

    return grouped_dataset


def _evaluate_options(data, **kwargs):

    # trim option chains with strikes too far out from current price
    data = data.pipe(_calculate_otm_pct).pipe(
        _trim,
        "otm_pct",
        lower=kwargs["max_otm_pct"] * -1,
        upper=kwargs["max_otm_pct"],
    )

    # remove option chains that are worthless, it's unrealistic to enter
    # trades with worthless options
    entries = _remove_min_bid_ask(data, kwargs["min_bid_ask"])

    # to reduce unnecessary computation, filter for options with the desired exit DTE
    exits = _get(data, "dte", kwargs["exit_dte"])

    return (
        entries.merge(
            right=exits,
            on=["underlying_symbol", "option_type", "expiration", "strike"],
            suffixes=("_entry", "_exit"),
        )
        # by default we use the midpoint spread price to calculate entry and exit costs
        .assign(entry=lambda r: (r["bid_entry"] + r["ask_entry"]) / 2)
        .assign(exit=lambda r: (r["bid_exit"] + r["ask_exit"]) / 2)
        .pipe(_remove_invalid_evaluated_options)
    )[evaluated_cols]


def _evaluate_all_options(data, **kwargs):
    return (
        data.pipe(_assign_dte)
        .pipe(_trim, "dte", kwargs["exit_dte"], kwargs["max_entry_dte"])
        .pipe(_evaluate_options, **kwargs)
        .pipe(_cut_options_by_dte, kwargs["dte_interval"], kwargs["max_entry_dte"])
        .pipe(
            _cut_options_by_otm,
            kwargs["otm_pct_interval"],
            kwargs["max_otm_pct"],
        )
    )


def _calls(data):
    return data[data.option_type.str.lower().str.startswith("c")]


def _puts(data):
    return data[data.option_type.str.lower().str.startswith("p")]


def _calculate_otm_pct(data):
    return data.assign(
        otm_pct=lambda r: round((r["strike"] - r["underlying_price"]) / r["strike"], 2)
    )


def _apply_ratios(data, leg_def):
    for idx in range(1, len(leg_def) + 1):
        entry_col = f"entry_leg{idx}"
        exit_col = f"exit_leg{idx}"
        entry_kwargs = {entry_col: lambda r: r[entry_col] * leg_def[idx - 1][0].value}
        exit_kwargs = {exit_col: lambda r: r[exit_col] * leg_def[idx - 1][0].value}
        data = data.assign(**entry_kwargs).assign(**exit_kwargs)

    return data


def _assign_profit(data, leg_def, suffixes):
    data = _apply_ratios(data, leg_def)

    # determine all entry and exit columns
    entry_cols = ["entry" + s for s in suffixes]
    exit_cols = ["exit" + s for s in suffixes]

    # calculate the total entry costs and exit proceeds
    data["total_entry_cost"] = data.loc[:, entry_cols].sum(axis=1)
    data["total_exit_proceeds"] = data.loc[:, exit_cols].sum(axis=1)

    data["pct_change"] = (
        data["total_exit_proceeds"] - data["total_entry_cost"]
    ) / data["total_entry_cost"].abs()

    return data


def _strategy_engine(data, leg_def, join_on=None, rules=None):
    if len(leg_def) == 1:
        data["pct_change"] = (data["exit"] - data["entry"]) / data["entry"].abs()
        return leg_def[0][1](data)

    def _rule_func(d, r, ld):
        return d if r is None else r(d, ld)

    partials = [leg[1](data) for leg in leg_def]
    suffixes = [f"_leg{idx}" for idx in range(1, len(leg_def) + 1)]

    # noinspection PyTypeChecker
    return (
        reduce(
            lambda left, right: pd.merge(
                left, right, on=join_on, how="inner", suffixes=suffixes
            ),
            partials,
        )
        .pipe(_rule_func, rules, leg_def)
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
