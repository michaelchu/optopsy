from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .checks import _run_calendar_checks, _run_checks
from .definitions import describe_cols, evaluated_cols
from .timestamps import normalize_dates


def _calculate_fill_price(
    bid: pd.Series,
    ask: pd.Series,
    side_value: int,
    slippage: str,
    fill_ratio: float = 0.5,
    volume: Optional[pd.Series] = None,
    reference_volume: int = 1000,
) -> pd.Series:
    """
    Calculate fill price based on slippage model.

    Args:
        bid: Series of bid prices
        ask: Series of ask prices
        side_value: 1 for long (buying), -1 for short (selling)
        slippage: Slippage mode - "mid", "spread", or "liquidity"
        fill_ratio: Base fill ratio for liquidity mode (0.0-1.0)
        volume: Optional series of volume data for liquidity-based slippage
        reference_volume: Volume threshold for "liquid" option

    Returns:
        Series of fill prices adjusted for slippage
    """
    mid = (bid + ask) / 2
    half_spread = (ask - bid) / 2

    if slippage == "mid":
        return mid

    if slippage == "spread":
        ratio = 1.0
    else:  # liquidity
        if volume is None:
            ratio = fill_ratio
        else:
            # Higher fill ratio for illiquid options
            liquidity_score = (volume / reference_volume).clip(upper=1.0)
            ratio = fill_ratio + (1 - fill_ratio) * (1 - liquidity_score)

    if side_value == 1:  # long - buying at higher price
        return mid + (half_spread * ratio)
    else:  # short - selling at lower price
        return mid - (half_spread * ratio)


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


def _apply_signal_filter(
    data: pd.DataFrame,
    valid_dates: pd.DataFrame,
    date_col: str = "quote_date",
) -> pd.DataFrame:
    """
    Filter data to only include rows matching valid (symbol, date) pairs.

    Both the option chain data (normalized at the root of _process_strategy /
    _process_calendar_strategy) and signal dates (normalized in apply_signal)
    are already date-only, so this is a straightforward inner join.

    Args:
        data: DataFrame to filter (already date-normalized)
        valid_dates: DataFrame with (underlying_symbol, quote_date) of valid dates
            (already date-normalized via apply_signal)
        date_col: Name of the date column in data to match against (default: quote_date)

    Returns:
        Filtered DataFrame
    """
    if date_col != "quote_date":
        valid_dates = valid_dates.rename(columns={"quote_date": date_col})
    return data.merge(valid_dates, on=["underlying_symbol", date_col], how="inner")


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
    # Use observed=True to only return groups with actual data (avoids pandas 3.0
    # issue where observed=False returns all category combinations as empty rows)
    grouped_dataset = data.groupby(cols, observed=True)["pct_change"].describe()

    # if any non-count columns return NaN remove the row
    if drop_na:
        subset = [col for col in grouped_dataset.columns if "_count" not in col]
        grouped_dataset = grouped_dataset.dropna(subset=subset, how="all")

    return grouped_dataset


