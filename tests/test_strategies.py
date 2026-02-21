import numpy as np
import pandas as pd
import pytest

from optopsy.definitions import (
    calendar_spread_external_cols,
    calendar_spread_internal_cols,
    diagonal_spread_external_cols,
    diagonal_spread_internal_cols,
    double_strike_external_cols,
    double_strike_internal_cols,
    quadruple_strike_external_cols,
    quadruple_strike_internal_cols,
    single_strike_external_cols,
    single_strike_internal_cols,
    straddle_internal_cols,
    triple_strike_external_cols,
    triple_strike_internal_cols,
)
from optopsy.strategies import (
    covered_call,
    iron_butterfly,
    iron_condor,
    long_call_butterfly,
    long_call_calendar,
    long_call_diagonal,
    long_call_spread,
    long_calls,
    long_put_butterfly,
    long_put_calendar,
    long_put_diagonal,
    long_put_spread,
    long_puts,
    long_straddles,
    long_strangles,
    protective_put,
    reverse_iron_butterfly,
    reverse_iron_condor,
    short_call_butterfly,
    short_call_calendar,
    short_call_diagonal,
    short_call_spread,
    short_calls,
    short_put_butterfly,
    short_put_calendar,
    short_put_diagonal,
    short_put_spread,
    short_puts,
    short_straddles,
    short_strangles,
)

describe_cols = [
    "count",
    "mean",
    "std",
    "min",
    "25%",
    "50%",
    "75%",
    "max",
]


# =============================================================================
# Butterfly Strategy Tests
# =============================================================================


def test_long_call_butterfly_raw(multi_strike_data):
    """Test long call butterfly returns correct structure and calculated values."""
    results = long_call_butterfly(multi_strike_data, raw=True)
    assert list(results.columns) == triple_strike_internal_cols
    # All legs should be calls
    assert results.iloc[0]["option_type_leg1"] == "call"
    assert results.iloc[0]["option_type_leg2"] == "call"
    assert results.iloc[0]["option_type_leg3"] == "call"
    # Strikes should be in ascending order with equal width
    assert results.iloc[0]["strike_leg1"] < results.iloc[0]["strike_leg2"]
    assert results.iloc[0]["strike_leg2"] < results.iloc[0]["strike_leg3"]
    # Check calculated values for butterfly at strikes 210, 212.5, 215
    # Entry: long 210 call (4.95) + short 2x 212.5 calls (-3.05*2=-6.10) + long 215 call (1.55) = 0.40
    # Exit: 5.00 + (-5.00) + 0.05 = 0.05
    row = results[
        (results["strike_leg1"] == 210.0)
        & (results["strike_leg2"] == 212.5)
        & (results["strike_leg3"] == 215.0)
    ].iloc[0]
    assert round(row["total_entry_cost"], 2) == 0.40
    assert round(row["total_exit_proceeds"], 2) == 0.05
    assert round(row["pct_change"], 2) == -0.88


def test_long_call_butterfly(multi_strike_data):
    """Test long call butterfly aggregated output."""
    results = long_call_butterfly(multi_strike_data)
    assert list(results.columns) == triple_strike_external_cols + describe_cols


def test_short_call_butterfly_raw(multi_strike_data):
    """Test short call butterfly returns correct structure."""
    results = short_call_butterfly(multi_strike_data, raw=True)
    assert list(results.columns) == triple_strike_internal_cols
    assert results.iloc[0]["option_type_leg1"] == "call"
    assert results.iloc[0]["option_type_leg2"] == "call"
    assert results.iloc[0]["option_type_leg3"] == "call"


def test_long_put_butterfly_raw(multi_strike_data):
    """Test long put butterfly returns correct structure and calculated values."""
    results = long_put_butterfly(multi_strike_data, raw=True)
    assert list(results.columns) == triple_strike_internal_cols
    # All legs should be puts
    assert results.iloc[0]["option_type_leg1"] == "put"
    assert results.iloc[0]["option_type_leg2"] == "put"
    assert results.iloc[0]["option_type_leg3"] == "put"
    # Check calculated values for butterfly at strikes 210, 212.5, 215
    # All puts expired worthless since underlying at 215
    row = results[
        (results["strike_leg1"] == 210.0)
        & (results["strike_leg2"] == 212.5)
        & (results["strike_leg3"] == 215.0)
    ].iloc[0]
    # Entry: long 210 put (1.45) + short 2x 212.5 puts (2 * -3.05 = -6.10) + long 215 put (5.05) = 0.40
    assert round(row["total_entry_cost"], 2) == 0.40
    # Exit: all puts worthless = 0.025 + (-0.05) + 0.025 = 0.0
    assert round(row["total_exit_proceeds"], 2) == 0.0
    assert round(row["pct_change"], 2) == -1.0


def test_long_put_butterfly(multi_strike_data):
    """Test long put butterfly aggregated output."""
    results = long_put_butterfly(multi_strike_data)
    assert list(results.columns) == triple_strike_external_cols + describe_cols


def test_short_put_butterfly_raw(multi_strike_data):
    """Test short put butterfly returns correct structure."""
    results = short_put_butterfly(multi_strike_data, raw=True)
    assert list(results.columns) == triple_strike_internal_cols
    assert results.iloc[0]["option_type_leg1"] == "put"
    assert results.iloc[0]["option_type_leg2"] == "put"
    assert results.iloc[0]["option_type_leg3"] == "put"


# =============================================================================
# Iron Condor Strategy Tests
# =============================================================================


