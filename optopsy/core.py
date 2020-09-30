from .helpers import inspect
import pandas as pd
import numpy as np

pd.set_option("expand_frame_repr", False)
pd.set_option("display.max_rows", None, "display.max_columns", None)


def _assign_dte(data):
    return data.assign(dte=lambda r: (r["expiration"] - r["quote_date"]).dt.days)


def _trim_data(data, col, lower, upper):
    if lower is not None and upper is not None:
        return data.loc[(data[col] >= lower) & (data[col] <= upper)]
    elif lower is None and upper is not None:
        return data.loc[data[col] <= upper]
    elif lower is not None and upper is None:
        return data.loc[data[col] >= lower]
    else:
        return data


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
    ).assign(short_profit_pct=lambda r: round((r["entry"] - r["exit"]) / r["exit"], 2))


def _select_output_columns(data):
    return data[
        [
            "underlying_symbol",
            "option_type",
            "expiration",
            "dte_entry",
            "strike",
            "underlying_price_entry",
            "underlying_price_exit",
            "entry",
            "exit",
            "long_profit",
            "short_profit",
        ]
    ]


def _select_final_output_column(data, ret_profit, side):
    common_cols = ["dte_range", "strike_otm_pct_range"]

    if side == "long" or side == "short":
        root = f"{side}_profit" if ret_profit else f"{side}_profit_pct"
        cols = common_cols + [col for col in data.columns if root in col]
        return data[cols]
    else:
        return data


def _cut_options_by_dte(data, dte_interval, max_entry_dte):
    dte_intervals = list(range(0, max_entry_dte, dte_interval))
    data["dte_range"] = pd.cut(data["dte_entry"], dte_intervals)
    return data


def _cut_options_by_strike_dist(
    data, strike_dist_pct_interval, max_strike_dist_pct_interval
):
    # consider using np.linspace in future
    strike_dist_pct_intervals = [
        round(i, 2)
        for i in list(
            np.arange(
                max_strike_dist_pct_interval * -1,
                max_strike_dist_pct_interval,
                strike_dist_pct_interval,
            )
        )
    ]
    data["strike_otm_pct_range"] = pd.cut(
        data["strike_dist_pct"], strike_dist_pct_intervals
    )
    return data


def _group_by_intervals(data, drop_na):
    grouped_dataset = data.groupby(["dte_range", "strike_otm_pct_range"]).agg(
        {
            "long_profit": ["min", "max", "mean", "median", "std", "count"],
            "long_profit_pct": ["min", "max", "mean", "median", "std", "count"],
            "short_profit": ["min", "max", "mean", "median", "std", "count"],
            "short_profit_pct": ["min", "max", "mean", "median", "std", "count"],
        }
    )
    grouped_dataset.columns = [
        "_".join(col).rstrip("_") for col in grouped_dataset.columns.values
    ]

    # if any non-count columns return NaN remove the row
    if drop_na:
        subset = [col for col in grouped_dataset.columns if "_count" not in col]
        grouped_dataset = grouped_dataset.dropna(subset=subset, how="all")

    return grouped_dataset


def _evaluate(entries, exits):
    return (
        entries.merge(
            right=exits,
            on=["underlying_symbol", "option_type", "expiration", "strike"],
            suffixes=("_entry", "_exit"),
        )
        .assign(entry=lambda r: (r["bid_entry"] + r["ask_entry"]) / 2)
        .assign(exit=lambda r: (r["bid_exit"] + r["ask_exit"]) / 2)
    )


def _evaluate_options(data, min_bid_ask, exit_dte):
    """
    Take all option entries and exits and calculate the profit/loss
    per option chain.

    Args:
        data: Dataframe containing option chains

    Returns:
        DataFrame with each option chain evaluated in all entry and exit combinations

    """

    # remove option chains that are worthless, it's unrealistic to enter
    # trades with worthless options
    entries = _remove_min_bid_ask(data, min_bid_ask)

    # to reduce unnecessary computation, filter for options with the desired exit DTE
    exits = _get(data, "dte", exit_dte)
    evaluated_options = _evaluate(entries, exits)

    return (
        evaluated_options.pipe(_remove_invalid_evaluated_options)
        .pipe(_calculate_profit_loss)
        .pipe(_select_output_columns)
    )


def _process_entries_and_exits(
    data,
    dte_interval,
    max_entry_dte,
    exit_dte,
    strike_dist_pct_interval,
    max_strike_dist_pct_interval,
    min_bid_ask,
):
    return (
        data.pipe(_assign_dte)
        .pipe(_trim_data, "dte", exit_dte, max_entry_dte)
        .pipe(_evaluate_options, min_bid_ask, exit_dte)
        .pipe(_cut_options_by_dte, dte_interval, max_entry_dte)
        .pipe(_calculate_strike_dist_pct)
        .pipe(
            _cut_options_by_strike_dist,
            strike_dist_pct_interval,
            max_strike_dist_pct_interval,
        )
    )


def _calls(data):
    return data[data.option_type.str.lower().str.startswith("c")]


def _puts(data):
    return data[data.option_type.str.lower().str.startswith("p")]


def _calculate_strike_dist_pct(data):
    return data.assign(
        strike_dist_pct=lambda r: round(
            (r["strike"] - r["underlying_price_entry"]) / r["strike"], 2
        )
    )
