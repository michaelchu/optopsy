import datetime

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
from optopsy.types import TargetRange

describe_cols = [
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


# =============================================================================
# Butterfly Strategy Tests
# =============================================================================


_BF_CALL_DELTAS = dict(
    leg1_delta=TargetRange(target=0.65, min=0.55, max=0.75),
    leg2_delta=TargetRange(target=0.50, min=0.40, max=0.60),
    leg3_delta=TargetRange(target=0.35, min=0.25, max=0.45),
)
_BF_PUT_DELTAS = dict(
    leg1_delta=TargetRange(target=0.35, min=0.25, max=0.45),
    leg2_delta=TargetRange(target=0.50, min=0.40, max=0.60),
    leg3_delta=TargetRange(target=0.65, min=0.55, max=0.75),
)


def test_long_call_butterfly_raw(multi_strike_data):
    """Test long call butterfly returns correct structure and calculated values."""
    results = long_call_butterfly(multi_strike_data, raw=True, **_BF_CALL_DELTAS)
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
    results = long_call_butterfly(multi_strike_data, **_BF_CALL_DELTAS)
    assert list(results.columns) == triple_strike_external_cols + describe_cols


def test_short_call_butterfly_raw(multi_strike_data):
    """Test short call butterfly returns correct structure."""
    results = short_call_butterfly(multi_strike_data, raw=True, **_BF_CALL_DELTAS)
    assert list(results.columns) == triple_strike_internal_cols
    assert results.iloc[0]["option_type_leg1"] == "call"
    assert results.iloc[0]["option_type_leg2"] == "call"
    assert results.iloc[0]["option_type_leg3"] == "call"


def test_long_put_butterfly_raw(multi_strike_data):
    """Test long put butterfly returns correct structure and calculated values."""
    results = long_put_butterfly(multi_strike_data, raw=True, **_BF_PUT_DELTAS)
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
    results = long_put_butterfly(multi_strike_data, **_BF_PUT_DELTAS)
    assert list(results.columns) == triple_strike_external_cols + describe_cols


def test_short_put_butterfly_raw(multi_strike_data):
    """Test short put butterfly returns correct structure."""
    results = short_put_butterfly(multi_strike_data, raw=True, **_BF_PUT_DELTAS)
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
    assert not results.empty
    # Both legs should be calls
    assert results.iloc[0]["option_type_leg1"] == "call"
    assert results.iloc[0]["option_type_leg2"] == "call"
    # Default deep ITM leg1 (207.5, delta=0.80) + DEFAULT leg2 (215.0, delta=0.35)
    row = results.iloc[0]
    assert row["strike_leg1"] == 207.5
    assert row["strike_leg2"] == 215.0
    # Entry: long 207.5 call (6.95) + short 215 call (-1.55) = 5.40
    assert round(row["total_entry_cost"], 2) == 5.40
    # Exit: long 207.5 call (7.50) + short 215 call (-0.05) = 7.45
    assert round(row["total_exit_proceeds"], 2) == 7.45
    assert round(row["pct_change"], 2) == 0.38


def test_covered_call(multi_strike_data):
    """Test covered call aggregated output."""
    results = covered_call(multi_strike_data)
    assert list(results.columns) == double_strike_external_cols + describe_cols


_PROT_PUT_DELTAS = dict(
    leg1_delta=TargetRange(target=0.80, min=0.70, max=0.90),
    leg2_delta=TargetRange(target=0.50, min=0.40, max=0.60),
)


def test_protective_put_raw(multi_strike_data):
    """Test protective put returns correct structure and calculated values."""
    results = protective_put(multi_strike_data, raw=True, **_PROT_PUT_DELTAS)
    assert list(results.columns) == double_strike_internal_cols
    assert not results.empty
    # Leg 1 should be call (synthetic stock), leg 2 should be put
    assert results.iloc[0]["option_type_leg1"] == "call"
    assert results.iloc[0]["option_type_leg2"] == "put"
    # leg1 deep ITM call at 207.5, leg2 ATM put at 212.5
    row = results.iloc[0]
    assert row["strike_leg1"] == 207.5
    assert row["strike_leg2"] == 212.5
    # Entry: long 207.5 call (6.95) + long 212.5 put (3.05) = 10.00
    assert round(row["total_entry_cost"], 2) == 10.00
    # Exit: call worth 7.50 + put expired (0.025) = 7.525
    assert round(row["total_exit_proceeds"], 3) == 7.525
    assert round(row["pct_change"], 4) == -0.2475


def test_protective_put(multi_strike_data):
    """Test protective put aggregated output."""
    results = protective_put(multi_strike_data, **_PROT_PUT_DELTAS)
    assert list(results.columns) == double_strike_external_cols + describe_cols


# --- Stock-backed covered strategy tests ---


def test_covered_call_with_stock_raw(multi_strike_data, stock_data_multi_strike):
    """Covered call using actual stock data returns correct structure and values."""
    results = covered_call(
        multi_strike_data, stock_data=stock_data_multi_strike, raw=True
    )
    assert list(results.columns) == double_strike_internal_cols
    assert not results.empty
    row = results.iloc[0]
    # Leg 1 is stock, leg 2 is short call
    assert row["option_type_leg1"] == "stock"
    assert row["option_type_leg2"] == "call"
    # Stock entry price is the close at entry date
    assert row["strike_leg1"] == 212.5
    # Short call selected at 215.0 (delta 0.35, closest to DEFAULT 0.30)
    assert row["strike_leg2"] == 215.0
    assert row["delta_entry_leg1"] == 1.0
    # Entry: buy stock 212.5 + short call -mid(1.50,1.60) = 212.5 - 1.55 = 210.95
    assert round(row["total_entry_cost"], 2) == 210.95
    # Exit: sell stock 215.0 + close short call -mid(0.0,0.10) = 215.0 - 0.05 = 214.95
    assert round(row["total_exit_proceeds"], 2) == 214.95
    assert round(row["pct_change"], 4) == round(4.00 / 210.95, 4)


def test_covered_call_with_stock_aggregated(multi_strike_data, stock_data_multi_strike):
    """Covered call with stock data returns valid aggregated output."""
    results = covered_call(multi_strike_data, stock_data=stock_data_multi_strike)
    assert not results.empty
    assert "dte_range" in results.columns
    assert "delta_range_leg2" in results.columns
    assert "delta_range_leg1" not in results.columns


def test_protective_put_with_stock_raw(multi_strike_data, stock_data_multi_strike):
    """Protective put using actual stock data returns correct structure and values."""
    results = protective_put(
        multi_strike_data, stock_data=stock_data_multi_strike, raw=True
    )
    assert list(results.columns) == double_strike_internal_cols
    assert not results.empty
    row = results.iloc[0]
    assert row["option_type_leg1"] == "stock"
    assert row["option_type_leg2"] == "put"
    assert row["strike_leg1"] == 212.5
    # Long put selected at 210.0 (|delta|=0.35, closest to DEFAULT 0.30)
    assert row["strike_leg2"] == 210.0
    assert row["delta_entry_leg1"] == 1.0
    # Entry: buy stock 212.5 + long put mid(1.40,1.50) = 212.5 + 1.45 = 213.95
    assert round(row["total_entry_cost"], 2) == 213.95
    # Exit: sell stock 215.0 + put mid(0.0,0.05) = 215.0 + 0.025 = 215.025
    assert round(row["total_exit_proceeds"], 3) == 215.025
    assert round(row["pct_change"], 4) == round(1.075 / 213.95, 4)


def test_covered_call_with_stock_no_match(multi_strike_data):
    """When stock data has no matching dates, result is empty."""
    empty_stock = pd.DataFrame(
        {
            "underlying_symbol": ["SPX"],
            "quote_date": [datetime.datetime(2020, 1, 1)],
            "close": [300.0],
        }
    )
    results = covered_call(multi_strike_data, stock_data=empty_stock, raw=True)
    assert results.empty
    assert list(results.columns) == double_strike_internal_cols

    # Aggregated mode should also return empty without groupby errors
    results_agg = covered_call(multi_strike_data, stock_data=empty_stock)
    assert results_agg.empty


def test_covered_call_with_stock_partial_match(multi_strike_data):
    """When stock data matches entry but not exit date, result is empty."""
    # Only entry date (2018-01-01) present, exit date (2018-01-31) missing
    partial_stock = pd.DataFrame(
        {
            "underlying_symbol": ["SPX"],
            "quote_date": [datetime.datetime(2018, 1, 1)],
            "close": [212.5],
        }
    )
    results = covered_call(multi_strike_data, stock_data=partial_stock, raw=True)
    assert results.empty
    assert list(results.columns) == double_strike_internal_cols


def test_covered_call_with_stock_exit_dte_tolerance():
    """Stock exit date uses actual option exit date, not computed expiration - exit_dte.

    Regression test for GitHub issue #187.  When exit_dte_tolerance > 0
    the option exit row may land on a date different from
    expiration - exit_dte.  The stock exit price must be looked up on
    the actual option exit date (quote_date_exit), not the computed one.

    Setup:
    - Expiration 2018-02-28, entry 2018-01-15 (DTE=44), exit_dte=7, tolerance=3
    - Computed exit date = expiration - 7 = 2018-02-21
    - Only available exit row at DTE=9 (2018-02-19) — within tolerance [4,10]
    - Stock data exists on 2018-01-15 and 2018-02-19, but NOT on 2018-02-21
    - Old code joined on 2018-02-21 and got empty; fix joins on 2018-02-19.
    """
    exp_date = datetime.datetime(2018, 2, 28)
    entry_date = datetime.datetime(2018, 1, 15)  # DTE = 44
    actual_exit_date = datetime.datetime(2018, 2, 19)  # DTE = 9 (closest to 7)

    cols = [
        "underlying_symbol",
        "underlying_price",
        "option_type",
        "expiration",
        "quote_date",
        "strike",
        "bid",
        "ask",
        "delta",
    ]
    rows = [
        # Entry day — call at strike 105 (OTM)
        ["SPX", 100.0, "call", exp_date, entry_date, 105.0, 1.50, 1.60, 0.35],
        # Exit day — DTE=9, within tolerance of exit_dte=7±3
        ["SPX", 103.0, "call", exp_date, actual_exit_date, 105.0, 0.40, 0.50, 0.25],
    ]
    data = pd.DataFrame(data=rows, columns=cols)

    stock_data = pd.DataFrame(
        {
            "underlying_symbol": ["SPX", "SPX"],
            "quote_date": [entry_date, actual_exit_date],
            "close": [100.0, 103.0],
        }
    )
    # No stock row on 2018-02-21 (the computed expiration - exit_dte date)

    results = covered_call(
        data,
        stock_data=stock_data,
        exit_dte=7,
        exit_dte_tolerance=3,
        raw=True,
    )
    assert not results.empty, (
        "Should match stock exit on actual option exit date, not computed date"
    )
    row = results.iloc[0]
    assert row["option_type_leg1"] == "stock"
    assert row["option_type_leg2"] == "call"
    # Stock entry price is the close at entry date
    assert row["strike_leg1"] == 100.0
    # Total exit uses stock close on actual_exit_date (2018-02-19), not computed date
    stock_exit = 103.0
    option_exit_mid = (0.40 + 0.50) / 2  # short call exit mid
    expected_exit_proceeds = stock_exit - option_exit_mid
    assert round(row["total_exit_proceeds"], 2) == round(expected_exit_proceeds, 2)


def test_protective_put_with_stock_aggregated(
    multi_strike_data, stock_data_multi_strike
):
    """Protective put with stock data returns valid aggregated output."""
    results = protective_put(multi_strike_data, stock_data=stock_data_multi_strike)
    assert not results.empty
    assert "dte_range" in results.columns
    assert "delta_range_leg2" in results.columns
    assert "delta_range_leg1" not in results.columns


def test_covered_without_stock_unchanged(multi_strike_data):
    """Without stock_data the existing synthetic approach is used."""
    results = covered_call(multi_strike_data, raw=True)
    assert results.iloc[0]["option_type_leg1"] == "call"
    assert results.iloc[0]["strike_leg1"] == 207.5


# --- yfinance-format stock data tests ---


def test_covered_call_with_yfinance_format(multi_strike_data):
    """Covered call accepts yfinance-style DataFrame (DatetimeIndex, capitalized cols)."""
    yf_stock = pd.DataFrame(
        {
            "Close": [212.5, 215.0],
        },
        index=pd.DatetimeIndex(
            [datetime.datetime(2018, 1, 1), datetime.datetime(2018, 1, 31)],
            name="Date",
        ),
    )
    results = covered_call(multi_strike_data, stock_data=yf_stock, raw=True)
    assert not results.empty
    assert results.iloc[0]["option_type_leg1"] == "stock"
    assert results.iloc[0]["strike_leg1"] == 212.5


def test_protective_put_with_yfinance_format(multi_strike_data):
    """Protective put accepts yfinance-style DataFrame."""
    yf_stock = pd.DataFrame(
        {
            "Close": [212.5, 215.0],
        },
        index=pd.DatetimeIndex(
            [datetime.datetime(2018, 1, 1), datetime.datetime(2018, 1, 31)],
            name="Date",
        ),
    )
    results = protective_put(multi_strike_data, stock_data=yf_stock, raw=True)
    assert not results.empty
    assert results.iloc[0]["option_type_leg1"] == "stock"
    assert results.iloc[0]["option_type_leg2"] == "put"


def test_covered_call_with_date_column(multi_strike_data):
    """stock_data with 'date' column (no DatetimeIndex) is normalized."""
    stock = pd.DataFrame(
        {
            "date": [
                datetime.datetime(2018, 1, 1),
                datetime.datetime(2018, 1, 31),
            ],
            "close": [212.5, 215.0],
        }
    )
    results = covered_call(multi_strike_data, stock_data=stock, raw=True)
    assert not results.empty
    assert results.iloc[0]["option_type_leg1"] == "stock"


def test_covered_call_stock_data_multi_symbol_error(multi_strike_data):
    """Raise when stock_data has no symbol and options data has multiple symbols."""
    # Create options data with two symbols
    multi_sym = multi_strike_data.copy()
    extra = multi_strike_data.copy()
    extra["underlying_symbol"] = "AAPL"
    multi_sym = pd.concat([multi_sym, extra], ignore_index=True)

    stock = pd.DataFrame(
        {
            "Close": [212.5, 215.0],
        },
        index=pd.DatetimeIndex(
            [datetime.datetime(2018, 1, 1), datetime.datetime(2018, 1, 31)],
            name="Date",
        ),
    )
    with pytest.raises(KeyError, match="multiple symbols"):
        covered_call(multi_sym, stock_data=stock, raw=True)


def test_single_long_calls_raw(data):
    results = long_calls(data, raw=True)
    assert len(results) == 1
    assert list(results.columns) == single_strike_internal_cols
    assert "call" in list(results["option_type"].values)
    # Delta targeting selects 215.0 (delta 0.30, closest to DEFAULT target)
    assert round(results.iloc[0]["pct_change"], 2) == -0.17


def test_single_long_puts_raw(data):
    results = long_puts(data, raw=True)
    assert len(results) == 1
    assert list(results.columns) == single_strike_internal_cols
    assert "put" in list(results["option_type"].values)
    # Delta targeting selects 210.0 put (abs delta 0.30)
    assert round(results.iloc[0]["pct_change"], 2) == -1


def test_single_short_calls_raw(data):
    results = short_calls(data, raw=True)
    assert len(results) == 1
    assert list(results.columns) == single_strike_internal_cols
    assert "call" in list(results["option_type"].values)
    assert round(results.iloc[0]["pct_change"], 2) == 0.17


def test_single_short_puts_raw(data):
    results = short_puts(data, raw=True)
    assert len(results) == 1
    assert list(results.columns) == single_strike_internal_cols
    assert "put" in list(results["option_type"].values)
    # Short puts kept the entire premium (underlying moved away from strike)
    assert round(results.iloc[0]["pct_change"], 2) == 1


def test_singles_long_calls(data):
    results = long_calls(data)
    assert len(results) == 1
    assert results.iloc[0]["count"] == 1.0
    assert round(results.iloc[0]["mean"], 2) == -0.17
    assert list(results.columns) == single_strike_external_cols + describe_cols


def test_singles_long_puts(data):
    results = long_puts(data)
    assert len(results) == 1
    assert results.iloc[0]["count"] == 1.0
    assert round(results.iloc[0]["mean"], 2) == -1.0
    assert list(results.columns) == single_strike_external_cols + describe_cols


def test_singles_short_calls(data):
    results = short_calls(data)
    assert len(results) == 1
    assert results.iloc[0]["count"] == 1.0
    assert round(results.iloc[0]["mean"], 2) == 0.17
    assert list(results.columns) == single_strike_external_cols + describe_cols


def test_singles_short_puts(data):
    results = short_puts(data)
    assert len(results) == 1
    assert results.iloc[0]["count"] == 1.0
    assert round(results.iloc[0]["mean"], 2) == 1.0
    assert list(results.columns) == single_strike_external_cols + describe_cols


def test_straddles_long_raw(data):
    results = long_straddles(data, raw=True)
    assert list(results.columns) == straddle_internal_cols
    assert len(results) == 1
    assert results.iloc[0]["option_type_leg1"] == "put"
    assert results.iloc[0]["option_type_leg2"] == "call"
    # ATM at 212.5: put entry 5.75 + call entry 7.40 = 13.15
    # Exit: put 0.0 + call 7.50 = 7.50. pct_change = (7.50 - 13.15)/13.15
    assert round(results.iloc[0]["pct_change"], 2) == -0.43


def test_straddles_short_raw(data):
    results = short_straddles(data, raw=True)
    assert list(results.columns) == straddle_internal_cols
    assert len(results) == 1
    assert results.iloc[0]["option_type_leg1"] == "put"
    assert results.iloc[0]["option_type_leg2"] == "call"
    assert round(results.iloc[0]["pct_change"], 2) == 0.43


def test_long_straddles(data):
    results = long_straddles(data)
    assert len(results) == 1
    assert results.iloc[0]["count"] == 1.0
    assert round(results.iloc[0]["mean"], 2) == -0.43
    assert list(results.columns) == double_strike_external_cols + describe_cols


def test_short_straddles(data):
    results = short_straddles(data)
    assert len(results) == 1
    assert results.iloc[0]["count"] == 1.0
    assert round(results.iloc[0]["mean"], 2) == 0.43
    assert list(results.columns) == double_strike_external_cols + describe_cols


def test_strangles_long_raw(data):
    results = long_strangles(data, raw=True)
    assert len(results) == 1
    assert list(results.columns) == double_strike_internal_cols
    assert results.iloc[0]["option_type_leg1"] == "put"
    assert results.iloc[0]["option_type_leg2"] == "call"
    # Put at 210.0 (4.55) + call at 215.0 (6.025) = 10.575
    # Exit: put 0.0 + call 5.005 = 5.005. pct_change = (5.005 - 10.575)/10.575
    assert round(results.iloc[0]["pct_change"], 2) == -0.53


def test_strangles_short_raw(data):
    results = short_strangles(data, raw=True)
    assert len(results) == 1
    assert list(results.columns) == double_strike_internal_cols
    assert results.iloc[0]["option_type_leg1"] == "put"
    assert results.iloc[0]["option_type_leg2"] == "call"
    assert round(results.iloc[0]["pct_change"], 2) == 0.53


def test_long_strangles(data):
    results = long_strangles(data)
    assert len(results) == 1
    assert results.iloc[0]["count"] == 1.0
    assert round(results.iloc[0]["mean"], 2) == -0.53
    assert list(results.columns) == double_strike_external_cols + describe_cols


def test_short_strangles(data):
    results = short_strangles(data)
    assert len(results) == 1
    assert results.iloc[0]["count"] == 1.0
    assert round(results.iloc[0]["mean"], 2) == 0.53
    assert list(results.columns) == double_strike_external_cols + describe_cols


_CALL_SPREAD_DELTAS = dict(
    leg1_delta=TargetRange(target=0.50, min=0.40, max=0.60),
    leg2_delta=TargetRange(target=0.30, min=0.20, max=0.40),
)
_PUT_SPREAD_DELTAS = dict(
    leg1_delta=TargetRange(target=0.30, min=0.20, max=0.40),
    leg2_delta=TargetRange(target=0.50, min=0.40, max=0.60),
)


def test_long_call_spread_raw(data):
    results = long_call_spread(data, raw=True, **_CALL_SPREAD_DELTAS)
    assert len(results) == 1
    assert list(results.columns) == double_strike_internal_cols
    assert results.iloc[0]["option_type_leg1"] == "call"
    assert results.iloc[0]["option_type_leg2"] == "call"
    # leg1 at 212.5 (delta 0.50), leg2 at 215.0 (delta 0.30)
    assert round(results.iloc[0]["pct_change"], 2) == 0.81


def test_long_put_spread_raw(data):
    results = long_put_spread(data, raw=True, **_PUT_SPREAD_DELTAS)
    assert len(results) == 1
    assert list(results.columns) == double_strike_internal_cols
    assert results.iloc[0]["option_type_leg1"] == "put"
    assert results.iloc[0]["option_type_leg2"] == "put"
    assert round(results.iloc[0]["pct_change"], 2) == -1


def test_short_call_spread_raw(data):
    results = short_call_spread(data, raw=True, **_CALL_SPREAD_DELTAS)
    assert len(results) == 1
    assert list(results.columns) == double_strike_internal_cols
    assert results.iloc[0]["option_type_leg1"] == "call"
    assert results.iloc[0]["option_type_leg2"] == "call"
    assert round(results.iloc[0]["pct_change"], 2) == -0.81


def test_short_put_spread_raw(data):
    results = short_put_spread(data, raw=True, **_PUT_SPREAD_DELTAS)
    assert len(results) == 1
    assert list(results.columns) == double_strike_internal_cols
    assert results.iloc[0]["option_type_leg1"] == "put"
    assert results.iloc[0]["option_type_leg2"] == "put"
    assert round(results.iloc[0]["pct_change"], 2) == 1


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
    assert len(results) == 1
    # All legs should be calls
    assert results.iloc[0]["option_type"] == "call"
    # Same strike for both legs (calendar spread)
    assert "strike" in results.columns
    # Front expiration should be before back expiration
    assert results.iloc[0]["expiration_leg1"] < results.iloc[0]["expiration_leg2"]

    # Delta targeting selects strike 215.0 (delta 0.35, closest to DEFAULT 0.30)
    row = results.iloc[0]
    assert row["strike"] == 215.0
    # Entry: short front 215 call (-1.75) + long back 215 call (3.65) = 1.90
    # Exit: close short front (-0.85) + close long back (3.35) = 2.50
    assert round(row["total_entry_cost"], 2) == 1.90
    assert round(row["total_exit_proceeds"], 2) == 2.50
    assert round(row["pct_change"], 2) == 0.32


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
    assert len(results) == 1
    assert results.iloc[0]["option_type"] == "call"

    # Short calendar is opposite of long: signs reversed
    row = results.iloc[0]
    assert row["strike"] == 215.0
    assert round(row["total_entry_cost"], 2) == -1.90
    assert round(row["total_exit_proceeds"], 2) == -2.50
    assert round(row["pct_change"], 2) == -0.32


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
    assert len(results) == 1
    assert results.iloc[0]["option_type"] == "put"
    assert results.iloc[0]["expiration_leg1"] < results.iloc[0]["expiration_leg2"]

    # Delta targeting selects strike 210.0 (abs delta 0.35, closest to DEFAULT 0.30)
    row = results.iloc[0]
    assert row["strike"] == 210.0
    # Entry: short front 210 put (-1.95) + long back 210 put (3.45) = 1.50
    # Exit: close short front (-0.15) + close long back (1.45) = 1.30
    assert round(row["total_entry_cost"], 2) == 1.50
    assert round(row["total_exit_proceeds"], 2) == 1.30
    assert round(row["pct_change"], 2) == -0.13


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
    # Delta targeting selects 215.0 (delta 0.30). mid = (6.00 + 6.05) / 2 = 6.025
    row = results[results["strike"] == 215.0].iloc[0]
    assert round(row["entry"], 3) == 6.025


def test_slippage_spread_mode(data):
    """Test that spread slippage mode uses ask for long entries."""
    results_mid = long_calls(data, raw=True, slippage="mid")
    results_spread = long_calls(data, raw=True, slippage="spread")

    row_mid = results_mid.iloc[0]
    row_spread = results_spread.iloc[0]

    # Spread entry should be higher than mid for long positions
    assert row_spread["entry"] > row_mid["entry"]
    # For 215.0 call: ask=6.05
    assert round(row_spread["entry"], 2) == 6.05


def test_slippage_spread_short_positions(data):
    """Test that spread slippage uses bid for short entries."""
    results_spread = short_calls(data, raw=True, slippage="spread")

    # For short calls, entry fill is at bid price (6.00 for 215.0 strike)
    row = results_spread.iloc[0]
    assert round(row["entry"], 2) == 6.00


def test_slippage_liquidity_mode(data_with_volume):
    """Test liquidity-based slippage adjusts based on volume."""
    # Delta targeting selects 1 strike per group; use explicit delta to target high-vol option
    results = long_calls(
        data_with_volume,
        raw=True,
        slippage="liquidity",
        fill_ratio=0.5,
        reference_volume=1000,
        leg1_delta=TargetRange(target=0.55, min=0.45, max=0.65),
    )
    assert len(results) == 1

    # High vol: vol=2000, reference=1000 -> liquidity_score=1.0 -> ratio=0.5
    # bid=7.35, ask=7.45, mid=7.40, half_spread=0.05
    # entry = 7.40 + 0.05 * 0.5 = 7.425
    high_vol_row = results[results["strike"] == 212.5].iloc[0]
    assert round(high_vol_row["entry"], 3) == 7.425


def test_slippage_liquidity_requires_volume_column(data):
    """Test that liquidity slippage raises error without volume column."""
    with pytest.raises(ValueError, match="volume.*not found"):
        long_calls(data, slippage="liquidity")


def test_slippage_invalid_mode_raises(data):
    """Test that invalid slippage mode raises error."""
    with pytest.raises(
        ValueError, match=r"slippage.*Input should be 'mid', 'spread' or 'liquidity'"
    ):
        long_calls(data, slippage="invalid")


def test_slippage_fill_ratio_validation(data):
    """Test that fill_ratio must be between 0 and 1."""
    with pytest.raises(ValueError, match=r"fill_ratio.*less than or equal to 1"):
        long_calls(data, slippage="liquidity", fill_ratio=1.5)


def test_slippage_multi_leg_spread_mode(multi_strike_data):
    """Test slippage on multi-leg strategies (vertical spreads)."""
    spread_deltas = dict(
        leg1_delta=TargetRange(target=0.50, min=0.40, max=0.60),
        leg2_delta=TargetRange(target=0.20, min=0.10, max=0.30),
    )
    results_mid = long_call_spread(
        multi_strike_data, raw=True, slippage="mid", **spread_deltas
    )
    results_spread = long_call_spread(
        multi_strike_data, raw=True, slippage="spread", **spread_deltas
    )

    assert not results_mid.empty
    assert not results_spread.empty

    # Spread mode should have higher (worse) total entry cost for debit spread
    assert (
        results_spread.iloc[0]["total_entry_cost"]
        > results_mid.iloc[0]["total_entry_cost"]
    )


def test_slippage_calendar_spread_mode(calendar_data):
    """Test slippage on calendar spreads."""
    cal_kwargs = dict(
        raw=True,
        front_dte_min=20,
        front_dte_max=40,
        back_dte_min=50,
        back_dte_max=70,
        exit_dte=7,
    )
    results_mid = long_call_calendar(calendar_data, slippage="mid", **cal_kwargs)
    results_spread = long_call_calendar(calendar_data, slippage="spread", **cal_kwargs)

    assert not results_mid.empty
    assert not results_spread.empty

    # Calendar spread is a debit spread, so higher entry cost is worse
    assert (
        results_spread.iloc[0]["total_entry_cost"]
        > results_mid.iloc[0]["total_entry_cost"]
    )


def test_slippage_covered_call_with_stock(multi_strike_data, stock_data_multi_strike):
    """Test that slippage is applied to the option leg in stock-backed covered calls."""
    results_mid = covered_call(
        multi_strike_data, stock_data=stock_data_multi_strike, raw=True, slippage="mid"
    )
    results_spread = covered_call(
        multi_strike_data,
        stock_data=stock_data_multi_strike,
        raw=True,
        slippage="spread",
    )

    assert not results_mid.empty
    assert not results_spread.empty

    row_mid = results_mid.iloc[0]
    row_spread = results_spread.iloc[0]

    # Stock prices are identical (close prices, no bid/ask)
    assert row_mid["strike_leg1"] == row_spread["strike_leg1"]

    # Covered call = long stock + short call.
    # Short call entry fills at bid (worse for seller) under spread slippage,
    # so option premium received is lower -> total entry cost is higher.
    assert row_spread["total_entry_cost"] > row_mid["total_entry_cost"]

    # Verify exact values:
    # Short call at 215.0: bid=1.50, ask=1.60, mid=1.55
    # Mid mode: entry = stock(212.5) - mid(1.55) = 210.95
    assert round(row_mid["total_entry_cost"], 2) == 210.95
    # Spread mode: short entry fills at bid=1.50
    # entry = stock(212.5) - bid(1.50) = 211.00
    assert round(row_spread["total_entry_cost"], 2) == 211.00


def test_slippage_protective_put_with_stock(multi_strike_data, stock_data_multi_strike):
    """Test that slippage is applied to the option leg in stock-backed protective puts."""
    results_mid = protective_put(
        multi_strike_data, stock_data=stock_data_multi_strike, raw=True, slippage="mid"
    )
    results_spread = protective_put(
        multi_strike_data,
        stock_data=stock_data_multi_strike,
        raw=True,
        slippage="spread",
    )

    assert not results_mid.empty
    assert not results_spread.empty

    row_mid = results_mid.iloc[0]
    row_spread = results_spread.iloc[0]

    # Protective put = long stock + long put.
    # Long put entry fills at ask (worse for buyer) under spread slippage,
    # so total entry cost is higher.
    assert row_spread["total_entry_cost"] > row_mid["total_entry_cost"]

    # Verify exact values:
    # Long put at 210.0: bid=1.40, ask=1.50, mid=1.45
    # Mid mode: entry = stock(212.5) + mid(1.45) = 213.95
    assert round(row_mid["total_entry_cost"], 2) == 213.95
    # Spread mode: long entry fills at ask=1.50
    # entry = stock(212.5) + ask(1.50) = 214.00
    assert round(row_spread["total_entry_cost"], 2) == 214.00


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
        "delta",
    ]
    df = pd.DataFrame(columns=cols)
    df["underlying_price"] = df["underlying_price"].astype("float64")
    df["strike"] = df["strike"].astype("float64")
    df["bid"] = df["bid"].astype("float64")
    df["ask"] = df["ask"].astype("float64")
    df["delta"] = df["delta"].astype("float64")
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
    # Use narrow DTE/delta intervals to create bins with no data (NaN stats)
    common = dict(dte_interval=5, max_entry_dte=90, delta_interval=0.01)
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
    results = long_call_spread(multi_strike_data, **_CALL_SPREAD_DELTAS)
    assert list(results.columns) == double_strike_external_cols + describe_cols
    assert len(results) > 0