def _get_exits(
    data: pd.DataFrame, exit_dte: int, exit_dte_tolerance: int = 0
) -> pd.DataFrame:
    """
    Get exit rows from option data, optionally using tolerance-based DTE matching.

    When tolerance is 0 (default), only rows with exactly the target exit_dte are
    returned. When tolerance > 0, rows within [max(0, exit_dte - tolerance),
    exit_dte + tolerance] are considered, and for each contract the row with DTE
    closest to exit_dte is selected.

    Args:
        data: DataFrame containing option data with 'dte' column
        exit_dte: Target DTE for exit
        exit_dte_tolerance: Maximum allowed deviation from exit_dte (default 0)

    Returns:
        DataFrame of exit rows
    """
    if exit_dte_tolerance == 0:
        return _get(data, "dte", exit_dte)

    lower = max(0, exit_dte - exit_dte_tolerance)
    upper = exit_dte + exit_dte_tolerance
    candidates = _trim(data, "dte", lower, upper)

    if candidates.empty:
        return candidates

    # For each contract, pick the row with DTE closest to exit_dte
    contract_cols = ["underlying_symbol", "option_type", "expiration", "strike"]
    candidates = candidates.copy()
    candidates["_dte_diff"] = (candidates["dte"] - exit_dte).abs()
    exits = (
        candidates.sort_values("_dte_diff")
        .drop_duplicates(subset=contract_cols, keep="first")
        .drop(columns=["_dte_diff"])
    )
    return exits


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

    # Pre-computed signal date DataFrames (from apply_signal)
    entry_dates = kwargs.get("entry_dates")
    exit_dates = kwargs.get("exit_dates")

    # remove option chains that are worthless, it's unrealistic to enter
    # trades with worthless options
    entries = _remove_min_bid_ask(data, kwargs["min_bid_ask"])

    # Apply delta filtering only to entries (not exits) - delta changes over time
    if has_delta and (delta_min is not None or delta_max is not None):
        entries = _filter_by_delta(entries, delta_min, delta_max)

    # Apply entry date filtering (only to entries, exits are unaffected)
    if entry_dates is not None:
        entries = _apply_signal_filter(entries, entry_dates)

    # to reduce unnecessary computation, filter for options with the desired exit DTE
    exits = _get_exits(data, kwargs["exit_dte"], kwargs.get("exit_dte_tolerance", 0))

    # Apply exit date filtering (only to exits, entries are unaffected)
    if exit_dates is not None:
        exits = _apply_signal_filter(exits, exit_dates)

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

    # Include volume if present (for liquidity-based slippage)
    if "volume_entry" in result.columns:
        output_cols = output_cols + ["volume_entry"]
    if "volume_exit" in result.columns:
        output_cols = output_cols + ["volume_exit"]

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
    return data[data["option_type"].str.startswith("c")]


def _puts(data: pd.DataFrame) -> pd.DataFrame:
    """Filter dataframe for put options only."""
    return data[data["option_type"].str.startswith("p")]


def _calculate_otm_pct(data: pd.DataFrame) -> pd.DataFrame:
    """Calculate out-of-the-money percentage for each option."""
    return data.assign(
        otm_pct=lambda r: round((r["strike"] - r["underlying_price"]) / r["strike"], 2)
    )


def _get_leg_quantity(leg: Tuple) -> int:
    """Get quantity for a leg, defaulting to 1 if not specified."""
    return leg[2] if len(leg) > 2 else 1


def _apply_ratios(
    data: pd.DataFrame,
    leg_def: List[Tuple],
    slippage: str = "mid",
    fill_ratio: float = 0.5,
    reference_volume: int = 1000,
) -> pd.DataFrame:
    """
    Apply position ratios (long/short multipliers) and quantities to entry and exit prices.

    When slippage is enabled, recalculates fill prices from bid/ask based on position side.
    """
    data = data.copy()
    for idx in range(1, len(leg_def) + 1):
        entry_col = f"entry_leg{idx}"
        exit_col = f"exit_leg{idx}"
        bid_entry_col = f"bid_entry_leg{idx}"
        ask_entry_col = f"ask_entry_leg{idx}"
        bid_exit_col = f"bid_exit_leg{idx}"
        ask_exit_col = f"ask_exit_leg{idx}"
        volume_col = f"volume_entry_leg{idx}"

        leg = leg_def[idx - 1]
        side_value = leg[0].value
        quantity = _get_leg_quantity(leg)
        multiplier = side_value * quantity

        # Check if bid/ask columns exist for slippage calculation
        has_bid_ask = bid_entry_col in data.columns and ask_entry_col in data.columns

        if has_bid_ask and slippage != "mid":
            # Calculate fill price based on slippage model
            volume_entry = data.get(volume_col) if volume_col in data.columns else None

            # Entry: use side_value to determine buy/sell direction
            entry_fill = _calculate_fill_price(
                data[bid_entry_col],
                data[ask_entry_col],
                side_value,
                slippage,
                fill_ratio,
                volume_entry,
                reference_volume,
            )

            # Exit: reverse the side (closing the position)
            volume_exit_col = f"volume_exit_leg{idx}"
            volume_exit = (
                data.get(volume_exit_col) if volume_exit_col in data.columns else None
            )
            exit_fill = _calculate_fill_price(
                data[bid_exit_col],
                data[ask_exit_col],
                -side_value,
                slippage,
                fill_ratio,
                volume_exit,
                reference_volume,
            )

            # Apply multiplier (includes quantity)
            data[entry_col] = entry_fill * multiplier
            data[exit_col] = exit_fill * multiplier
        else:
            # Original behavior: just apply multiplier to mid price
            entry_kwargs = {
                entry_col: lambda r, col=entry_col, m=multiplier: r[col] * m
            }
            exit_kwargs = {exit_col: lambda r, col=exit_col, m=multiplier: r[col] * m}
            data = data.assign(**entry_kwargs).assign(**exit_kwargs)

    return data


