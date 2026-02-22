"""
Column Definitions for Strategy Output

This module defines the column structures for different strategy types:
- Single-leg strategies (calls, puts)
- Double-leg strategies (spreads, straddles, strangles)
- Triple-leg strategies (butterflies)
- Quadruple-leg strategies (iron condors, iron butterflies)
- Calendar and diagonal spreads (different expirations)

Each strategy has internal columns (raw trade data) and external columns
(for aggregated statistics output).
"""

from typing import List

# columns of options after evaluation
evaluated_cols: List[str] = [
    "underlying_symbol",
    "option_type",
    "expiration",
    "quote_date_entry",
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

# columns of dataframe after generating strategy
single_strike_internal_cols: List[str] = [
    "underlying_symbol",
    "underlying_price_entry",
    "quote_date_entry",
    "option_type",
    "expiration",
    "dte_entry",
    "strike",
    "entry",
    "exit",
    "pct_change",
]


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

# base columns of dataframe after aggregation(minus the calculated columns)
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

# Columns added by pandas describe() plus risk metrics for aggregated statistics output
describe_cols: List[str] = [
    "count",
    "mean",
    "std",
    "min",
    "25%",
    "50%",
    "75%",
    "max",
    "win_rate",
    "profit_factor",
]