def test_short_call_spread_aggregated(multi_strike_data):
    """Test short call spread aggregated output has correct columns."""
    results = short_call_spread(multi_strike_data, **_CALL_SPREAD_DELTAS)
    assert list(results.columns) == double_strike_external_cols + describe_cols


def test_long_put_spread_aggregated(multi_strike_data):
    """Test long put spread aggregated output has correct columns."""
    results = long_put_spread(multi_strike_data, **_PUT_SPREAD_DELTAS)
    assert list(results.columns) == double_strike_external_cols + describe_cols


def test_short_put_spread_aggregated(multi_strike_data):
    """Test short put spread aggregated output has correct columns."""
    results = short_put_spread(multi_strike_data, **_PUT_SPREAD_DELTAS)
    assert list(results.columns) == double_strike_external_cols + describe_cols


# =============================================================================
# Diagonal Spread P&L Value Tests
# =============================================================================


def test_long_call_diagonal_pnl_values(calendar_data):
    """Test long call diagonal spread calculates P&L correctly."""
    results = long_call_diagonal(
        calendar_data,
        raw=True,
        front_dte_min=20,
        front_dte_max=40,
        back_dte_min=50,
        back_dte_max=70,
        exit_dte=7,
        leg1_delta=TargetRange(target=0.65, min=0.55, max=0.75),
        leg2_delta=TargetRange(target=0.50, min=0.40, max=0.60),
    )
    assert len(results) == 1
    row = results.iloc[0]
    # Front 210 call / back 212.5 call
    assert row["strike_leg1"] == 210.0
    assert row["strike_leg2"] == 212.5
    # Entry: short front 210 call (-4.45) + long back 212.5 call (4.95) = 0.50 debit
    assert round(row["total_entry_cost"], 2) == 0.50
    # Exit: close short front (-5.45) + close long back (5.05) = -0.40
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
    """Test long put diagonal spread P&L values."""
    results = long_put_diagonal(
        calendar_data,
        raw=True,
        front_dte_min=20,
        front_dte_max=40,
        back_dte_min=50,
        back_dte_max=70,
        exit_dte=7,
        leg1_delta=TargetRange(target=0.50, min=0.40, max=0.60),
        leg2_delta=TargetRange(target=0.35, min=0.25, max=0.45),
    )
    assert len(results) == 1
    row = results.iloc[0]
    # Front 212.5 put / back 210 put
    assert row["strike_leg1"] == 212.5
    assert row["strike_leg2"] == 210.0
    # Entry: short front 212.5 put (-2.95) + long back 210 put (3.45) = 0.50 debit
    assert round(row["total_entry_cost"], 2) == 0.50
    # Exit: close short front (-0.35) + close long back (1.45) = 1.10
    assert round(row["total_exit_proceeds"], 2) == 1.10
    assert round(row["pct_change"], 2) == 1.20