def _assign_profit(
    data: pd.DataFrame,
    leg_def: List[Tuple],
    suffixes: List[str],
    slippage: str = "mid",
    fill_ratio: float = 0.5,
    reference_volume: int = 1000,
) -> pd.DataFrame:
    """Calculate total profit/loss and percentage change for multi-leg strategies."""
    data = _apply_ratios(data, leg_def, slippage, fill_ratio, reference_volume)

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
    slippage: str = "mid",
    fill_ratio: float = 0.5,
    reference_volume: int = 1000,
) -> pd.DataFrame:
    """
    Core strategy execution engine that constructs single or multi-leg option strategies.

    Args:
        data: DataFrame containing evaluated option data
        leg_def: List of tuples defining strategy legs (side, filter_function)
        join_on: Columns to join on for multi-leg strategies
        rules: Optional filtering rules to apply after joining legs
        slippage: Slippage mode - "mid", "spread", or "liquidity"
        fill_ratio: Base fill ratio for liquidity mode (0.0-1.0)
        reference_volume: Volume threshold for liquid options

    Returns:
        DataFrame with constructed strategy and calculated profit/loss
    """
    if len(leg_def) == 1:
        side = leg_def[0][0]
        has_bid_ask = "bid_entry" in data.columns and "ask_entry" in data.columns

        if has_bid_ask and slippage != "mid":
            data = data.copy()  # Avoid modifying original DataFrame
            # Calculate fill prices with slippage
            volume_entry = (
                data.get("volume_entry") if "volume_entry" in data.columns else None
            )

            data["entry"] = _calculate_fill_price(
                data["bid_entry"],
                data["ask_entry"],
                side.value,
                slippage,
                fill_ratio,
                volume_entry,
                reference_volume,
            )
            # Exit: reverse the side (closing the position)
            volume_exit = (
                data.get("volume_exit") if "volume_exit" in data.columns else None
            )
            data["exit"] = _calculate_fill_price(
                data["bid_exit"],
                data["ask_exit"],
                -side.value,
                slippage,
                fill_ratio,
                volume_exit,
                reference_volume,
            )

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

    # Pre-rename columns for each leg to avoid suffix issues with 3+ legs.
    # .rename() already returns a new DataFrame, so .copy() is unnecessary.
    partials = [
        _rename_leg_columns(leg[1](data), idx, join_on or [])
        for idx, leg in enumerate(leg_def, start=1)
    ]
    suffixes = [f"_leg{idx}" for idx in range(1, len(leg_def) + 1)]

    # Merge all legs sequentially
    result = partials[0]
    for partial in partials[1:]:
        result = pd.merge(result, partial, on=join_on, how="inner")

    return result.pipe(_rule_func, rules, leg_def).pipe(
        _assign_profit, leg_def, suffixes, slippage, fill_ratio, reference_volume
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

    # Normalize date columns once at the root so all downstream merges
    # (signal filtering, entry/exit matching) work regardless of source.
    data = data.copy()
    data["quote_date"] = normalize_dates(data["quote_date"])
    data["expiration"] = normalize_dates(data["expiration"])
    # Normalize option_type once so _calls/_puts avoid repeated .str.lower() calls
    data["option_type"] = data["option_type"].str.lower()

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
            exit_dte_tolerance=context["params"].get("exit_dte_tolerance", 0),
            otm_pct_interval=context["params"]["otm_pct_interval"],
            max_otm_pct=context["params"]["max_otm_pct"],
            min_bid_ask=context["params"]["min_bid_ask"],
            delta_min=context["params"].get("delta_min"),
            delta_max=context["params"].get("delta_max"),
            delta_interval=context["params"].get("delta_interval"),
            entry_dates=context["params"].get("entry_dates"),
            exit_dates=context["params"].get("exit_dates"),
        )
        .pipe(
            _strategy_engine,
            context["leg_def"],
            context.get("join_on"),
            context.get("rules"),
            context["params"].get("slippage", "mid"),
            context["params"].get("fill_ratio", 0.5),
            context["params"].get("reference_volume", 1000),
        )
        .pipe(
            _format_output,
            context["params"],
            context["internal_cols"],
            external_cols,
        )
    )


