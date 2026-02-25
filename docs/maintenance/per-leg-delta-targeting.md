# Per-Leg Delta Targeting

## Problem

Multi-leg strategies (spreads, condors, etc.) select strikes via OTM percentage filtering, then combinatorially join all possible leg combinations. When two legs land on nearly identical strikes, the net entry cost approaches zero, producing absurd `pct_change` values. OTM% is not how traders select strikes -- delta targeting is industry standard ("sell the 30-delta put, buy the 16-delta put").

## Solution

Add per-leg delta targeting via `leg*_delta` parameters. Each leg gets a `TargetRange` with `target`, `min`, and `max` delta values (inspired by [ORATS backtest API](https://docs.orats.io/backtest-api-guide/parameters.html)). This selects the closest-delta option per leg on each entry date, replacing the combinatorial join with targeted 1:1 selection.

## API

```python
from optopsy import TargetRange

# Each leg gets its own TargetRange with target, min, max (unsigned, 0-1)
op.short_put_spread(
    data,
    leg1_delta=TargetRange(target=0.30, min=0.25, max=0.35),
    leg2_delta=TargetRange(target=0.16, min=0.10, max=0.20),
)

op.iron_condor(
    data,
    leg1_delta=TargetRange(target=0.10, min=0.05, max=0.15),
    leg2_delta=TargetRange(target=0.20, min=0.15, max=0.25),
    leg3_delta=TargetRange(target=0.20, min=0.15, max=0.25),
    leg4_delta=TargetRange(target=0.10, min=0.05, max=0.15),
)

op.long_calls(
    data,
    leg1_delta=TargetRange(target=0.30, min=0.25, max=0.35),
)

# Mutually exclusive with delta_min/delta_max (raises ValueError)
```

Delta values are unsigned (0-1). The system determines call vs put from `leg_def` and matches against `abs(delta)`.

### TargetRange

```python
class TargetRange(BaseModel):
    target: float  # Target delta (0-1, unsigned)
    min: float     # Minimum acceptable delta (0-1, unsigned)
    max: float     # Maximum acceptable delta (0-1, unsigned)
    # Validates: 0 < min <= target <= max <= 1
```

## Files Modified

| File | Change |
|---|---|
| `optopsy/types.py` | Add `TargetRange` model. Add `leg1_delta` through `leg4_delta` fields to `StrategyParamsDict` and `StrategyParams`. Model validator: mutually exclusive with `delta_min`/`delta_max`. |
| `optopsy/checks.py` | Update `_requires_delta()` to also check for `leg*_delta` params |
| `optopsy/filters.py` | New `_select_closest_delta(data, delta_target)` -- filters by `[min, max]` range, then groups by `(underlying_symbol, quote_date, expiration, option_type)` and picks row with `abs(delta)` closest to `target` |
| `optopsy/evaluation.py` | New `_evaluate_options_by_delta()` and `_evaluate_all_options_by_delta()` -- entry/exit matching pipeline that skips OTM% filtering and uses delta selection instead |
| `optopsy/core.py` | New `_process_strategy_delta_targeted()` -- evaluates each leg independently with its own `TargetRange`, joins via `_strategy_engine()`. `_process_strategy()` branches here when any `leg*_delta` is present |
| `optopsy/output.py` | Include `delta_entry_legN` columns in raw output when present |
| `optopsy/__init__.py` | Export `TargetRange` |

## How It Works

### Existing Path (OTM%)

1. Filter all options by OTM% range
2. Combinatorially join all valid strikes across legs
3. Apply rules (ascending strikes, equal wings, etc.)
4. Calculate P&L

### New Path (Per-Leg Delta)

1. For each leg independently:
   - Filter by option type (call/put from `leg_def`)
   - Apply `min_bid_ask` filter
   - Filter to options within `[TargetRange.min, TargetRange.max]` abs(delta) range
   - Group by `(symbol, quote_date, expiration, option_type)`
   - Select the single row with `abs(delta)` closest to `TargetRange.target`
2. Join legs on shared columns (symbol, expiration, DTE range, etc.)
   - `otm_pct_range` is stripped from `join_on` since legs use different OTM levels
   - `delta_range_legN` replaces `otm_pct_range_legN` in grouping columns
3. Apply rules and calculate P&L via existing `_strategy_engine()` (reused, not duplicated)

### Key Design Decisions

- **ORATS-inspired per-leg structure**: Each leg gets its own `TargetRange` with target/min/max, mirroring ORATS' `strikeSelection.type=absDelta` approach.
- **Per-leg evaluation**: Each leg gets its own evaluation call. This avoids combinatorial explosion and ensures each leg lands on a specific strike.
- **Unsigned deltas**: Users specify unsigned values (e.g., 0.30). The system uses `abs(delta)` for matching, since put deltas are negative and call deltas are positive.
- **Min/max range filtering**: Options outside the `[min, max]` range are excluded before closest-to-target selection. This prevents landing on unreasonable strikes when the target delta isn't available.
- **Mutual exclusivity**: `leg*_delta` cannot be combined with `delta_min`/`delta_max`. Enforced by a Pydantic model validator.

## Tests

- `tests/test_delta_targeting.py` -- single-leg, vertical spread, iron condor, straddle, validation errors, raw/aggregated output
- `tests/test_types_validation.py` -- TargetRange and leg*_delta validation edge cases
- `tests/conftest.py` -- `multi_strike_data_with_delta` fixture with realistic delta values

## Out of Scope

- Calendar/diagonal spreads (separate processing path)
- Removing the existing OTM% path