# =============================================================================
# Short Variant P&L Value Assertions
# =============================================================================


def test_short_call_butterfly_pnl_values(multi_strike_data):
    """Short call butterfly P&L should be opposite of long call butterfly."""
    long_results = long_call_butterfly(multi_strike_data, raw=True, **_BF_CALL_DELTAS)
    short_results = short_call_butterfly(multi_strike_data, raw=True, **_BF_CALL_DELTAS)

    assert not long_results.empty
    assert not short_results.empty

    long_row = long_results.iloc[0]
    short_row = short_results.iloc[0]

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
    long_results = long_put_butterfly(multi_strike_data, raw=True, **_BF_PUT_DELTAS)
    short_results = short_put_butterfly(multi_strike_data, raw=True, **_BF_PUT_DELTAS)

    assert not long_results.empty
    assert not short_results.empty

    long_row = long_results.iloc[0]
    short_row = short_results.iloc[0]

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


# =============================================================================
# Delta Interval Grouping Tests
# =============================================================================


class TestDeltaInterval:
    def test_delta_interval_adds_delta_range_column(self, data_with_delta):
        """delta_interval should add delta_range grouping column to aggregated output."""
        results = long_calls(data_with_delta, delta_interval=0.5, raw=False)
        assert "delta_range" in results.columns
        assert list(results.columns) == single_strike_external_cols + describe_cols


