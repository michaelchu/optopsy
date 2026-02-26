"""Tests for commission modeling: Commission model, calculation, and strategy integration."""

import datetime

import numpy as np
import pandas as pd
import pytest

from optopsy.pricing import _calculate_commission
from optopsy.strategies import (
    covered_call,
    iron_condor,
    long_call_calendar,
    long_call_spread,
    long_calls,
    long_puts,
    protective_put,
    short_puts,
)
from optopsy.strategies._helpers import Side
from optopsy.types import Commission, StrategyParams, TargetRange

# =============================================================================
# Commission Model Tests
# =============================================================================


class TestCommissionModel:
    def test_default_values(self):
        c = Commission()
        assert c.per_contract == 0.0
        assert c.per_share == 0.0
        assert c.base_fee == 0.0
        assert c.min_fee == 0.0

    def test_per_contract_only(self):
        c = Commission(per_contract=0.65)
        assert c.per_contract == 0.65

    def test_full_config(self):
        c = Commission(per_contract=0.65, per_share=0.005, base_fee=9.99, min_fee=4.95)
        assert c.per_contract == 0.65
        assert c.per_share == 0.005
        assert c.base_fee == 9.99
        assert c.min_fee == 4.95

    def test_rejects_negative_per_contract(self):
        with pytest.raises(Exception):
            Commission(per_contract=-0.65)

    def test_rejects_negative_base_fee(self):
        with pytest.raises(Exception):
            Commission(base_fee=-1.0)

    def test_rejects_extra_fields(self):
        with pytest.raises(Exception):
            Commission(per_contract=0.65, unknown=1.0)


class TestStrategyParamsCommission:
    def test_none_default(self):
        params = StrategyParams.model_validate({})
        assert params.commission is None

    def test_float_coercion(self):
        params = StrategyParams.model_validate({"commission": 0.65})
        assert isinstance(params.commission, Commission)
        assert params.commission.per_contract == 0.65

    def test_int_coercion(self):
        params = StrategyParams.model_validate({"commission": 1})
        assert isinstance(params.commission, Commission)
        assert params.commission.per_contract == 1.0

    def test_dict_coercion(self):
        params = StrategyParams.model_validate(
            {"commission": {"per_contract": 0.65, "base_fee": 9.99}}
        )
        assert isinstance(params.commission, Commission)
        assert params.commission.per_contract == 0.65
        assert params.commission.base_fee == 9.99

    def test_commission_instance(self):
        c = Commission(per_contract=0.65)
        params = StrategyParams.model_validate({"commission": c})
        assert params.commission is c

    def test_rejects_bool(self):
        with pytest.raises(Exception):
            StrategyParams.model_validate({"commission": True})

    def test_rejects_string(self):
        with pytest.raises(Exception):
            StrategyParams.model_validate({"commission": "0.65"})


# =============================================================================
# Commission Calculation Tests
# =============================================================================


def _dummy_filter(data):
    return data


def _make_leg_def(num_legs, quantities=None):
    """Helper to create leg definitions for testing."""
    if quantities is None:
        quantities = [1] * num_legs
    return [(Side.long, _dummy_filter, q) for q in quantities]


class TestCalculateCommission:
    def test_per_contract_single_leg(self):
        leg_def = _make_leg_def(1)
        comm = {"per_contract": 0.65, "per_share": 0.0, "base_fee": 0.0, "min_fee": 0.0}
        assert _calculate_commission(leg_def, comm) == 0.65

    def test_per_contract_two_legs(self):
        leg_def = _make_leg_def(2)
        comm = {"per_contract": 0.65, "per_share": 0.0, "base_fee": 0.0, "min_fee": 0.0}
        assert _calculate_commission(leg_def, comm) == 1.30

    def test_per_contract_four_legs(self):
        leg_def = _make_leg_def(4)
        comm = {"per_contract": 0.65, "per_share": 0.0, "base_fee": 0.0, "min_fee": 0.0}
        assert _calculate_commission(leg_def, comm) == 2.60

    def test_base_fee_plus_per_contract(self):
        leg_def = _make_leg_def(1)
        comm = {
            "per_contract": 0.65,
            "per_share": 0.0,
            "base_fee": 9.99,
            "min_fee": 0.0,
        }
        assert _calculate_commission(leg_def, comm) == pytest.approx(10.64)

    def test_min_fee_kicks_in(self):
        leg_def = _make_leg_def(1)
        comm = {
            "per_contract": 0.10,
            "per_share": 0.0,
            "base_fee": 0.0,
            "min_fee": 4.95,
        }
        # 0.10 * 1 = 0.10 < 4.95, so min_fee wins
        assert _calculate_commission(leg_def, comm) == 4.95

    def test_min_fee_does_not_kick_in(self):
        leg_def = _make_leg_def(10)
        comm = {
            "per_contract": 0.65,
            "per_share": 0.0,
            "base_fee": 0.0,
            "min_fee": 4.95,
        }
        # 0.65 * 10 = 6.50 > 4.95
        assert _calculate_commission(leg_def, comm) == 6.50

    def test_per_share_stock_leg(self):
        leg_def = _make_leg_def(1)
        comm = {
            "per_contract": 0.65,
            "per_share": 0.005,
            "base_fee": 0.0,
            "min_fee": 0.0,
        }
        result = _calculate_commission(
            leg_def, comm, has_stock_leg=True, num_shares=100
        )
        # 0.65 (option) + 0.005 * 100 (stock) = 1.15
        assert result == pytest.approx(1.15)

    def test_no_stock_leg_ignores_per_share(self):
        leg_def = _make_leg_def(1)
        comm = {
            "per_contract": 0.65,
            "per_share": 0.005,
            "base_fee": 0.0,
            "min_fee": 0.0,
        }
        result = _calculate_commission(leg_def, comm, has_stock_leg=False)
        assert result == 0.65

    def test_quantity_multiplier(self):
        leg_def = _make_leg_def(1, quantities=[2])
        comm = {"per_contract": 0.65, "per_share": 0.0, "base_fee": 0.0, "min_fee": 0.0}
        # quantity=2 means 2 contracts
        assert _calculate_commission(leg_def, comm) == 1.30

    def test_all_zero_returns_zero(self):
        leg_def = _make_leg_def(2)
        comm = {"per_contract": 0.0, "per_share": 0.0, "base_fee": 0.0, "min_fee": 0.0}
        assert _calculate_commission(leg_def, comm) == 0.0