def test_iron_condor_raw(multi_strike_data):
    """Test iron condor returns correct structure and calculated values."""
    results = iron_condor(multi_strike_data, raw=True)
    assert list(results.columns) == quadruple_strike_internal_cols
    # Leg 1 and 2 should be puts, leg 3 and 4 should be calls
    assert results.iloc[0]["option_type_leg1"] == "put"
    assert results.iloc[0]["option_type_leg2"] == "put"
    assert results.iloc[0]["option_type_leg3"] == "call"
    assert results.iloc[0]["option_type_leg4"] == "call"
    # Strikes should be in ascending order
    assert results.iloc[0]["strike_leg1"] < results.iloc[0]["strike_leg2"]
    assert results.iloc[0]["strike_leg2"] < results.iloc[0]["strike_leg3"]
    assert results.iloc[0]["strike_leg3"] < results.iloc[0]["strike_leg4"]
    # Check calculated values for iron condor at strikes 207.5, 210, 215, 217.5
    # Underlying moved from 212.5 to 215, staying within the condor range
    row = results[
        (results["strike_leg1"] == 207.5)
        & (results["strike_leg2"] == 210.0)
        & (results["strike_leg3"] == 215.0)
        & (results["strike_leg4"] == 217.5)
    ].iloc[0]
    # Net credit received at entry (negative cost = credit)
    assert round(row["total_entry_cost"], 2) == -1.90
    # Nearly all options expired worthless, kept most of premium
    assert round(row["total_exit_proceeds"], 3) == -0.025
    assert round(row["pct_change"], 2) == 0.99


def test_iron_condor(multi_strike_data):
    """Test iron condor aggregated output."""
    results = iron_condor(multi_strike_data)
    assert list(results.columns) == quadruple_strike_external_cols + describe_cols


def test_reverse_iron_condor_raw(multi_strike_data):
    """Test reverse iron condor returns correct structure."""
    results = reverse_iron_condor(multi_strike_data, raw=True)
    assert list(results.columns) == quadruple_strike_internal_cols
    assert results.iloc[0]["option_type_leg1"] == "put"
    assert results.iloc[0]["option_type_leg2"] == "put"
    assert results.iloc[0]["option_type_leg3"] == "call"
    assert results.iloc[0]["option_type_leg4"] == "call"


# =============================================================================
# Iron Butterfly Strategy Tests
# =============================================================================


def test_iron_butterfly_raw(multi_strike_data):
    """Test iron butterfly returns correct structure and calculated values."""
    results = iron_butterfly(multi_strike_data, raw=True)
    assert list(results.columns) == quadruple_strike_internal_cols
    # Leg 1 and 2 should be puts, leg 3 and 4 should be calls
    assert results.iloc[0]["option_type_leg1"] == "put"
    assert results.iloc[0]["option_type_leg2"] == "put"
    assert results.iloc[0]["option_type_leg3"] == "call"
    assert results.iloc[0]["option_type_leg4"] == "call"
    # Middle legs should share the same strike
    assert results.iloc[0]["strike_leg2"] == results.iloc[0]["strike_leg3"]
    # Check calculated values for iron butterfly at strikes 207.5, 212.5, 212.5, 217.5
    # Middle strike at 212.5 (ATM), wings at 207.5 and 217.5
    row = results[
        (results["strike_leg1"] == 207.5)
        & (results["strike_leg2"] == 212.5)
        & (results["strike_leg3"] == 212.5)
        & (results["strike_leg4"] == 217.5)
    ].iloc[0]
    # Net credit received at entry
    assert round(row["total_entry_cost"], 2) == -5.00
    # Underlying moved to 215, short straddle lost value
    assert round(row["total_exit_proceeds"], 3) == -2.475
    assert round(row["pct_change"], 2) == 0.50


def test_iron_butterfly(multi_strike_data):
    """Test iron butterfly aggregated output."""
    results = iron_butterfly(multi_strike_data)
    assert list(results.columns) == quadruple_strike_external_cols + describe_cols


def test_reverse_iron_butterfly_raw(multi_strike_data):
    """Test reverse iron butterfly returns correct structure."""
    results = reverse_iron_butterfly(multi_strike_data, raw=True)
    assert list(results.columns) == quadruple_strike_internal_cols
    assert results.iloc[0]["option_type_leg1"] == "put"
    assert results.iloc[0]["option_type_leg2"] == "put"
    assert results.iloc[0]["option_type_leg3"] == "call"
    assert results.iloc[0]["option_type_leg4"] == "call"
    # Middle legs should share the same strike
    assert results.iloc[0]["strike_leg2"] == results.iloc[0]["strike_leg3"]


# =============================================================================
# Covered Strategy Tests
# =============================================================================


def test_covered_call_raw(multi_strike_data):
    """Test covered call returns correct structure and calculated values."""
    results = covered_call(multi_strike_data, raw=True)
    assert list(results.columns) == double_strike_internal_cols
    # Both legs should be calls
    assert results.iloc[0]["option_type_leg1"] == "call"
    assert results.iloc[0]["option_type_leg2"] == "call"
    # Check calculated values for covered call at strikes 212.5, 215
    # Long deep ITM call (synthetic stock) + short OTM call
    row = results[
        (results["strike_leg1"] == 212.5) & (results["strike_leg2"] == 215.0)
    ].iloc[0]
    # Entry: long 212.5 call (3.05) + short 215 call (-1.55) = 1.50
    assert round(row["total_entry_cost"], 2) == 1.50
    # Exit: long call worth 2.50 + short call expired worthless (-0.05) = 2.45
    assert round(row["total_exit_proceeds"], 2) == 2.45
    assert round(row["pct_change"], 2) == 0.63


def test_covered_call(multi_strike_data):
    """Test covered call aggregated output."""
    results = covered_call(multi_strike_data)
    assert list(results.columns) == double_strike_external_cols + describe_cols


def test_protective_put_raw(multi_strike_data):
    """Test protective put returns correct structure and calculated values."""
    results = protective_put(multi_strike_data, raw=True)
    assert list(results.columns) == double_strike_internal_cols
    # Leg 1 should be call (synthetic stock), leg 2 should be put
    assert results.iloc[0]["option_type_leg1"] == "call"
    assert results.iloc[0]["option_type_leg2"] == "put"
    # Check calculated values for protective put at strikes 207.5, 210
    # Long call (synthetic stock) + long put for protection
    # Note: strike_leg1 < strike_leg2 due to non-overlapping rule
    row = results[
        (results["strike_leg1"] == 207.5) & (results["strike_leg2"] == 210.0)
    ].iloc[0]
    # Entry: long 207.5 call (6.95) + long 210 put (1.45) = 8.40
    assert round(row["total_entry_cost"], 2) == 8.40
    # Exit: call worth 7.50 + put expired worthless (0.025) = 7.525
    assert round(row["total_exit_proceeds"], 3) == 7.525
    # Small loss due to time decay
    assert round(row["pct_change"], 2) == -0.10