# =============================================================================
# Core Module Coverage — delta_max-only filter (core.py line 164)
# =============================================================================


def test_delta_targeting_selects_closest(data_with_delta):
    """Per-leg delta targeting selects the strike closest to target delta."""
    results = long_calls(
        data_with_delta,
        raw=True,
        leg1_delta=TargetRange(target=0.45, min=0.30, max=0.50),
    )
    # Should select call at 215.0 (delta 0.45, closest to target)
    assert len(results) == 1
    assert results.iloc[0]["option_type"] == "call"


# =============================================================================
# Core Module Coverage — entry_dates signal filter (core.py line 330)
# =============================================================================


def test_entry_dates_filter_valid(data):
    """entry_dates matching fixture date should return same results as unfiltered."""
    unfiltered = long_calls(data, raw=True)
    valid = pd.DataFrame(
        {
            "underlying_symbol": ["SPX"],
            "quote_date": pd.to_datetime(["2018-01-01"]),
        }
    )
    results = long_calls(data, raw=True, entry_dates=valid)
    assert len(results) == len(unfiltered)


def test_entry_dates_filter_invalid(data):
    """entry_dates with no matching date should return empty."""
    invalid = pd.DataFrame(
        {
            "underlying_symbol": ["SPX"],
            "quote_date": pd.to_datetime(["2099-01-01"]),
        }
    )
    results = long_calls(data, raw=True, entry_dates=invalid)
    assert len(results) == 0