# =============================================================================
# Strategy Integration Tests
# =============================================================================

_DELTA = dict(
    leg1_delta=TargetRange(target=0.30, min=0.20, max=0.40),
)
_SPREAD_DELTAS = dict(
    leg1_delta=TargetRange(target=0.50, min=0.40, max=0.60),
    leg2_delta=TargetRange(target=0.30, min=0.20, max=0.40),
)
_IC_DELTAS = dict(
    leg1_delta=TargetRange(target=0.35, min=0.25, max=0.45),
    leg2_delta=TargetRange(target=0.20, min=0.15, max=0.30),
    leg3_delta=TargetRange(target=0.20, min=0.15, max=0.30),
    leg4_delta=TargetRange(target=0.35, min=0.25, max=0.45),
)


class TestSingleLegCommission:
    def test_long_calls_no_commission_unchanged(self, data):
        """No commission should produce identical results."""
        result_default = long_calls(data, raw=True, **_DELTA)
        result_none = long_calls(data, raw=True, commission=None, **_DELTA)
        pd.testing.assert_frame_equal(result_default, result_none)

    def test_long_calls_with_commission_has_column(self, data):
        result = long_calls(data, raw=True, commission=0.65, **_DELTA)
        assert "total_commission" in result.columns

    def test_long_calls_commission_reduces_pct_change(self, data):
        result_no = long_calls(data, raw=True, **_DELTA)
        result_yes = long_calls(data, raw=True, commission=0.65, **_DELTA)
        if not result_no.empty and not result_yes.empty:
            # pct_change should be lower (worse) with commission
            np.testing.assert_array_less(
                result_yes["pct_change"].values,
                result_no["pct_change"].values,
            )

    def test_long_calls_commission_value(self, data):
        result = long_calls(data, raw=True, commission=0.65, **_DELTA)
        if not result.empty:
            # Single leg, 1 contract, round-trip = 0.65 * 2 = 1.30
            assert (result["total_commission"] == 1.30).all()

    def test_long_puts_with_commission(self, data):
        result = long_puts(data, raw=True, commission=0.65, **_DELTA)
        assert "total_commission" in result.columns

    def test_short_puts_with_commission(self, data):
        result = short_puts(data, raw=True, commission=0.65, **_DELTA)
        assert "total_commission" in result.columns

    def test_aggregated_output_excludes_commission_col(self, data):
        """Aggregated (non-raw) output should not have total_commission column."""
        result = long_calls(data, raw=False, commission=0.65, **_DELTA)
        assert "total_commission" not in result.columns