def test_protective_put(multi_strike_data):
    """Test protective put aggregated output."""
    results = protective_put(multi_strike_data)
    assert list(results.columns) == double_strike_external_cols + describe_cols


def test_single_long_calls_raw(data):
    results = long_calls(data, raw=True)
    assert len(results) == 2
    assert list(results.columns) == single_strike_internal_cols
    assert "call" in list(results["option_type"].values)
    assert round(results.iloc[0]["pct_change"], 2) == 0.01
    assert round(results.iloc[1]["pct_change"], 2) == -0.17


def test_single_long_puts_raw(data):
    results = long_puts(data, raw=True)
    assert len(results) == 2
    assert list(results.columns) == single_strike_internal_cols
    assert "put" in list(results["option_type"].values)
    assert round(results.iloc[0]["pct_change"], 2) == -1
    assert round(results.iloc[1]["pct_change"], 2) == -1


def test_single_short_calls_raw(data):
    results = short_calls(data, raw=True)
    assert len(results) == 2
    assert list(results.columns) == single_strike_internal_cols
    assert "call" in list(results["option_type"].values)
    assert round(results.iloc[0]["pct_change"], 2) == 0.01
    assert round(results.iloc[1]["pct_change"], 2) == -0.17


def test_single_short_puts_raw(data):
    results = short_puts(data, raw=True)
    assert len(results) == 2
    assert list(results.columns) == single_strike_internal_cols
    assert "put" in list(results["option_type"].values)
    assert round(results.iloc[0]["pct_change"], 2) == -1
    assert round(results.iloc[1]["pct_change"], 2) == -1


def test_singles_long_calls(data):
    results = long_calls(data)
    assert len(results) == 1
    assert results.iloc[0]["count"] == 2.0
    assert round(results.iloc[0]["mean"], 2) == -0.08
    assert list(results.columns) == single_strike_external_cols + describe_cols


def test_singles_long_puts(data):
    results = long_puts(data)
    assert len(results) == 1
    assert results.iloc[0]["count"] == 2.0
    assert round(results.iloc[0]["mean"], 2) == -1.0
    assert list(results.columns) == single_strike_external_cols + describe_cols


def test_singles_short_calls(data):
    results = short_calls(data)
    assert len(results) == 1
    assert results.iloc[0]["count"] == 2.0
    assert round(results.iloc[0]["mean"], 2) == -0.08
    assert list(results.columns) == single_strike_external_cols + describe_cols


def test_singles_short_puts(data):
    results = short_puts(data)
    assert len(results) == 1
    assert results.iloc[0]["count"] == 2.0
    assert round(results.iloc[0]["mean"], 2) == -1.0
    assert list(results.columns) == single_strike_external_cols + describe_cols


def test_straddles_long_raw(data):
    results = long_straddles(data, raw=True)
    assert list(results.columns) == straddle_internal_cols
    assert results.iloc[0]["option_type_leg1"] == "put"
    assert results.iloc[0]["option_type_leg2"] == "call"
    assert round(results.iloc[0]["pct_change"], 2) == -0.43
    assert round(results.iloc[1]["pct_change"], 2) == -0.62


def test_straddles_short_raw(data):
    results = short_straddles(data, raw=True)
    assert list(results.columns) == straddle_internal_cols
    assert results.iloc[0]["option_type_leg1"] == "put"
    assert results.iloc[0]["option_type_leg2"] == "call"
    assert round(results.iloc[0]["pct_change"], 2) == 0.43
    assert round(results.iloc[1]["pct_change"], 2) == 0.62


def test_long_straddles(data):
    results = long_straddles(data)
    assert len(results) == 1
    assert results.iloc[0]["count"] == 2.0
    assert round(results.iloc[0]["mean"], 2) == -0.52
    assert list(results.columns) == single_strike_external_cols + describe_cols


def test_short_straddles(data):
    results = short_straddles(data)
    assert len(results) == 1
    assert results.iloc[0]["count"] == 2.0
    assert round(results.iloc[0]["mean"], 2) == 0.52
    assert list(results.columns) == single_strike_external_cols + describe_cols


def test_strangles_long_raw(data):
    results = long_strangles(data, raw=True)
    assert len(results) == 1
    assert list(results.columns) == double_strike_internal_cols
    assert results.iloc[0]["option_type_leg1"] == "put"
    assert results.iloc[0]["option_type_leg2"] == "call"
    assert round(results.iloc[0]["pct_change"], 2) == -0.57


def test_strangles_short_raw(data):
    results = short_strangles(data, raw=True)
    assert len(results) == 1
    assert list(results.columns) == double_strike_internal_cols
    assert results.iloc[0]["option_type_leg1"] == "put"
    assert results.iloc[0]["option_type_leg2"] == "call"
    assert round(results.iloc[0]["pct_change"], 2) == 0.57


def test_long_strangles(data):
    results = long_strangles(data)
    assert len(results) == 1
    assert results.iloc[0]["count"] == 1.0
    assert round(results.iloc[0]["mean"], 2) == -0.57
    assert list(results.columns) == double_strike_external_cols + describe_cols


def test_short_strangles(data):
    results = short_strangles(data)
    assert len(results) == 1
    assert results.iloc[0]["count"] == 1.0
    assert round(results.iloc[0]["mean"], 2) == 0.57
    assert list(results.columns) == double_strike_external_cols + describe_cols


def test_long_call_spread_raw(data):
    results = long_call_spread(data, raw=True)
    assert len(results) == 1
    assert list(results.columns) == double_strike_internal_cols
    assert results.iloc[0]["option_type_leg1"] == "call"
    assert results.iloc[0]["option_type_leg2"] == "call"
    assert round(results.iloc[0]["pct_change"], 2) == 0.81


