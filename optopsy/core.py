import pandas as pd
import numpy as np

from .definitions import *

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


def _calculate_profit_loss(data):
    return data.assign(long_profit=lambda r: r["exit"] - r["entry"]).assign(
        short_profit=lambda r: r["entry"] - r["exit"]
    )


def _calculate_profit_loss_pct(data):
    return data.assign(
        long_profit_pct=lambda r: round((r["exit"] - r["entry"]) / r["entry"], 2)
    ).assign(short_profit_pct=lambda r: round((r["entry"] - r["exit"]) / r["entry"], 2))


def _select_final_output_column(data, cols, side):
    if side == "long" or side == "short":
        root = f"{side}_profit_pct"
        all_cols = cols + [col for col in data.columns if root in col]
        return data[all_cols]
    else:
        return data


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


def _group_by_intervals(data, cols, drop_na, side):

    if side == "long":
        side = ["long_profit_pct"]
    elif side == "short":
        side = ["short_profit_pct"]
    else:
        side = ["long_profit_pct", "short_profit_pct"]

    grouped_dataset = data.groupby(cols)[side].describe()

    grouped_dataset.columns = [
        "_".join(col).rstrip("_") for col in grouped_dataset.columns.values
    ]

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
        .pipe(_calculate_profit_loss)
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