# =============================================================================
# Core Module Coverage — exit_dates signal filter (core.py line 337)
# =============================================================================


def test_exit_dates_filter_valid(data):
    """exit_dates matching fixture exit date should return same results as unfiltered."""
    unfiltered = long_calls(data, raw=True)
    valid = pd.DataFrame(
        {
            "underlying_symbol": ["SPX"],
            "quote_date": pd.to_datetime(["2018-01-31"]),
        }
    )
    results = long_calls(data, raw=True, exit_dates=valid)
    assert len(results) == len(unfiltered)


def test_exit_dates_filter_invalid(data):
    """exit_dates with no matching date should return empty."""
    invalid = pd.DataFrame(
        {
            "underlying_symbol": ["SPX"],
            "quote_date": pd.to_datetime(["2099-01-01"]),
        }
    )
    results = long_calls(data, raw=True, exit_dates=invalid)
    assert len(results) == 0


# =============================================================================
# Core Module Coverage — implied_volatility passthrough (core.py line 361)
# =============================================================================


@pytest.fixture(scope="module")
def data_with_iv():
    """Data with implied_volatility and delta columns."""
    from datetime import datetime

    exp_date = datetime(2018, 1, 31)
    quote_dates = [datetime(2018, 1, 1), datetime(2018, 1, 31)]
    cols = [
        "underlying_symbol",
        "underlying_price",
        "option_type",
        "expiration",
        "quote_date",
        "strike",
        "bid",
        "ask",
        "delta",
        "implied_volatility",
    ]
    d = [
        [
            "SPX",
            213.93,
            "call",
            exp_date,
            quote_dates[0],
            212.5,
            7.35,
            7.45,
            0.55,
            0.20,
        ],
        [
            "SPX",
            213.93,
            "call",
            exp_date,
            quote_dates[0],
            215.0,
            6.00,
            6.05,
            0.30,
            0.22,
        ],
        ["SPX", 220, "call", exp_date, quote_dates[1], 212.5, 7.45, 7.55, 0.95, 0.18],
        ["SPX", 220, "call", exp_date, quote_dates[1], 215.0, 4.96, 5.05, 0.85, 0.19],
    ]
    return pd.DataFrame(data=d, columns=cols)


