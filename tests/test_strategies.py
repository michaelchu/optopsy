from optopsy.strategies import *
from optopsy.definitions import *
import pytest

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