def _evaluate_calendar_options(
    data: pd.DataFrame, dte_min: int, dte_max: int, **kwargs: Any
) -> pd.DataFrame:
    """
    Evaluate options for a single leg of a calendar/diagonal spread.

    Args:
        data: DataFrame containing option chain data with DTE assigned
        dte_min: Minimum DTE for this leg
        dte_max: Maximum DTE for this leg
        **kwargs: Additional parameters including max_otm_pct, min_bid_ask

    Returns:
        DataFrame with evaluated options for this leg
    """
    # Filter by DTE range for this leg
    leg_data = _trim(data, "dte", dte_min, dte_max)

    # Calculate OTM percentage and filter
    leg_data = leg_data.pipe(_calculate_otm_pct).pipe(
        _trim,
        "otm_pct",
        lower=kwargs["max_otm_pct"] * -1,
        upper=kwargs["max_otm_pct"],
    )

    # Remove options with bid/ask below minimum
    leg_data = _remove_min_bid_ask(leg_data, kwargs["min_bid_ask"])

    return leg_data


def _get_strike_column(same_strike: bool, leg_num: int) -> str:
    """Return the appropriate strike column name based on spread type."""
    return "strike" if same_strike else f"strike_leg{leg_num}"


def _prepare_calendar_leg(
    options: pd.DataFrame, leg_num: int, same_strike: bool
) -> pd.DataFrame:
    """
    Rename columns for a calendar/diagonal spread leg.

    Args:
        options: DataFrame with option data for this leg
        leg_num: Leg number (1 for front, 2 for back)
        same_strike: True for calendar spreads, False for diagonal

    Returns:
        DataFrame with renamed columns
    """
    strike_col = _get_strike_column(same_strike, leg_num)
    price_col = "underlying_price_entry" if leg_num == 1 else "underlying_price_back"

    return options.rename(
        columns={
            "expiration": f"expiration_leg{leg_num}",
            "dte": f"dte_entry_leg{leg_num}",
            "strike": strike_col,
            "bid": f"bid_leg{leg_num}",
            "ask": f"ask_leg{leg_num}",
            "otm_pct": f"otm_pct_leg{leg_num}",
            "underlying_price": price_col,
        }
    )


def _get_calendar_leg_columns(leg_num: int, same_strike: bool) -> List[str]:
    """Return the columns needed for a calendar spread leg."""
    strike_col = _get_strike_column(same_strike, leg_num)
    cols = [
        "underlying_symbol",
        "quote_date",
        "option_type",
        f"expiration_leg{leg_num}",
        f"dte_entry_leg{leg_num}",
        f"bid_leg{leg_num}",
        f"ask_leg{leg_num}",
        f"otm_pct_leg{leg_num}",
    ]
    if leg_num == 1:
        cols.append("underlying_price_entry")
    cols.append(strike_col)
    return cols


def _merge_calendar_legs(
    front: pd.DataFrame, back: pd.DataFrame, same_strike: bool
) -> pd.DataFrame:
    """
    Merge front and back legs of a calendar/diagonal spread.

    Args:
        front: DataFrame with front leg data
        back: DataFrame with back leg data
        same_strike: True for calendar spreads, False for diagonal

    Returns:
        Merged DataFrame
    """
    join_cols = ["underlying_symbol", "quote_date", "option_type"]
    if same_strike:
        join_cols.append("strike")

    front_cols = _get_calendar_leg_columns(1, same_strike)
    back_cols = _get_calendar_leg_columns(2, same_strike)

    return pd.merge(front[front_cols], back[back_cols], on=join_cols, how="inner")


