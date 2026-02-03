from typing import Any, Callable, Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
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


def _filter_by_delta(
    data: pd.DataFrame, delta_min: Optional[float], delta_max: Optional[float]
) -> pd.DataFrame:
    """
    Filter options by delta range.

    Args:
        data: DataFrame with delta column
        delta_min: Minimum delta value (inclusive), or None for no lower bound
        delta_max: Maximum delta value (inclusive), or None for no upper bound

    Returns:
        Filtered DataFrame
    """
    if delta_min is None and delta_max is None:
        return data

    if delta_min is not None and delta_max is not None:
        return _trim(data, "delta", delta_min, delta_max)
    elif delta_min is not None:
        return _ltrim(data, "delta", delta_min)
    else:
        return _rtrim(data, "delta", delta_max)


def _cut_options_by_delta(
    data: pd.DataFrame, delta_interval: Optional[float]
) -> pd.DataFrame:
    """
    Categorize options into delta intervals for grouping.

    Args:
        data: DataFrame with delta_entry column
        delta_interval: Interval size for delta grouping, or None to skip

    Returns:
        DataFrame with delta_range column added (if delta_interval provided)
    """
    if delta_interval is None:
        return data

    # Delta ranges from -1 to 1 for puts and calls
    delta_intervals = [
        round(i, 2) for i in list(np.arange(-1.0, 1.0 + delta_interval, delta_interval))
    ]
    data["delta_range"] = pd.cut(data["delta_entry"], delta_intervals)
    return data


def _group_by_intervals(
    data: pd.DataFrame, cols: List[str], drop_na: bool
) -> pd.DataFrame:
    """Group options by intervals and calculate descriptive statistics."""
    # this is a bottleneck, try to optimize
    grouped_dataset = data.groupby(cols, observed=False)["pct_change"].describe()

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
        **kwargs: Configuration parameters including max_otm_pct, min_bid_ask, exit_dte,
                  delta_min, delta_max

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

    has_delta = "delta" in data.columns
    delta_min = kwargs.get("delta_min")
    delta_max = kwargs.get("delta_max")

    # remove option chains that are worthless, it's unrealistic to enter
    # trades with worthless options
    entries = _remove_min_bid_ask(data, kwargs["min_bid_ask"])

    # Apply delta filtering only to entries (not exits) - delta changes over time
    if has_delta and (delta_min is not None or delta_max is not None):
        entries = _filter_by_delta(entries, delta_min, delta_max)

    # to reduce unnecessary computation, filter for options with the desired exit DTE
    exits = _get(data, "dte", kwargs["exit_dte"])

    # Determine merge columns
    merge_cols = ["underlying_symbol", "option_type", "expiration", "strike"]

    result = (
        entries.merge(
            right=exits,
            on=merge_cols,
            suffixes=("_entry", "_exit"),
        )
        # by default we use the midpoint spread price to calculate entry and exit costs
        .assign(entry=lambda r: (r["bid_entry"] + r["ask_entry"]) / 2)
        .assign(exit=lambda r: (r["bid_exit"] + r["ask_exit"]) / 2)
        .pipe(_remove_invalid_evaluated_options)
    )

    # Determine output columns based on whether delta is present
    output_cols = evaluated_cols.copy()
    if has_delta and "delta_entry" in result.columns:
        output_cols = output_cols + ["delta_entry"]

    return result[output_cols]


def _evaluate_all_options(data: pd.DataFrame, **kwargs: Any) -> pd.DataFrame:
    """
    Complete pipeline to evaluate all options with DTE and OTM percentage categorization.

    Args:
        data: DataFrame containing option chain data
        **kwargs: Configuration parameters for evaluation and categorization

    Returns:
        DataFrame with evaluated and categorized options
    """
    result = (
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

    # Apply delta grouping if delta_interval is specified
    delta_interval = kwargs.get("delta_interval")
    if delta_interval is not None:
        result = result.pipe(_cut_options_by_delta, delta_interval)

    return result


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


def _get_leg_quantity(leg: Tuple) -> int:
    """Get quantity for a leg, defaulting to 1 if not specified."""
    return leg[2] if len(leg) > 2 else 1


def _apply_ratios(data: pd.DataFrame, leg_def: List[Tuple]) -> pd.DataFrame:
    """Apply position ratios (long/short multipliers) and quantities to entry and exit prices."""
    for idx in range(1, len(leg_def) + 1):
        entry_col = f"entry_leg{idx}"
        exit_col = f"exit_leg{idx}"
        leg = leg_def[idx - 1]
        multiplier = leg[0].value * _get_leg_quantity(leg)
        # Use default arguments to capture values at each iteration (avoid late binding)
        entry_kwargs = {entry_col: lambda r, col=entry_col, m=multiplier: r[col] * m}
        exit_kwargs = {exit_col: lambda r, col=exit_col, m=multiplier: r[col] * m}
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


def _rename_leg_columns(
    data: pd.DataFrame, leg_idx: int, join_on: List[str]
) -> pd.DataFrame:
    """Rename columns with leg suffix, excluding join columns."""
    rename_map = {
        col: f"{col}_leg{leg_idx}" for col in data.columns if col not in join_on
    }
    return data.rename(columns=rename_map)


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

    # Pre-rename columns for each leg to avoid suffix issues with 3+ legs
    partials = [
        _rename_leg_columns(leg[1](data).copy(), idx, join_on or [])
        for idx, leg in enumerate(leg_def, start=1)
    ]
    suffixes = [f"_leg{idx}" for idx in range(1, len(leg_def) + 1)]

    # Merge all legs sequentially
    result = partials[0]
    for partial in partials[1:]:
        result = pd.merge(result, partial, on=join_on, how="inner")

    return result.pipe(_rule_func, rules, leg_def).pipe(
        _assign_profit, leg_def, suffixes
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

    # Build external_cols, adding delta_range if delta grouping is enabled
    external_cols = context["external_cols"].copy()
    if context["params"].get("delta_interval") is not None:
        external_cols = ["delta_range"] + external_cols

    return (
        _evaluate_all_options(
            data,
            dte_interval=context["params"]["dte_interval"],
            max_entry_dte=context["params"]["max_entry_dte"],
            exit_dte=context["params"]["exit_dte"],
            otm_pct_interval=context["params"]["otm_pct_interval"],
            max_otm_pct=context["params"]["max_otm_pct"],
            min_bid_ask=context["params"]["min_bid_ask"],
            delta_min=context["params"].get("delta_min"),
            delta_max=context["params"].get("delta_max"),
            delta_interval=context["params"].get("delta_interval"),
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
            external_cols,
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