def test_long_put_spread_raw(data):
    results = long_put_spread(data, raw=True)
    assert len(results) == 1
    assert list(results.columns) == double_strike_internal_cols
    assert results.iloc[0]["option_type_leg1"] == "put"
    assert results.iloc[0]["option_type_leg2"] == "put"
    assert round(results.iloc[0]["pct_change"], 2) == -1


def test_short_call_spread_raw(data):
    results = short_call_spread(data, raw=True)
    assert len(results) == 1
    assert list(results.columns) == double_strike_internal_cols
    assert results.iloc[0]["option_type_leg1"] == "call"
    assert results.iloc[0]["option_type_leg2"] == "call"
    assert round(results.iloc[0]["pct_change"], 2) == -0.81


def test_short_put_spread_raw(data):
    results = short_put_spread(data, raw=True)
    assert len(results) == 1
    assert list(results.columns) == double_strike_internal_cols
    assert results.iloc[0]["option_type_leg1"] == "put"
    assert results.iloc[0]["option_type_leg2"] == "put"
    assert round(results.iloc[0]["pct_change"], 2) == 1


# =============================================================================
# Greeks (Delta) Filtering and Grouping Tests
# =============================================================================


def test_long_calls_with_delta_filter(data_with_delta):
    """Test that delta filtering works - only include calls with delta >= 0.40."""
    results = long_calls(data_with_delta, raw=True, delta_min=0.40)
    # Only calls with delta >= 0.40 should be included (0.60 and 0.45)
    assert len(results) == 2
    assert "call" in list(results["option_type"].values)


def test_long_calls_with_delta_range(data_with_delta):
    """Test that delta range filtering works - include calls with 0.30 <= delta <= 0.50."""
    results = long_calls(data_with_delta, raw=True, delta_min=0.30, delta_max=0.50)
    # Only calls with 0.30 <= delta <= 0.50 should be included (0.45 and 0.30)
    assert len(results) == 2


def test_long_puts_with_delta_filter(data_with_delta):
    """Test that delta filtering works for puts - only include puts with delta <= -0.50."""
    results = long_puts(data_with_delta, raw=True, delta_max=-0.50)
    # Only puts with delta <= -0.50 should be included (-0.55 and -0.70)
    assert len(results) == 2
    assert "put" in list(results["option_type"].values)


def test_long_calls_with_delta_grouping(data_with_delta):
    """Test that delta grouping adds delta_range to output columns."""
    results = long_calls(data_with_delta, delta_interval=0.10)
    # Should have delta_range as first column in grouped output
    assert "delta_range" in results.columns
    # delta_range should be first column before other external cols
    assert list(results.columns)[0] == "delta_range"


def test_delta_filter_no_delta_column_raises(data):
    """Test that using delta filter on data without delta column raises error."""
    with pytest.raises(ValueError, match="Greek column 'delta' not found"):
        long_calls(data, delta_min=0.30)


# =============================================================================
# Calendar Spread Strategy Tests
# =============================================================================


def test_long_call_calendar_raw(calendar_data):
    """Test long call calendar returns correct structure and calculated values."""
    results = long_call_calendar(
        calendar_data,
        raw=True,
        front_dte_min=20,
        front_dte_max=40,
        back_dte_min=50,
        back_dte_max=70,
        exit_dte=7,
    )
    assert list(results.columns) == calendar_spread_internal_cols
    # All legs should be calls
    assert results.iloc[0]["option_type"] == "call"
    # Same strike for both legs (calendar spread)
    assert "strike" in results.columns
    # Front expiration should be before back expiration
    assert results.iloc[0]["expiration_leg1"] < results.iloc[0]["expiration_leg2"]

    # Check calculated values for calendar at strike 212.5
    # Entry: short front call (-2.95) + long back call (4.95) = 2.00 (net debit)
    # Exit: close short front (-3.05) + close long back (5.05) = 2.00
    row = results[results["strike"] == 212.5].iloc[0]
    assert round(row["total_entry_cost"], 2) == 2.00
    assert round(row["total_exit_proceeds"], 2) == 2.00
    assert round(row["pct_change"], 2) == 0.0


def test_long_call_calendar(calendar_data):
    """Test long call calendar aggregated output."""
    results = long_call_calendar(
        calendar_data,
        front_dte_min=20,
        front_dte_max=40,
        back_dte_min=50,
        back_dte_max=70,
        exit_dte=7,
    )
    assert list(results.columns) == calendar_spread_external_cols + describe_cols


def test_short_call_calendar_raw(calendar_data):
    """Test short call calendar returns correct structure."""
    results = short_call_calendar(
        calendar_data,
        raw=True,
        front_dte_min=20,
        front_dte_max=40,
        back_dte_min=50,
        back_dte_max=70,
        exit_dte=7,
    )
    assert list(results.columns) == calendar_spread_internal_cols
    assert results.iloc[0]["option_type"] == "call"

    # For short calendar, entry/exit signs are opposite
    # Entry: long front call (2.95) + short back call (-4.95) = -2.00 (net credit)
    # Exit: close long front (3.05) + close short back (-5.05) = -2.00
    row = results[results["strike"] == 212.5].iloc[0]
    assert round(row["total_entry_cost"], 2) == -2.00
    assert round(row["total_exit_proceeds"], 2) == -2.00
    assert round(row["pct_change"], 2) == 0.0


def test_long_put_calendar_raw(calendar_data):
    """Test long put calendar returns correct structure and calculated values."""
    results = long_put_calendar(
        calendar_data,
        raw=True,
        front_dte_min=20,
        front_dte_max=40,
        back_dte_min=50,
        back_dte_max=70,
        exit_dte=7,
    )
    assert list(results.columns) == calendar_spread_internal_cols
    assert results.iloc[0]["option_type"] == "put"
    assert results.iloc[0]["expiration_leg1"] < results.iloc[0]["expiration_leg2"]

    # Check calculated values for put calendar at strike 212.5
    # Entry: short front put (-2.95) + long back put (4.95) = 2.00 (net debit)
    # Exit: close short front (-0.35) + close long back (2.55) = 2.20
    row = results[results["strike"] == 212.5].iloc[0]
    assert round(row["total_entry_cost"], 2) == 2.00
    assert round(row["total_exit_proceeds"], 2) == 2.20
    assert round(row["pct_change"], 2) == 0.10


