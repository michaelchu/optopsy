# columns of options after evaluation
evaluated_cols = [
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

# columns of dataframe after generating strategy
single_strike_internal_cols = [
    "underlying_symbol",
    "expiration",
    "dte_entry",
    "dte_range",
    "otm_pct_range",
    "strike",
    "underlying_price_entry",
    "underlying_price_exit",
    "entry",
    "exit",
    "long_profit",
    "short_profit",
]

double_strike_internal_cols = [
    "underlying_symbol",
    "expiration",
    "dte_entry",
    "dte_range",
    "otm_pct_range_leg1",
    "strike_leg1",
    "otm_pct_range_leg2",
    "strike_leg2",
    "underlying_price_entry",
    "underlying_price_exit",
    "entry",
    "exit",
    "long_profit",
    "short_profit",
]

triple_strike_internal_cols = [
    "underlying_symbol",
    "expiration",
    "dte_entry",
    "dte_range",
    "leg1_otm_pct_range",
    "leg1_strike",
    "leg2_otm_pct_range",
    "leg2_strike",
    "leg3_otm_pct_range",
    "leg3_strike",
    "underlying_price_entry",
    "underlying_price_exit",
    "entry",
    "exit",
    "long_profit",
    "short_profit",
]

quadruple_strike_internal_cols = [
    "underlying_symbol",
    "expiration",
    "dte_entry",
    "dte_range",
    "leg1_otm_pct_range",
    "leg1_strike",
    "leg2_otm_pct_range",
    "leg2_strike",
    "leg3_otm_pct_range",
    "leg3_strike",
    "leg4_otm_pct_range",
    "leg4_strike",
    "underlying_price_entry",
    "underlying_price_exit",
    "entry",
    "exit",
    "long_profit",
    "short_profit",
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