class TestMultiLegCommission:
    def test_spread_commission_column(self, data):
        result = long_call_spread(data, raw=True, commission=0.65, **_SPREAD_DELTAS)
        if not result.empty:
            assert "total_commission" in result.columns
            # 2 legs, 1 contract each, round-trip = (0.65 * 2) * 2 = 2.60
            assert (result["total_commission"] == 2.60).all()

    def test_spread_commission_reduces_pct_change(self, data):
        result_no = long_call_spread(data, raw=True, **_SPREAD_DELTAS)
        result_yes = long_call_spread(data, raw=True, commission=0.65, **_SPREAD_DELTAS)
        if not result_no.empty and not result_yes.empty:
            np.testing.assert_array_less(
                result_yes["pct_change"].values,
                result_no["pct_change"].values,
            )

    def test_iron_condor_commission(self, multi_strike_data):
        result = iron_condor(multi_strike_data, raw=True, commission=0.65, **_IC_DELTAS)
        if not result.empty:
            assert "total_commission" in result.columns
            # 4 legs, round-trip = (0.65 * 4) * 2 = 5.20
            assert (result["total_commission"] == 5.20).all()

    def test_base_fee_plus_per_contract(self, data):
        comm = Commission(per_contract=0.65, base_fee=9.99)
        result = long_call_spread(data, raw=True, commission=comm, **_SPREAD_DELTAS)
        if not result.empty:
            # 2 contracts: (9.99 + 0.65*2) * 2 = 11.29 * 2 = 22.58
            np.testing.assert_allclose(result["total_commission"].values, 22.58)

    def test_min_fee_commission(self, data):
        comm = Commission(per_contract=0.10, min_fee=4.95)
        result = long_call_spread(data, raw=True, commission=comm, **_SPREAD_DELTAS)
        if not result.empty:
            # 2 contracts: max(0.10*2, 4.95) = 4.95 per side, 4.95 * 2 = 9.90
            assert (result["total_commission"] == 9.90).all()


class TestCalendarCommission:
    def test_calendar_with_commission(self, calendar_data):
        delta = dict(leg1_delta=TargetRange(target=0.50, min=0.35, max=0.65))
        result_no = long_call_calendar(calendar_data, raw=True, **delta)
        result_yes = long_call_calendar(
            calendar_data, raw=True, commission=0.65, **delta
        )
        if not result_no.empty and not result_yes.empty:
            assert "total_commission" in result_yes.columns
            # 2 legs, round-trip = (0.65 * 2) * 2 = 2.60
            assert (result_yes["total_commission"] == 2.60).all()


@pytest.fixture(scope="module")
def stock_data():
    """Stock data matching the `data` fixture dates for covered call/protective put."""
    return pd.DataFrame(
        {
            "underlying_symbol": ["SPX", "SPX"],
            "quote_date": [
                datetime.datetime(2018, 1, 1),
                datetime.datetime(2018, 1, 31),
            ],
            "close": [213.93, 220.0],
        }
    )


class TestCoveredCommission:
    def test_covered_call_per_contract_only(self, data, stock_data):
        result = covered_call(
            data,
            stock_data=stock_data,
            raw=True,
            commission=0.65,
            leg2_delta=TargetRange(target=0.30, min=0.20, max=0.40),
        )
        if not result.empty:
            assert "total_commission" in result.columns
            # 1 option contract, no per_share, round-trip = 0.65 * 2 = 1.30
            assert (result["total_commission"] == 1.30).all()

    def test_covered_call_with_per_share(self, data, stock_data):
        comm = Commission(per_contract=0.65, per_share=0.005)
        result = covered_call(
            data,
            stock_data=stock_data,
            raw=True,
            commission=comm,
            leg2_delta=TargetRange(target=0.30, min=0.20, max=0.40),
        )
        if not result.empty:
            assert "total_commission" in result.columns
            # (0.65 + 0.005*100) * 2 = 1.15 * 2 = 2.30
            assert (result["total_commission"] == 2.30).all()

    def test_protective_put_with_commission(self, data, stock_data):
        comm = Commission(per_contract=0.65, per_share=0.005)
        result = protective_put(
            data,
            stock_data=stock_data,
            raw=True,
            commission=comm,
            leg2_delta=TargetRange(target=0.30, min=0.20, max=0.40),
        )
        if not result.empty:
            assert "total_commission" in result.columns

    def test_covered_call_no_commission_unchanged(self, data, stock_data):
        delta = dict(leg2_delta=TargetRange(target=0.30, min=0.20, max=0.40))
        result_default = covered_call(data, stock_data=stock_data, raw=True, **delta)
        result_none = covered_call(
            data, stock_data=stock_data, raw=True, commission=None, **delta
        )
        if not result_default.empty:
            pd.testing.assert_frame_equal(result_default, result_none)


class TestBackwardCompatibility:
    def test_no_commission_matches_original(self, data):
        """Without commission, results must be identical to pre-commission code."""
        result_a = long_calls(data, raw=True, **_DELTA)
        result_b = long_calls(data, raw=True, commission=None, **_DELTA)
        pd.testing.assert_frame_equal(result_a, result_b)
        assert "total_commission" not in result_a.columns

    def test_zero_commission_matches_original(self, data):
        """Zero commission should produce identical pct_change."""
        result_a = long_calls(data, raw=True, **_DELTA)
        result_b = long_calls(data, raw=True, commission=Commission(), **_DELTA)
        if not result_a.empty and not result_b.empty:
            # pct_change should be the same
            np.testing.assert_array_almost_equal(
                result_a["pct_change"].values,
                result_b["pct_change"].values,
            )