def test_implied_volatility_passthrough(data_with_iv):
    """IV column in input should appear as implied_volatility_entry with correct values."""
    results = long_calls(data_with_iv, raw=True)
    assert "implied_volatility_entry" in results.columns
    # Delta targeting selects 215.0 (delta 0.30), which has IV=0.22
    assert len(results) == 1
    assert results.iloc[0]["implied_volatility_entry"] == 0.22


# =============================================================================
# Core Module Coverage — exit_dte_tolerance on non-calendar (core.py lines 273-289)
# =============================================================================


@pytest.fixture(scope="module")
def data_with_near_exit():
    """Data with exit at DTE=8 for testing exit_dte_tolerance on non-calendar strategies."""
    from datetime import datetime

    exp_date = datetime(2018, 2, 28)
    entry_date = datetime(2018, 1, 1)
    # Exit at DTE=8 (8 days before expiration = Feb 20)
    exit_date = datetime(2018, 2, 20)

    cols = [
        "underlying_symbol",
        "underlying_price",
        "option_type",
        "expiration",
        "quote_date",
        "strike",
        "bid",
        "ask",
        "delta",
    ]
    d = [
        ["SPX", 213.93, "call", exp_date, entry_date, 212.5, 7.35, 7.45, 0.55],
        ["SPX", 213.93, "call", exp_date, entry_date, 215.0, 6.00, 6.05, 0.30],
        ["SPX", 220, "call", exp_date, exit_date, 212.5, 7.45, 7.55, 0.95],
        ["SPX", 220, "call", exp_date, exit_date, 215.0, 4.96, 5.05, 0.85],
    ]
    return pd.DataFrame(data=d, columns=cols)