def test_long_put_calendar(calendar_data):
    """Test long put calendar aggregated output."""
    results = long_put_calendar(
        calendar_data,
        front_dte_min=20,
        front_dte_max=40,
        back_dte_min=50,
        back_dte_max=70,
        exit_dte=7,
    )
    assert list(results.columns) == calendar_spread_external_cols + describe_cols


def test_short_put_calendar_raw(calendar_data):
    """Test short put calendar returns correct structure."""
    results = short_put_calendar(
        calendar_data,
        raw=True,
        front_dte_min=20,
        front_dte_max=40,
        back_dte_min=50,
        back_dte_max=70,
        exit_dte=7,
    )
    assert list(results.columns) == calendar_spread_internal_cols
    assert results.iloc[0]["option_type"] == "put"


# =============================================================================
# Diagonal Spread Strategy Tests
# =============================================================================


def test_long_call_diagonal_raw(calendar_data):
    """Test long call diagonal returns correct structure and calculated values."""
    results = long_call_diagonal(
        calendar_data,
        raw=True,
        front_dte_min=20,
        front_dte_max=40,
        back_dte_min=50,
        back_dte_max=70,
        exit_dte=7,
    )
    assert list(results.columns) == diagonal_spread_internal_cols
    assert results.iloc[0]["option_type"] == "call"
    # Different strikes for diagonal spread
    assert "strike_leg1" in results.columns
    assert "strike_leg2" in results.columns
    # Front expiration should be before back expiration
    assert results.iloc[0]["expiration_leg1"] < results.iloc[0]["expiration_leg2"]


def test_long_call_diagonal(calendar_data):
    """Test long call diagonal aggregated output."""
    results = long_call_diagonal(
        calendar_data,
        front_dte_min=20,
        front_dte_max=40,
        back_dte_min=50,
        back_dte_max=70,
        exit_dte=7,
    )
    assert list(results.columns) == diagonal_spread_external_cols + describe_cols


def test_short_call_diagonal_raw(calendar_data):
    """Test short call diagonal returns correct structure."""
    results = short_call_diagonal(
        calendar_data,
        raw=True,
        front_dte_min=20,
        front_dte_max=40,
        back_dte_min=50,
        back_dte_max=70,
        exit_dte=7,
    )
    assert list(results.columns) == diagonal_spread_internal_cols
    assert results.iloc[0]["option_type"] == "call"


def test_long_put_diagonal_raw(calendar_data):
    """Test long put diagonal returns correct structure."""
    results = long_put_diagonal(
        calendar_data,
        raw=True,
        front_dte_min=20,
        front_dte_max=40,
        back_dte_min=50,
        back_dte_max=70,
        exit_dte=7,
    )
    assert list(results.columns) == diagonal_spread_internal_cols
    assert results.iloc[0]["option_type"] == "put"


def test_long_put_diagonal(calendar_data):
    """Test long put diagonal aggregated output."""
    results = long_put_diagonal(
        calendar_data,
        front_dte_min=20,
        front_dte_max=40,
        back_dte_min=50,
        back_dte_max=70,
        exit_dte=7,
    )
    assert list(results.columns) == diagonal_spread_external_cols + describe_cols


def test_short_put_diagonal_raw(calendar_data):
    """Test short put diagonal returns correct structure."""
    results = short_put_diagonal(
        calendar_data,
        raw=True,
        front_dte_min=20,
        front_dte_max=40,
        back_dte_min=50,
        back_dte_max=70,
        exit_dte=7,
    )
    assert list(results.columns) == diagonal_spread_internal_cols
    assert results.iloc[0]["option_type"] == "put"


def test_calendar_expiration_ordering(calendar_data):
    """Test that calendar spreads enforce front < back expiration."""
    results = long_call_calendar(
        calendar_data,
        raw=True,
        front_dte_min=20,
        front_dte_max=40,
        back_dte_min=50,
        back_dte_max=70,
        exit_dte=7,
    )
    # All results should have front expiration before back expiration
    for _, row in results.iterrows():
        assert row["expiration_leg1"] < row["expiration_leg2"]


def test_diagonal_expiration_ordering(calendar_data):
    """Test that diagonal spreads enforce front < back expiration."""
    results = long_call_diagonal(
        calendar_data,
        raw=True,
        front_dte_min=20,
        front_dte_max=40,
        back_dte_min=50,
        back_dte_max=70,
        exit_dte=7,
    )
    # All results should have front expiration before back expiration
    for _, row in results.iterrows():
        assert row["expiration_leg1"] < row["expiration_leg2"]


def test_calendar_no_matching_expirations(data):
    """Test that calendar returns empty when no matching expirations exist."""
    # The basic 'data' fixture only has one expiration date
    results = long_call_calendar(
        data,
        raw=True,
        front_dte_min=20,
        front_dte_max=40,
        back_dte_min=50,
        back_dte_max=70,
        exit_dte=7,
    )
    # Should return empty DataFrame with correct columns
    assert len(results) == 0
    assert list(results.columns) == calendar_spread_internal_cols


def test_calendar_invalid_front_dte_range(calendar_data):
    """Test that calendar raises error when front_dte_min > front_dte_max."""
    with pytest.raises(ValueError, match="front_dte_min.*must be <=.*front_dte_max"):
        long_call_calendar(
            calendar_data,
            raw=True,
            front_dte_min=50,
            front_dte_max=20,
            back_dte_min=60,
            back_dte_max=90,
        )


def test_calendar_invalid_back_dte_range(calendar_data):
    """Test that calendar raises error when back_dte_min > back_dte_max."""
    with pytest.raises(ValueError, match="back_dte_min.*must be <=.*back_dte_max"):
        long_call_calendar(
            calendar_data,
            raw=True,
            front_dte_min=20,
            front_dte_max=40,
            back_dte_min=90,
            back_dte_max=60,
        )


