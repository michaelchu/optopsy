from typing import Any, Callable, Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from functools import reduce
from .definitions import evaluated_cols
from .checks import _run_checks

pd.set_option("expand_frame_repr", False)
pd.set_option("display.max_rows", None, "display.max_columns", None)


def _assign_dte(data: pd.DataFrame) -> pd.DataFrame:
    """Assign days to expiration (DTE) to the dataset."""
    return data.assign(dte=lambda r: (r["expiration"] - r["quote_date"]).dt.days)


def _trim(data: pd.DataFrame, col: str, lower: float, upper: float) -> pd.DataFrame:
    """Filter dataframe rows where column value is between lower and upper bounds."""
    return data.loc[(data[col] >= lower) & (data[col] <= upper)]


def _ltrim(data: pd.DataFrame, col: str, lower: float) -> pd.DataFrame:
    """Filter dataframe rows where column value is greater than or equal to lower bound."""
    return data.loc[data[col] >= lower]


def _rtrim(data: pd.DataFrame, col: str, upper: float) -> pd.DataFrame:
    """Filter dataframe rows where column value is less than or equal to upper bound."""
    return data.loc[data[col] <= upper]


def _get(data: pd.DataFrame, col: str, val: Any) -> pd.DataFrame:
    """Filter dataframe rows where column equals specified value."""
    return data.loc[data[col] == val]


def _remove_min_bid_ask(data: pd.DataFrame, min_bid_ask: float) -> pd.DataFrame:
    """Remove options with bid or ask prices below minimum threshold."""
    return data.loc[(data["bid"] > min_bid_ask) & (data["ask"] > min_bid_ask)]


def _remove_invalid_evaluated_options(data: pd.DataFrame) -> pd.DataFrame:
    """Keep evaluated options where entry DTE is greater than exit DTE."""
    return data.loc[
        (data["dte_exit"] <= data["dte_entry"])
        & (data["dte_entry"] != data["dte_exit"])
    ]


def _cut_options_by_dte(
    data: pd.DataFrame, dte_interval: int, max_entry_dte: int
) -> pd.DataFrame:
    """Categorize options into DTE intervals for grouping."""
    dte_intervals = list(range(0, max_entry_dte, dte_interval))
    data["dte_range"] = pd.cut(data["dte_entry"], dte_intervals)
    return data


def _cut_options_by_otm(
    data: pd.DataFrame, otm_pct_interval: float, max_otm_pct_interval: float
) -> pd.DataFrame:
    """Categorize options into out-of-the-money percentage intervals."""
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


def _group_by_intervals(
    data: pd.DataFrame, cols: List[str], drop_na: bool
) -> pd.DataFrame:
    """Group options by intervals and calculate descriptive statistics."""
    # this is a bottleneck, try to optimize
    grouped_dataset = data.groupby(cols)["pct_change"].describe()

    # if any non-count columns return NaN remove the row
    if drop_na:
        subset = [col for col in grouped_dataset.columns if "_count" not in col]
        grouped_dataset = grouped_dataset.dropna(subset=subset, how="all")

    return grouped_dataset