def test_exit_dte_tolerance_non_calendar(data_with_near_exit):
    """exit_dte_tolerance on non-calendar strategy exercises _get_exits tolerance path."""
    # Data has exit at DTE=8. Request exit_dte=7 with tolerance=2 → range [5,9]
    # DTE=8 is within range and closest to 7, so it should snap to it.
    # The _trim at line 385 keeps DTE >= exit_dte=7, so DTE=8 is kept.
    results = long_calls(
        data_with_near_exit, raw=True, exit_dte=7, exit_dte_tolerance=2
    )
    assert len(results) > 0


def test_calendar_empty_aggregated_output(data):
    """Calendar with no matching expirations should return empty aggregated output."""
    from optopsy.definitions import calendar_spread_external_cols

    results = long_call_calendar(
        data,
        raw=False,
        front_dte_min=20,
        front_dte_max=40,
        back_dte_min=50,
        back_dte_max=70,
        exit_dte=7,
    )
    assert len(results) == 0
    # Should have external cols + describe cols
    assert list(results.columns) == calendar_spread_external_cols + describe_cols


# =============================================================================
# Core Module Coverage — calendar entry_dates / exit_dates filters
# (core.py lines 1065, 1085, 1088)
# =============================================================================


def test_calendar_tolerance_no_nearby_dates(calendar_data):
    """Calendar with tolerance but no nearby exit dates returns empty."""
    # exit_dte=20 means exit 20 days before front exp (2018-01-11)
    # tolerance=1 means look for dates within 1 day of 2018-01-11
    # The fixture only has data on 2018-01-01 (entry) and 2018-01-24 (exit)
    # Neither is within 1 day of 2018-01-11 → empty date_map → empty result
    results = long_call_calendar(
        calendar_data,
        raw=True,
        front_dte_min=20,
        front_dte_max=40,
        back_dte_min=50,
        back_dte_max=70,
        exit_dte=20,
        exit_dte_tolerance=1,
    )
    assert len(results) == 0


def test_calendar_entry_dates_filter_valid(calendar_data):
    """Calendar with valid entry_dates should return same results as unfiltered."""
    cal_kwargs = dict(
        raw=True,
        front_dte_min=20,
        front_dte_max=40,
        back_dte_min=50,
        back_dte_max=70,
        exit_dte=7,
    )
    unfiltered = long_call_calendar(calendar_data, **cal_kwargs)
    valid = pd.DataFrame(
        {
            "underlying_symbol": ["SPX"],
            "quote_date": pd.to_datetime(["2018-01-01"]),
        }
    )
    results = long_call_calendar(calendar_data, entry_dates=valid, **cal_kwargs)
    assert len(results) == len(unfiltered)


def test_calendar_entry_dates_filter_invalid(calendar_data):
    """Calendar with non-matching entry_dates should return empty."""
    invalid = pd.DataFrame(
        {
            "underlying_symbol": ["SPX"],
            "quote_date": pd.to_datetime(["2099-01-01"]),
        }
    )
    results = long_call_calendar(
        calendar_data,
        raw=True,
        entry_dates=invalid,
        front_dte_min=20,
        front_dte_max=40,
        back_dte_min=50,
        back_dte_max=70,
        exit_dte=7,
    )
    assert len(results) == 0


def test_calendar_exit_dates_filter_valid(calendar_data):
    """Calendar with valid exit_dates should return same results as unfiltered."""
    cal_kwargs = dict(
        raw=True,
        front_dte_min=20,
        front_dte_max=40,
        back_dte_min=50,
        back_dte_max=70,
        exit_dte=7,
    )
    unfiltered = long_call_calendar(calendar_data, **cal_kwargs)
    valid = pd.DataFrame(
        {
            "underlying_symbol": ["SPX"],
            "quote_date": pd.to_datetime(["2018-01-24"]),
        }
    )
    results = long_call_calendar(calendar_data, exit_dates=valid, **cal_kwargs)
    assert len(results) == len(unfiltered)