def test_calendar_overlapping_dte_ranges(calendar_data):
    """Test that calendar raises error when front and back DTE ranges overlap."""
    with pytest.raises(ValueError, match="front_dte_max.*must be <.*back_dte_min"):
        long_call_calendar(
            calendar_data,
            raw=True,
            front_dte_min=20,
            front_dte_max=60,
            back_dte_min=40,
            back_dte_max=90,
        )


def test_calendar_adjacent_dte_ranges_rejected(calendar_data):
    """Test that calendar raises error when front_dte_max equals back_dte_min."""
    with pytest.raises(ValueError, match="front_dte_max.*must be <.*back_dte_min"):
        long_call_calendar(
            calendar_data,
            raw=True,
            front_dte_min=20,
            front_dte_max=45,
            back_dte_min=45,
            back_dte_max=90,
        )


# =============================================================================
# Slippage Tests
# =============================================================================


def test_slippage_mid_is_default(data):
    """Test that default slippage mode is 'mid' (backward compatible)."""
    results = long_calls(data, raw=True)
    # With mid slippage, entry should be (bid + ask) / 2
    # For 212.5 strike call: bid=7.35, ask=7.45, mid=7.40
    row = results[results["strike"] == 212.5].iloc[0]
    assert round(row["entry"], 2) == 7.40


def test_slippage_spread_mode(data):
    """Test that spread slippage mode uses ask for long entries."""
    # Default (mid) - entry should be (7.35 + 7.45) / 2 = 7.40
    results_mid = long_calls(data, raw=True, slippage="mid")

    # Spread - for long calls, entry should be at ask price (7.45)
    results_spread = long_calls(data, raw=True, slippage="spread")

    row_mid = results_mid[results_mid["strike"] == 212.5].iloc[0]
    row_spread = results_spread[results_spread["strike"] == 212.5].iloc[0]

    # Spread entry should be higher than mid for long positions
    assert row_spread["entry"] > row_mid["entry"]
    assert round(row_spread["entry"], 2) == 7.45  # ask price


def test_slippage_spread_short_positions(data):
    """Test that spread slippage uses bid for short entries."""
    results_spread = short_calls(data, raw=True, slippage="spread")

    # For short calls, entry fill is at bid price (7.35)
    # The fill price is positive; the Side multiplier makes P&L negative
    row = results_spread[results_spread["strike"] == 212.5].iloc[0]
    assert round(row["entry"], 2) == 7.35


def test_slippage_liquidity_mode(data_with_volume):
    """Test liquidity-based slippage adjusts based on volume."""
    # With reference_volume=1000, high volume options get better fills
    results = long_calls(
        data_with_volume,
        raw=True,
        slippage="liquidity",
        fill_ratio=0.5,
        reference_volume=1000,
    )

    # High volume option (2000 vol) should get fill closer to mid
    high_vol_row = results[results["strike"] == 212.5].iloc[0]
    # Low volume option (100 vol) should get fill closer to ask
    low_vol_row = results[results["strike"] == 215.0].iloc[0]

    # Calculate expected fills
    # High vol: vol=2000, reference=1000 -> liquidity_score=1.0 -> ratio=0.5
    # bid=7.35, ask=7.45, mid=7.40, half_spread=0.05
    # entry = 7.40 + 0.05 * 0.5 = 7.425
    assert round(high_vol_row["entry"], 3) == 7.425

    # Low vol: vol=100, reference=1000 -> liquidity_score=0.1 -> ratio=0.5+(1-0.5)*(1-0.1)=0.95
    # bid=6.00, ask=6.10, mid=6.05, half_spread=0.05
    # entry = 6.05 + 0.05 * 0.95 = 6.0975
    assert round(low_vol_row["entry"], 4) == 6.0975


def test_slippage_liquidity_requires_volume_column(data):
    """Test that liquidity slippage raises error without volume column."""
    with pytest.raises(ValueError, match="volume.*not found"):
        long_calls(data, slippage="liquidity")


def test_slippage_invalid_mode_raises(data):
    """Test that invalid slippage mode raises error."""
    with pytest.raises(ValueError, match="must be 'mid', 'spread', or 'liquidity'"):
        long_calls(data, slippage="invalid")


def test_slippage_fill_ratio_validation(data):
    """Test that fill_ratio must be between 0 and 1."""
    with pytest.raises(ValueError, match="between 0 and 1"):
        long_calls(data, slippage="liquidity", fill_ratio=1.5)


def test_slippage_multi_leg_spread_mode(multi_strike_data):
    """Test slippage on multi-leg strategies (vertical spreads)."""
    # Long call spread: long lower strike, short higher strike
    results_mid = long_call_spread(multi_strike_data, raw=True, slippage="mid")
    results_spread = long_call_spread(multi_strike_data, raw=True, slippage="spread")

    # With spread slippage:
    # - Long leg entry at ask (higher cost)
    # - Short leg entry at bid (lower credit)
    # Net result: worse entry for the spread
    row_mid = results_mid.iloc[0]
    row_spread = results_spread.iloc[0]

    # Spread mode should have higher (worse) total entry cost for debit spread
    assert row_spread["total_entry_cost"] > row_mid["total_entry_cost"]


def test_slippage_calendar_spread_mode(calendar_data):
    """Test slippage on calendar spreads."""
    results_mid = long_call_calendar(
        calendar_data,
        raw=True,
        slippage="mid",
        front_dte_min=20,
        front_dte_max=40,
        back_dte_min=50,
        back_dte_max=70,
        exit_dte=7,
    )
    results_spread = long_call_calendar(
        calendar_data,
        raw=True,
        slippage="spread",
        front_dte_min=20,
        front_dte_max=40,
        back_dte_min=50,
        back_dte_max=70,
        exit_dte=7,
    )

    # With spread slippage, calendar spread entry cost should be higher
    # (worse fills for both legs)
    row_mid = results_mid[results_mid["strike"] == 212.5].iloc[0]
    row_spread = results_spread[results_spread["strike"] == 212.5].iloc[0]

    # Calendar spread is a debit spread, so higher entry cost is worse
    assert row_spread["total_entry_cost"] > row_mid["total_entry_cost"]


