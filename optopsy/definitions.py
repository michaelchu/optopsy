# columns of options after evaluation
evaluated_cols = [
    "underlying_symbol",
    "option_type",
    "expiration",
    "dte_entry",
    "strike",
    "otm_pct_entry",
    "underlying_price_entry",
    "underlying_price_exit",
    "entry",
    "exit",
]

# columns of dataframe after generating strategy
single_strike_internal_cols = [
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


straddle_internal_cols = [
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


double_strike_internal_cols = [
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

triple_strike_internal_cols = [
    "underlying_symbol",
    "underlying_price_entry",
    "expiration",
    "dte_entry",
    "option_type_leg1",
    "strike_leg1",
    "option_type_leg2",
    "strike_leg2",
    "option_type_leg3",
    "strike_leg3",
    "entry",
    "exit",
    "long_profit",
    "short_profit",
    "long_pct_change",
    "short_pct_change",
]

quadruple_strike_internal_cols = [
    "underlying_symbol",
    "underlying_price_entry",
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
    "entry",
    "exit",
    "long_profit",
    "short_profit",
    "long_pct_change",
    "short_pct_change",
]

# base columns of dataframe after aggregation(minus the calculated columns)
single_strike_external_cols = ["dte_range", "otm_pct_range"]
double_strike_external_cols = ["dte_range", "otm_pct_range_leg1", "otm_pct_range_leg2"]
triple_strike_external_cols = [
    "dte_range",
    "otm_pct_range_leg1",
    "otm_pct_range_leg2",
    "otm_pct_range_leg3",
]
quadruple_strike_external_cols = [
    "dte_range",
    "otm_pct_range_leg1",
    "otm_pct_range_leg2",
    "otm_pct_range_leg3",
    "otm_pct_range_leg4",
]