def test_calendar_exit_dates_filter_invalid(calendar_data):
    """Calendar with non-matching exit_dates should return empty."""
    invalid = pd.DataFrame(
        {
            "underlying_symbol": ["SPX"],
            "quote_date": pd.to_datetime(["2099-01-01"]),
        }
    )
    results = long_call_calendar(
        calendar_data,
        raw=True,
        exit_dates=invalid,
        front_dte_min=20,
        front_dte_max=40,
        back_dte_min=50,
        back_dte_max=70,
        exit_dte=7,
    )
    assert len(results) == 0


# =============================================================================
# Short Single-Leg Pct_Change Sign Convention Tests
# =============================================================================


def test_short_calls_pct_change_opposite_of_long(data):
    """Short calls and long calls should have opposite pct_change signs."""
    long_results = long_calls(data, raw=True)
    short_results = short_calls(data, raw=True)
    assert len(long_results) == 1
    assert len(short_results) == 1
    long_pct = long_results.iloc[0]["pct_change"]
    short_pct = short_results.iloc[0]["pct_change"]
    # Opposite sign: long loses when call drops, short gains
    assert round(long_pct, 2) == -round(short_pct, 2)


def test_short_puts_pct_change_opposite_of_long(data):
    """Short puts and long puts should have opposite pct_change signs."""
    long_results = long_puts(data, raw=True)
    short_results = short_puts(data, raw=True)
    long_pct = long_results.iloc[0]["pct_change"]
    short_pct = short_results.iloc[0]["pct_change"]
    assert round(long_pct, 2) == -round(short_pct, 2)


# =============================================================================
# Missing Aggregated Output Tests for Reverse Iron Strategies
# =============================================================================


def test_reverse_iron_condor_aggregated(multi_strike_data):
    """Reverse iron condor aggregated output has correct columns."""
    results = reverse_iron_condor(multi_strike_data)
    assert list(results.columns) == quadruple_strike_external_cols + describe_cols
    assert len(results) > 0


def test_reverse_iron_butterfly_aggregated(multi_strike_data):
    """Reverse iron butterfly aggregated output has correct columns."""
    results = reverse_iron_butterfly(multi_strike_data)
    assert list(results.columns) == quadruple_strike_external_cols + describe_cols
    assert len(results) > 0


# =============================================================================
# Missing Aggregated Output Tests for Short Calendar/Diagonal Variants
# =============================================================================

_CAL_KWARGS = dict(
    front_dte_min=20,
    front_dte_max=40,
    back_dte_min=50,
    back_dte_max=70,
    exit_dte=7,
)


def test_short_put_calendar_aggregated(calendar_data):
    """Short put calendar aggregated output has correct columns."""
    results = short_put_calendar(calendar_data, **_CAL_KWARGS)
    assert list(results.columns) == calendar_spread_external_cols + describe_cols
    assert len(results) > 0


def test_short_call_diagonal_aggregated(calendar_data):
    """Short call diagonal aggregated output has correct columns."""
    results = short_call_diagonal(calendar_data, **_CAL_KWARGS)
    assert list(results.columns) == diagonal_spread_external_cols + describe_cols
    assert len(results) > 0


def test_short_put_diagonal_aggregated(calendar_data):
    """Short put diagonal aggregated output has correct columns."""
    results = short_put_diagonal(calendar_data, **_CAL_KWARGS)
    assert list(results.columns) == diagonal_spread_external_cols + describe_cols
    assert len(results) > 0


# =============================================================================
# Parameter Filter Tests — min_bid_ask and max_entry_dte
# =============================================================================


def test_min_bid_ask_filters_low_spread_options():
    """Options with bid or ask at or below min_bid_ask should be excluded."""
    import datetime

    exp_date = datetime.datetime(2018, 1, 31)
    entry_date = datetime.datetime(2018, 1, 1)
    exit_date = datetime.datetime(2018, 1, 31)
    cols = [
        "underlying_symbol",
        "underlying_price",
        "option_type",
        "expiration",
        "quote_date",
        "strike",
        "bid",
        "ask",
        "delta",
    ]
    d = [
        # Entry — one call with bid just below default min_bid_ask=0.05
        ["SPX", 213.93, "call", exp_date, entry_date, 215.0, 0.04, 0.06, 0.30],
        # Exit
        ["SPX", 220, "call", exp_date, exit_date, 215.0, 4.96, 5.05, 0.85],
    ]
    df = pd.DataFrame(data=d, columns=cols)

    # With default min_bid_ask=0.05, the 215.0 call (bid=0.04) is filtered → no result
    results_default = long_calls(df, raw=True)
    assert len(results_default) == 0, (
        "215.0 call with bid=0.04 should be filtered by min_bid_ask=0.05"
    )

    # With min_bid_ask=0.03, the 215.0 call (bid=0.04 > 0.03) passes → 1 result
    results_low = long_calls(df, raw=True, min_bid_ask=0.03)
    assert len(results_low) == 1
    assert results_low.iloc[0]["strike"] == 215.0


def test_max_entry_dte_filters_far_expirations():
    """Options with DTE above max_entry_dte should be excluded from entry."""
    import datetime

    exp_near = datetime.datetime(2018, 3, 31)  # 89 DTE from entry
    exp_far = datetime.datetime(2018, 5, 31)  # 150 DTE from entry
    entry_date = datetime.datetime(2018, 1, 1)

    cols = [
        "underlying_symbol",
        "underlying_price",
        "option_type",
        "expiration",
        "quote_date",
        "strike",
        "bid",
        "ask",
        "delta",
    ]
    d = [
        # Near expiration (89 DTE) — within default max_entry_dte=90
        ["SPX", 213.93, "call", exp_near, entry_date, 212.5, 7.35, 7.45, 0.30],
        # Far expiration (150 DTE) — beyond default max_entry_dte=90
        ["SPX", 213.93, "call", exp_far, entry_date, 212.5, 9.00, 9.10, 0.30],
        # Exits at expiration
        ["SPX", 220, "call", exp_near, exp_near, 212.5, 7.45, 7.55, 0.95],
        ["SPX", 220, "call", exp_far, exp_far, 212.5, 7.45, 7.55, 0.95],
    ]
    df = pd.DataFrame(data=d, columns=cols)

    near_dte = (exp_near - entry_date).days  # 89

    # Default max_entry_dte=90: near (~89 DTE) passes, far (150 DTE) excluded
    results_default = long_calls(df, raw=True)
    assert len(results_default) == 1, (
        f"Expected only near-expiry result, got {len(results_default)}"
    )
    assert results_default.iloc[0]["dte_entry"] == near_dte

    # With max_entry_dte=160: both expirations should be included
    results_wide = long_calls(df, raw=True, max_entry_dte=160)
    assert len(results_wide) == 2