def _get_exit_leg_subset(
    exit_data: pd.DataFrame, leg_num: int, same_strike: bool
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Prepare exit data for joining with a specific leg.

    Args:
        exit_data: DataFrame with exit date prices
        leg_num: Leg number (1 or 2)
        same_strike: True for calendar spreads, False for diagonal

    Returns:
        Tuple of (subset DataFrame, join columns)
    """
    strike_col = _get_strike_column(same_strike, leg_num)

    renamed = exit_data.rename(
        columns={
            "quote_date": "exit_date",
            "expiration": f"expiration_leg{leg_num}",
            "bid": f"exit_bid_leg{leg_num}",
            "ask": f"exit_ask_leg{leg_num}",
        }
    )

    if not same_strike:
        renamed = renamed.rename(columns={"strike": strike_col})

    join_cols = [
        "underlying_symbol",
        "exit_date",
        "option_type",
        f"expiration_leg{leg_num}",
        strike_col,
    ]

    subset_cols = join_cols + [f"exit_bid_leg{leg_num}", f"exit_ask_leg{leg_num}"]

    return renamed[subset_cols], join_cols


def _find_calendar_exit_prices(
    merged: pd.DataFrame,
    data: pd.DataFrame,
    exit_dte: int,
    same_strike: bool,
    exit_dte_tolerance: int = 0,
) -> pd.DataFrame:
    """
    Find exit prices for calendar/diagonal spread positions.

    Args:
        merged: DataFrame with merged entry positions
        data: Original DataFrame with all option data (with DTE assigned)
        exit_dte: Days before front expiration to exit
        same_strike: True for calendar spreads, False for diagonal
        exit_dte_tolerance: Maximum days of deviation from target exit date (default 0)

    Returns:
        DataFrame with exit prices merged in, or empty DataFrame if no exit data
    """
    # Calculate exit date for each position.
    # Exit is timed relative to front leg (leg1) expiration, which is standard
    # calendar spread management: close before the short-dated option expires.
    # Both expiration and quote_date are already date-normalized at the root.
    merged["exit_date"] = merged["expiration_leg1"] - pd.Timedelta(days=exit_dte)

    all_exit_dates = merged["exit_date"].unique()

    if exit_dte_tolerance == 0:
        # Exact date matching (original behavior)
        exit_data = data[data["quote_date"].isin(all_exit_dates)]
    else:
        # Tolerance-based matching: snap each target exit_date to the
        # closest available quote_date within tolerance.
        tolerance_td = pd.Timedelta(days=exit_dte_tolerance)
        available_dates = np.sort(data["quote_date"].unique())

        date_map = {}
        for target_date in all_exit_dates:
            diffs = np.abs(available_dates - target_date)
            min_idx = diffs.argmin()
            if diffs[min_idx] <= tolerance_td:
                date_map[target_date] = available_dates[min_idx]

        if not date_map:
            return merged.iloc[:0]

        merged["exit_date"] = merged["exit_date"].map(lambda d: date_map.get(d, d))
        exit_data = data[data["quote_date"].isin(date_map.values())]

    if exit_data.empty:
        return merged.iloc[:0]

    # Merge exit prices for each leg
    for leg_num in [1, 2]:
        exit_subset, join_cols = _get_exit_leg_subset(exit_data, leg_num, same_strike)
        merged = pd.merge(merged, exit_subset, on=join_cols, how="inner")
        if merged.empty:
            return merged

    return merged


def _calculate_calendar_pnl(
    merged: pd.DataFrame,
    leg_def: List[Tuple],
    slippage: str = "mid",
    fill_ratio: float = 0.5,
    reference_volume: int = 1000,
) -> pd.DataFrame:
    """
    Calculate P&L for calendar/diagonal spread positions.

    Args:
        merged: DataFrame with entry and exit prices
        leg_def: List of tuples defining strategy legs
        slippage: Slippage mode - "mid", "spread", or "liquidity"
        fill_ratio: Base fill ratio for liquidity mode (0.0-1.0)
        reference_volume: Volume threshold for liquid options

    Returns:
        DataFrame with P&L columns added
    """
    front_side = leg_def[0][0].value
    back_side = leg_def[1][0].value

    # Calculate entry prices based on slippage model
    volume_leg1 = merged.get("volume_leg1") if "volume_leg1" in merged.columns else None
    volume_leg2 = merged.get("volume_leg2") if "volume_leg2" in merged.columns else None

    merged["entry_leg1"] = _calculate_fill_price(
        merged["bid_leg1"],
        merged["ask_leg1"],
        front_side,
        slippage,
        fill_ratio,
        volume_leg1,
        reference_volume,
    )
    merged["entry_leg2"] = _calculate_fill_price(
        merged["bid_leg2"],
        merged["ask_leg2"],
        back_side,
        slippage,
        fill_ratio,
        volume_leg2,
        reference_volume,
    )

    # Calculate exit prices (reverse sides for closing positions)
    # Note: Exit volume is not currently tracked for calendar spreads since exit
    # data comes from a different quote date. For liquidity mode, exits use
    # the base fill_ratio without volume adjustment.
    merged["exit_leg1"] = _calculate_fill_price(
        merged["exit_bid_leg1"],
        merged["exit_ask_leg1"],
        -front_side,
        slippage,
        fill_ratio,
        None,
        reference_volume,
    )
    merged["exit_leg2"] = _calculate_fill_price(
        merged["exit_bid_leg2"],
        merged["exit_ask_leg2"],
        -back_side,
        slippage,
        fill_ratio,
        None,
        reference_volume,
    )

    # Apply position multipliers based on leg definition
    front_multiplier = front_side
    back_multiplier = back_side

    merged["entry_leg1"] = merged["entry_leg1"] * front_multiplier
    merged["exit_leg1"] = merged["exit_leg1"] * front_multiplier
    merged["entry_leg2"] = merged["entry_leg2"] * back_multiplier
    merged["exit_leg2"] = merged["exit_leg2"] * back_multiplier

    # Calculate totals
    merged["total_entry_cost"] = merged["entry_leg1"] + merged["entry_leg2"]
    merged["total_exit_proceeds"] = merged["exit_leg1"] + merged["exit_leg2"]

    # Calculate percentage change.
    # Use a minimum threshold to avoid misleading percentages from near-zero entries.
    min_entry_threshold = 0.01
    merged["pct_change"] = np.where(
        merged["total_entry_cost"].abs() >= min_entry_threshold,
        (merged["total_exit_proceeds"] - merged["total_entry_cost"])
        / merged["total_entry_cost"].abs(),
        np.nan,
    )

    return merged


def _process_calendar_strategy(data: pd.DataFrame, **context: Any) -> pd.DataFrame:
    """
    Process calendar/diagonal spread strategies with different expirations.

    Calendar spreads have the same strike but different expirations.
    Diagonal spreads have different strikes and different expirations.

    Args:
        data: DataFrame containing raw option chain data
        **context: Dictionary containing strategy parameters, leg definitions, and formatting options

    Returns:
        DataFrame with processed calendar/diagonal strategy results
    """
    params = context["params"]
    _run_calendar_checks(params, data)

    leg_def = context["leg_def"]
    same_strike = context.get("same_strike", True)
    rules = context.get("rules")
    internal_cols = context["internal_cols"]
    external_cols = context["external_cols"]

    def _fmt(df: pd.DataFrame) -> pd.DataFrame:
        return _format_calendar_output(
            df, params, internal_cols, external_cols, same_strike
        )

    # Work with a copy and normalize dates/option_type once at the root
    data = data.copy()
    data["quote_date"] = normalize_dates(data["quote_date"])
    data["expiration"] = normalize_dates(data["expiration"])
    data["option_type"] = data["option_type"].str.lower()
    data = _assign_dte(data)

    # Get front and back leg options
    front_options = _evaluate_calendar_options(
        data,
        params["front_dte_min"],
        params["front_dte_max"],
        max_otm_pct=params["max_otm_pct"],
        min_bid_ask=params["min_bid_ask"],
    )

    back_options = _evaluate_calendar_options(
        data,
        params["back_dte_min"],
        params["back_dte_max"],
        max_otm_pct=params["max_otm_pct"],
        min_bid_ask=params["min_bid_ask"],
    )

    # Filter by option type (calls or puts) based on leg definition
    option_filter = leg_def[0][1]
    front_options = option_filter(front_options)
    back_options = option_filter(back_options)

    # Prepare and merge legs
    front_renamed = _prepare_calendar_leg(front_options, 1, same_strike)
    back_renamed = _prepare_calendar_leg(back_options, 2, same_strike)
    merged = _merge_calendar_legs(front_renamed, back_renamed, same_strike)

    # Apply expiration ordering rule
    if rules is not None:
        merged = rules(merged, leg_def)

    # Apply entry date filtering to calendar/diagonal spreads
    entry_dates = params.get("entry_dates")
    if entry_dates is not None and not merged.empty:
        merged = _apply_signal_filter(merged, entry_dates)

    if merged.empty:
        return _fmt(merged)

    # Find exit prices
    merged = _find_calendar_exit_prices(
        merged,
        data,
        params["exit_dte"],
        same_strike,
        params.get("exit_dte_tolerance", 0),
    )

    if merged.empty:
        return _fmt(merged)

    # Apply exit date filtering to calendar/diagonal spreads
    exit_dates = params.get("exit_dates")
    if exit_dates is not None and not merged.empty:
        merged = _apply_signal_filter(merged, exit_dates, date_col="exit_date")

    if merged.empty:
        return _fmt(merged)

    # Calculate P&L
    merged = _calculate_calendar_pnl(
        merged,
        leg_def,
        params.get("slippage", "mid"),
        params.get("fill_ratio", 0.5),
        params.get("reference_volume", 1000),
    )

    return _fmt(merged)


def _format_calendar_output(
    data: pd.DataFrame,
    params: Dict[str, Any],
    internal_cols: List[str],
    external_cols: List[str],
    same_strike: bool,
) -> pd.DataFrame:
    """
    Format calendar/diagonal strategy output as either raw data or grouped statistics.

    Args:
        data: DataFrame with strategy results
        params: Parameters including 'raw' and 'drop_nan' flags
        internal_cols: Columns to include in raw output
        external_cols: Columns to group by for statistics output
        same_strike: Whether this is a calendar spread (True) or diagonal spread (False)

    Returns:
        Formatted DataFrame with either raw data or descriptive statistics
    """
    if data.empty:
        if params["raw"]:
            return pd.DataFrame(columns=internal_cols)
        return pd.DataFrame(columns=external_cols + describe_cols)

    if params["raw"]:
        # Return only the columns that exist in the data
        available_cols = [c for c in internal_cols if c in data.columns]
        return data[available_cols].reset_index(drop=True)

    # Work with a copy to avoid modifying input
    data = data.copy()

    # For aggregated output, create DTE ranges and OTM ranges
    dte_interval = params["dte_interval"]

    # Create DTE ranges for both legs
    front_dte_intervals = list(
        range(0, params["front_dte_max"] + dte_interval, dte_interval)
    )
    back_dte_intervals = list(
        range(0, params["back_dte_max"] + dte_interval, dte_interval)
    )

    data["dte_range_leg1"] = pd.cut(data["dte_entry_leg1"], front_dte_intervals)
    data["dte_range_leg2"] = pd.cut(data["dte_entry_leg2"], back_dte_intervals)

    # Create OTM ranges
    otm_pct_interval = params["otm_pct_interval"]
    max_otm_pct = params["max_otm_pct"]
    otm_pct_intervals = [
        round(i, 2)
        for i in list(np.arange(max_otm_pct * -1, max_otm_pct, otm_pct_interval))
    ]

    if same_strike:
        data["otm_pct_range"] = pd.cut(data["otm_pct_leg1"], otm_pct_intervals)
    else:
        data["otm_pct_range_leg1"] = pd.cut(data["otm_pct_leg1"], otm_pct_intervals)
        data["otm_pct_range_leg2"] = pd.cut(data["otm_pct_leg2"], otm_pct_intervals)

    return data.pipe(
        _group_by_intervals, external_cols, params["drop_nan"]
    ).reset_index()


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
