from optopsy.strategies import *
from optopsy.definitions import *

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
    """Test long call butterfly returns correct structure and leg types."""
    results = long_call_butterfly(multi_strike_data, raw=True)
    assert list(results.columns) == triple_strike_internal_cols
    # All legs should be calls
    assert results.iloc[0]["option_type_leg1"] == "call"
    assert results.iloc[0]["option_type_leg2"] == "call"
    assert results.iloc[0]["option_type_leg3"] == "call"
    # Strikes should be in ascending order with equal width
    assert results.iloc[0]["strike_leg1"] < results.iloc[0]["strike_leg2"]
    assert results.iloc[0]["strike_leg2"] < results.iloc[0]["strike_leg3"]


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
    """Test long put butterfly returns correct structure and leg types."""
    results = long_put_butterfly(multi_strike_data, raw=True)
    assert list(results.columns) == triple_strike_internal_cols
    # All legs should be puts
    assert results.iloc[0]["option_type_leg1"] == "put"
    assert results.iloc[0]["option_type_leg2"] == "put"
    assert results.iloc[0]["option_type_leg3"] == "put"


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
    """Test iron condor returns correct structure and leg types."""
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
    """Test iron butterfly returns correct structure and leg types."""
    results = iron_butterfly(multi_strike_data, raw=True)
    assert list(results.columns) == quadruple_strike_internal_cols
    # Leg 1 and 2 should be puts, leg 3 and 4 should be calls
    assert results.iloc[0]["option_type_leg1"] == "put"
    assert results.iloc[0]["option_type_leg2"] == "put"
    assert results.iloc[0]["option_type_leg3"] == "call"
    assert results.iloc[0]["option_type_leg4"] == "call"
    # Middle legs should share the same strike
    assert results.iloc[0]["strike_leg2"] == results.iloc[0]["strike_leg3"]


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
    """Test covered call returns correct structure."""
    results = covered_call(multi_strike_data, raw=True)
    assert list(results.columns) == double_strike_internal_cols
    # Both legs should be calls
    assert results.iloc[0]["option_type_leg1"] == "call"
    assert results.iloc[0]["option_type_leg2"] == "call"


def test_covered_call(multi_strike_data):
    """Test covered call aggregated output."""
    results = covered_call(multi_strike_data)
    assert list(results.columns) == double_strike_external_cols + describe_cols


def test_protective_put_raw(multi_strike_data):
    """Test protective put returns correct structure."""
    results = protective_put(multi_strike_data, raw=True)
    assert list(results.columns) == double_strike_internal_cols
    # Leg 1 should be call (synthetic stock), leg 2 should be put
    assert results.iloc[0]["option_type_leg1"] == "call"
    assert results.iloc[0]["option_type_leg2"] == "put"


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
