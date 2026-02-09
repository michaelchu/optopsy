"""Column definitions for strategy DataFrames at each pipeline stage.

The pipeline produces two kinds of output:

**Internal columns** (``*_internal_cols``)
    Used when ``raw=True``.  These are the trade-level columns that appear in
    the raw (unaggregated) output.  They contain per-position details such as
    individual leg strikes, entry/exit costs, and percentage change.

**External columns** (``*_external_cols``)
    Used when ``raw=False`` (default).  These are the grouping columns for
    the aggregated statistics output produced by ``pandas.DataFrame.describe()``.
    They define the DTE-range and OTM-percentage-range buckets that rows are
    grouped into.

Column sets are defined per leg count:

- ``single_strike_*``      — 1-leg strategies (long/short calls or puts).
- ``straddle_*``           — 2-leg same-strike (straddle) strategies.
- ``double_strike_*``      — 2-leg different-strike strategies (spreads, strangles).
- ``triple_strike_*``      — 3-leg strategies (butterflies).
- ``quadruple_strike_*``   — 4-leg strategies (iron condors, iron butterflies).
- ``calendar_spread_*``    — 2-leg same-strike, different-expiration strategies.
- ``diagonal_spread_*``    — 2-leg different-strike, different-expiration strategies.
"""

from typing import List

# Columns present after _evaluate_options() merges entry and exit quotes.
# These are the intermediate columns before legs are joined into strategies.
#   dte_entry        — days to expiration on the entry quote date
#   otm_pct_entry    — out-of-the-money percentage at entry: (strike - price) / strike
#   entry / exit     — fill prices (midpoint by default, adjusted by slippage model)
evaluated_cols: List[str] = [
    "underlying_symbol",
    "option_type",
    "expiration",
    "dte_entry",
    "strike",
    "otm_pct_entry",
    "underlying_price_entry",
    "underlying_price_exit",
    "bid_entry",
    "ask_entry",
    "bid_exit",
    "ask_exit",
    "entry",
    "exit",
]

# --- Raw output columns (trade-level, returned when raw=True) ---

# 1-leg strategies (long/short single calls or puts)
single_strike_internal_cols: List[str] = [
    "underlying_symbol",
    "underlying_price_entry",
    "option_type",
    "expiration",
    "dte_entry",
    "strike",
    "entry",
    "exit",
    "pct_change",
]


# 2-leg same-strike strategies (straddles: call + put at identical strike)
straddle_internal_cols: List[str] = [
    "underlying_symbol",
    "underlying_price_entry",
    "expiration",
    "dte_entry",
    "option_type_leg1",
    "option_type_leg2",
    "strike",
    "total_entry_cost",
    "total_exit_proceeds",
    "pct_change",
]


# 2-leg different-strike strategies (vertical spreads, strangles, covered calls)
double_strike_internal_cols: List[str] = [
    "underlying_symbol",
    "underlying_price_entry_leg1",
    "expiration",
    "dte_entry",
    "option_type_leg1",
    "strike_leg1",
    "option_type_leg2",
    "strike_leg2",
    "total_entry_cost",
    "total_exit_proceeds",
    "pct_change",
]

# 3-leg strategies (butterflies: two wings + body)
triple_strike_internal_cols: List[str] = [
    "underlying_symbol",
    "underlying_price_entry_leg1",
    "expiration",
    "dte_entry",
    "dte_range",
    "option_type_leg1",
    "strike_leg1",
    "option_type_leg2",
    "strike_leg2",
    "option_type_leg3",
    "strike_leg3",
    "total_entry_cost",
    "total_exit_proceeds",
    "pct_change",
]

# 4-leg strategies (iron condors, iron butterflies)
quadruple_strike_internal_cols: List[str] = [
    "underlying_symbol",
    "underlying_price_entry_leg1",
    "expiration",
    "dte_entry",
    "dte_range",
    "option_type_leg1",
    "strike_leg1",
    "option_type_leg2",
    "strike_leg2",
    "option_type_leg3",
    "strike_leg3",
    "option_type_leg4",
    "strike_leg4",
    "total_entry_cost",
    "total_exit_proceeds",
    "pct_change",
]

# --- Aggregated output grouping columns (returned when raw=False) ---
# These columns define the group-by keys for pandas describe() statistics.
# The describe_cols (count, mean, std, min, 25%, 50%, 75%, max) are appended
# automatically by _group_by_intervals().
single_strike_external_cols: List[str] = ["dte_range", "otm_pct_range"]
double_strike_external_cols: List[str] = [
    "dte_range",
    "otm_pct_range_leg1",
    "otm_pct_range_leg2",
]
triple_strike_external_cols: List[str] = [
    "dte_range",
    "otm_pct_range_leg1",
    "otm_pct_range_leg2",
    "otm_pct_range_leg3",
]
quadruple_strike_external_cols: List[str] = [
    "dte_range",
    "otm_pct_range_leg1",
    "otm_pct_range_leg2",
    "otm_pct_range_leg3",
    "otm_pct_range_leg4",
]

# Calendar spread columns (same strike, different expirations)
calendar_spread_internal_cols: List[str] = [
    "underlying_symbol",
    "underlying_price_entry",
    "option_type",
    "strike",
    "expiration_leg1",
    "expiration_leg2",
    "dte_entry_leg1",
    "dte_entry_leg2",
    "entry_leg1",
    "exit_leg1",
    "entry_leg2",
    "exit_leg2",
    "total_entry_cost",
    "total_exit_proceeds",
    "pct_change",
]

calendar_spread_external_cols: List[str] = [
    "dte_range_leg1",
    "dte_range_leg2",
    "otm_pct_range",
]

# Diagonal spread columns (different strikes, different expirations)
diagonal_spread_internal_cols: List[str] = [
    "underlying_symbol",
    "underlying_price_entry",
    "option_type",
    "strike_leg1",
    "strike_leg2",
    "expiration_leg1",
    "expiration_leg2",
    "dte_entry_leg1",
    "dte_entry_leg2",
    "entry_leg1",
    "exit_leg1",
    "entry_leg2",
    "exit_leg2",
    "total_entry_cost",
    "total_exit_proceeds",
    "pct_change",
]

diagonal_spread_external_cols: List[str] = [
    "dte_range_leg1",
    "dte_range_leg2",
    "otm_pct_range_leg1",
    "otm_pct_range_leg2",
]

# Columns added by pandas describe() for aggregated statistics output
describe_cols: List[str] = ["count", "mean", "std", "min", "25%", "50%", "75%", "max"]