def _evaluate_options(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Evaluate options by filtering, merging entry and exit data, and calculating costs.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Configuration parameters including max_otm_pct, min_bid_ask, exit_dte

    Returns:
        DataFrame with evaluated options including entry and exit prices
    """
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


def _evaluate_all_options(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Complete pipeline to evaluate all options with DTE and OTM percentage categorization.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Configuration parameters for evaluation and categorization

    Returns:
        DataFrame with evaluated and categorized options
    """
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


def _calls(data: pd.DataFrame) -> pd.DataFrame:
    """Filter dataframe for call options only."""
    return data[data.option_type.str.lower().str.startswith("c")]


def _puts(data: pd.DataFrame) -> pd.DataFrame:
    """Filter dataframe for put options only."""
    return data[data.option_type.str.lower().str.startswith("p")]


def _calculate_otm_pct(data: pd.DataFrame) -> pd.DataFrame:
    """Calculate out-of-the-money percentage for each option."""
    return data.assign(
        otm_pct=lambda r: round((r["strike"] - r["underlying_price"]) / r["strike"], 2)
    )


def _apply_ratios(data: pd.DataFrame, leg_def: List[Tuple]) -> pd.DataFrame:
    """Apply position ratios (long/short multipliers) to entry and exit prices."""
    for idx in range(1, len(leg_def) + 1):
        entry_col = f"entry_leg{idx}"
        exit_col = f"exit_leg{idx}"
        entry_kwargs = {entry_col: lambda r: r[entry_col] * leg_def[idx - 1][0].value}
        exit_kwargs = {exit_col: lambda r: r[exit_col] * leg_def[idx - 1][0].value}
        data = data.assign(**entry_kwargs).assign(**exit_kwargs)

    return data


def _assign_profit(
    data: pd.DataFrame, leg_def: List[Tuple], suffixes: List[str]
) -> pd.DataFrame:
    """Calculate total profit/loss and percentage change for multi-leg strategies."""
    data = _apply_ratios(data, leg_def)

    # determine all entry and exit columns
    entry_cols = ["entry" + s for s in suffixes]
    exit_cols = ["exit" + s for s in suffixes]

    # calculate the total entry costs and exit proceeds
    data["total_entry_cost"] = data.loc[:, entry_cols].sum(axis=1)
    data["total_exit_proceeds"] = data.loc[:, exit_cols].sum(axis=1)

    data["pct_change"] = np.where(
        data["total_entry_cost"].abs() > 0,
        (data["total_exit_proceeds"] - data["total_entry_cost"])
        / data["total_entry_cost"].abs(),
        np.nan,
    )

    return data


def _strategy_engine(
    data: pd.DataFrame,
    leg_def: List[Tuple],
    join_on: Optional[List[str]] = None,
    rules: Optional[Callable] = None,
) -> pd.DataFrame:
    """
    Core strategy execution engine that constructs single or multi-leg option strategies.

    Args:
        data: DataFrame containing evaluated option data
        leg_def: List of tuples defining strategy legs (side, filter_function)
        join_on: Columns to join on for multi-leg strategies
        rules: Optional filtering rules to apply after joining legs

    Returns:
        DataFrame with constructed strategy and calculated profit/loss
    """
    if len(leg_def) == 1:
        data["pct_change"] = np.where(
            data["entry"].abs() > 0,
            (data["exit"] - data["entry"]) / data["entry"].abs(),
            np.nan,
        )
        return leg_def[0][1](data)

    def _rule_func(
        d: pd.DataFrame, r: Optional[Callable], ld: List[Tuple]
    ) -> pd.DataFrame:
        return d if r is None else r(d, ld)

    partials = [leg[1](data) for leg in leg_def]
    suffixes = [f"_leg{idx}" for idx in range(1, len(leg_def) + 1)]

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


def _process_strategy(data: pd.DataFrame, **context: Any) -> pd.DataFrame:
    """
    Main entry point for processing option strategies.

    Args:
        data: DataFrame containing raw option chain data
        **context: Dictionary containing strategy parameters, leg definitions, and formatting options

    Returns:
        DataFrame with processed strategy results
    """
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


def _format_output(
    data: pd.DataFrame,
    params: Dict[str, Any],
    internal_cols: List[str],
    external_cols: List[str],
) -> pd.DataFrame:
    """
    Format strategy output as either raw data or grouped statistics.

    Args:
        data: DataFrame with strategy results
        params: Parameters including 'raw' and 'drop_nan' flags
        internal_cols: Columns to include in raw output
        external_cols: Columns to group by for statistics output

    Returns:
        Formatted DataFrame with either raw data or descriptive statistics
    """
    if params["raw"]:
        return data[internal_cols].reset_index(drop=True)

    return data.pipe(
        _group_by_intervals, external_cols, params["drop_nan"]
    ).reset_index()