# =============================================================================
# Empty DataFrame Edge Cases
# =============================================================================


@pytest.fixture(scope="module")
def empty_option_data():
    """Empty DataFrame with correct columns and dtypes for options data."""
    cols = [
        "underlying_symbol",
        "underlying_price",
        "option_type",
        "expiration",
        "quote_date",
        "strike",
        "bid",
        "ask",
    ]
    df = pd.DataFrame(columns=cols)
    df["underlying_price"] = df["underlying_price"].astype("float64")
    df["strike"] = df["strike"].astype("float64")
    df["bid"] = df["bid"].astype("float64")
    df["ask"] = df["ask"].astype("float64")
    df["expiration"] = pd.Series(dtype="datetime64[ns]")
    df["quote_date"] = pd.Series(dtype="datetime64[ns]")
    return df


def test_empty_data_long_calls(empty_option_data):
    """Empty DataFrame should return empty result with correct columns."""
    results = long_calls(empty_option_data, raw=True)
    assert len(results) == 0
    assert list(results.columns) == single_strike_internal_cols


def test_empty_data_long_call_spread(empty_option_data):
    """Empty DataFrame should return empty result for spread."""
    results = long_call_spread(empty_option_data, raw=True)
    assert len(results) == 0


def test_empty_data_iron_condor(empty_option_data):
    """Empty DataFrame should return empty result for iron condor."""
    results = iron_condor(empty_option_data, raw=True)
    assert len(results) == 0


# =============================================================================
# NaN Values in Price Columns
# =============================================================================


def test_nan_in_bid_ask_filtered(data):
    """Options with NaN bid/ask should be filtered by min_bid_ask check."""
    data_with_nan = data.copy()
    # Set some bid/ask to NaN
    data_with_nan.loc[0, "bid"] = np.nan
    data_with_nan.loc[0, "ask"] = np.nan
    # Should not crash — NaN rows are filtered out during evaluation
    results = long_calls(data_with_nan, raw=True)
    assert isinstance(results, pd.DataFrame)


# =============================================================================
# drop_nan=False Tests
# =============================================================================


def test_drop_nan_false(multi_strike_data):
    """drop_nan=False should retain groups where all non-count stats are NaN."""
    # Use narrow DTE/OTM intervals to create bins with no data (NaN stats)
    common = dict(
        dte_interval=5, max_entry_dte=90, otm_pct_interval=0.01, max_otm_pct=0.5
    )
    results_drop = long_calls(multi_strike_data, drop_nan=True, **common)
    results_keep = long_calls(multi_strike_data, drop_nan=False, **common)
    # drop_nan=False should keep more (or equal) rows than drop_nan=True
    assert len(results_keep) >= len(results_drop)
    assert list(results_keep.columns) == single_strike_external_cols + describe_cols


# =============================================================================
# Vertical Spread Aggregated Mode Tests
# =============================================================================


def test_long_call_spread_aggregated(multi_strike_data):
    """Test long call spread aggregated output has correct columns."""
    results = long_call_spread(multi_strike_data)
    assert list(results.columns) == double_strike_external_cols + describe_cols
    assert len(results) > 0


def test_short_call_spread_aggregated(multi_strike_data):
    """Test short call spread aggregated output has correct columns."""
    results = short_call_spread(multi_strike_data)
    assert list(results.columns) == double_strike_external_cols + describe_cols


def test_long_put_spread_aggregated(multi_strike_data):
    """Test long put spread aggregated output has correct columns."""
    results = long_put_spread(multi_strike_data)
    assert list(results.columns) == double_strike_external_cols + describe_cols


def test_short_put_spread_aggregated(multi_strike_data):
    """Test short put spread aggregated output has correct columns."""
    results = short_put_spread(multi_strike_data)
    assert list(results.columns) == double_strike_external_cols + describe_cols


# =============================================================================
# Diagonal Spread P&L Value Tests
# =============================================================================


def test_long_call_diagonal_pnl_values(calendar_data):
    """Test long call diagonal spread calculates P&L correctly.

    Using front 210 call / back 212.5 call diagonal:
    Entry: short front 210 call (-4.45) + long back 212.5 call (4.95) = 0.50 debit
    Exit: close short front (-5.45) + close long back (5.05) = -0.40
    pct_change = (-0.40 - 0.50) / |0.50| = -1.80
    """
    results = long_call_diagonal(
        calendar_data,
        raw=True,
        front_dte_min=20,
        front_dte_max=40,
        back_dte_min=50,
        back_dte_max=70,
        exit_dte=7,
    )
    assert len(results) == 9
    row = results[
        (results["strike_leg1"] == 210.0) & (results["strike_leg2"] == 212.5)
    ].iloc[0]
    assert round(row["total_entry_cost"], 2) == 0.50
    assert round(row["total_exit_proceeds"], 2) == -0.40
    assert round(row["pct_change"], 2) == -1.80


def test_short_call_diagonal_pnl_values(calendar_data):
    """Test short call diagonal P&L values are opposite of long."""
    long_results = long_call_diagonal(
        calendar_data,
        raw=True,
        front_dte_min=20,
        front_dte_max=40,
        back_dte_min=50,
        back_dte_max=70,
        exit_dte=7,
    )
    short_results = short_call_diagonal(
        calendar_data,
        raw=True,
        front_dte_min=20,
        front_dte_max=40,
        back_dte_min=50,
        back_dte_max=70,
        exit_dte=7,
    )
    assert len(long_results) > 0, "Long diagonal should produce results"
    assert len(short_results) > 0, "Short diagonal should produce results"
    # Entry costs should have opposite signs (debit vs credit)
    long_entry = long_results.iloc[0]["total_entry_cost"]
    short_entry = short_results.iloc[0]["total_entry_cost"]
    assert long_entry * short_entry < 0 or (long_entry == 0 and short_entry == 0)


def test_long_put_diagonal_pnl_values(calendar_data):
    """Test long put diagonal spread P&L values.

    Using front 212.5 put / back 210 put diagonal:
    Entry: short front 212.5 put (-2.95) + long back 210 put (3.45) = 0.50 debit
    Exit: close short front (-0.35) + close long back (1.45) = 1.10
    pct_change = (1.10 - 0.50) / |0.50| = 1.20
    """
    results = long_put_diagonal(
        calendar_data,
        raw=True,
        front_dte_min=20,
        front_dte_max=40,
        back_dte_min=50,
        back_dte_max=70,
        exit_dte=7,
    )
    assert len(results) == 9
    row = results[
        (results["strike_leg1"] == 212.5) & (results["strike_leg2"] == 210.0)
    ].iloc[0]
    assert round(row["total_entry_cost"], 2) == 0.50
    assert round(row["total_exit_proceeds"], 2) == 1.10
    assert round(row["pct_change"], 2) == 1.20


# =============================================================================
# Short Variant P&L Value Assertions
# =============================================================================


def test_short_call_butterfly_pnl_values(multi_strike_data):
    """Short call butterfly P&L should be opposite of long call butterfly."""
    long_results = long_call_butterfly(multi_strike_data, raw=True)
    short_results = short_call_butterfly(multi_strike_data, raw=True)

    # Find matching strike combination
    long_row = long_results[
        (long_results["strike_leg1"] == 210.0)
        & (long_results["strike_leg2"] == 212.5)
        & (long_results["strike_leg3"] == 215.0)
    ].iloc[0]
    short_row = short_results[
        (short_results["strike_leg1"] == 210.0)
        & (short_results["strike_leg2"] == 212.5)
        & (short_results["strike_leg3"] == 215.0)
    ].iloc[0]

    # Entry costs should be opposite sign (debit vs credit)
    assert round(long_row["total_entry_cost"], 2) == -round(
        short_row["total_entry_cost"], 2
    )
    # Exit proceeds should be opposite sign
    assert round(long_row["total_exit_proceeds"], 2) == -round(
        short_row["total_exit_proceeds"], 2
    )


def test_short_put_butterfly_pnl_values(multi_strike_data):
    """Short put butterfly P&L should be opposite of long put butterfly."""
    long_results = long_put_butterfly(multi_strike_data, raw=True)
    short_results = short_put_butterfly(multi_strike_data, raw=True)

    long_row = long_results[
        (long_results["strike_leg1"] == 210.0)
        & (long_results["strike_leg2"] == 212.5)
        & (long_results["strike_leg3"] == 215.0)
    ].iloc[0]
    short_row = short_results[
        (short_results["strike_leg1"] == 210.0)
        & (short_results["strike_leg2"] == 212.5)
        & (short_results["strike_leg3"] == 215.0)
    ].iloc[0]

    assert round(long_row["total_entry_cost"], 2) == -round(
        short_row["total_entry_cost"], 2
    )


def test_reverse_iron_condor_pnl_values(multi_strike_data):
    """Reverse iron condor P&L should be opposite of iron condor."""
    ic_results = iron_condor(multi_strike_data, raw=True)
    ric_results = reverse_iron_condor(multi_strike_data, raw=True)

    ic_row = ic_results[
        (ic_results["strike_leg1"] == 207.5)
        & (ic_results["strike_leg2"] == 210.0)
        & (ic_results["strike_leg3"] == 215.0)
        & (ic_results["strike_leg4"] == 217.5)
    ].iloc[0]
    ric_row = ric_results[
        (ric_results["strike_leg1"] == 207.5)
        & (ric_results["strike_leg2"] == 210.0)
        & (ric_results["strike_leg3"] == 215.0)
        & (ric_results["strike_leg4"] == 217.5)
    ].iloc[0]

    assert round(ic_row["total_entry_cost"], 2) == -round(
        ric_row["total_entry_cost"], 2
    )


def test_reverse_iron_butterfly_pnl_values(multi_strike_data):
    """Reverse iron butterfly P&L should be opposite of iron butterfly."""
    ib_results = iron_butterfly(multi_strike_data, raw=True)
    rib_results = reverse_iron_butterfly(multi_strike_data, raw=True)

    ib_row = ib_results[
        (ib_results["strike_leg1"] == 207.5)
        & (ib_results["strike_leg2"] == 212.5)
        & (ib_results["strike_leg3"] == 212.5)
        & (ib_results["strike_leg4"] == 217.5)
    ].iloc[0]
    rib_row = rib_results[
        (rib_results["strike_leg1"] == 207.5)
        & (rib_results["strike_leg2"] == 212.5)
        & (rib_results["strike_leg3"] == 212.5)
        & (rib_results["strike_leg4"] == 217.5)
    ].iloc[0]

    assert round(ib_row["total_entry_cost"], 2) == -round(
        rib_row["total_entry_cost"], 2
    )


# =============================================================================
# Calendar-specific exit_dte_tolerance Tests
# =============================================================================


def test_calendar_exit_dte_tolerance(calendar_data):
    """Calendar spread with exit_dte_tolerance should find nearby exit dates."""
    # Use exit_dte=8 which doesn't have exact data, but tolerance=2 should find day 7
    results = long_call_calendar(
        calendar_data,
        raw=True,
        front_dte_min=20,
        front_dte_max=40,
        back_dte_min=50,
        back_dte_max=70,
        exit_dte=8,
        exit_dte_tolerance=2,
    )
    # Should find results by snapping to the available exit date (7 DTE)
    assert len(results) > 0


def test_calendar_exit_dte_tolerance_zero_no_match(calendar_data):
    """Calendar with exit_dte=8 and tolerance=0 should find no matches."""
    results = long_call_calendar(
        calendar_data,
        raw=True,
        front_dte_min=20,
        front_dte_max=40,
        back_dte_min=50,
        back_dte_max=70,
        exit_dte=8,
        exit_dte_tolerance=0,
    )
    assert len(results) == 0


# =============================================================================
# Duplicate Input Row Tests
# =============================================================================


def test_duplicate_rows_handled(data):
    """Duplicate rows in input data should not crash the pipeline."""
    duplicated = pd.concat([data, data], ignore_index=True)
    results = long_calls(duplicated, raw=True)
    assert isinstance(results, pd.DataFrame)
    # Should have more results due to duplicated entries
    assert len(results) >= 2
