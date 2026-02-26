# Commission Modeling: Per-Contract and Per-Share Commissions

## Context

Optopsy currently has no commission modeling. Real broker fee structures include base fees per trade, per-contract fees, minimum fees, and per-share fees for stock legs. This feature adds a flexible `Commission` model that supports all common broker fee structures while keeping the simple case easy (`commission=0.65`).

## Commission Model

New Pydantic model in `types.py`:

```python
class Commission(BaseModel):
    per_contract: float = 0.0   # e.g. $0.65 per option contract
    per_share: float = 0.0      # e.g. $0.005 per share (stock legs)
    base_fee: float = 0.0       # e.g. $9.99 flat fee per trade
    min_fee: float = 0.0        # e.g. $4.95 minimum per trade
```

### Fee Formula

Per trade side (entry or exit):

```
option_fee = max(base_fee + per_contract * total_contracts, min_fee)
stock_fee  = per_share * num_shares
side_commission = option_fee + stock_fee
```

Applied at both entry and exit: `total_commission = 2 * side_commission`.

### Supported Broker Fee Structures

| Broker Model | Configuration |
|---|---|
| Flat per-contract | `Commission(per_contract=0.65)` |
| Base fee + per-contract | `Commission(per_contract=0.65, base_fee=9.99)` |
| Min fee + per-contract | `Commission(per_contract=0.65, min_fee=4.95)` |
| Per-share (stock legs) | `Commission(per_contract=0.65, per_share=0.005)` |
| Combined | `Commission(per_contract=0.65, base_fee=9.99, per_share=0.005)` |

### API Convenience

A bare float is coerced to `Commission(per_contract=float_value)`:

```python
# Simple: just a float means per-contract
op.long_calls(data, commission=0.65)

# Full control: Commission object
op.long_calls(data, commission=Commission(per_contract=0.65, base_fee=9.99))

# Dict also works
op.long_calls(data, commission={"per_contract": 0.65, "base_fee": 9.99})
```

## P&L Semantics

- `total_entry_cost` and `total_exit_proceeds` remain **pure option/stock pricing** (no commission baked in)
- `total_commission` is a new column showing the round-trip commission for that trade
- `pct_change` reflects the **net** return after commission: `(exit - entry - commission) / |entry|`
- When `commission` is `None` or all zeros, behavior is identical to current code (backward compatible)

## Implementation

### 1. `optopsy/types.py` -- Add `Commission` model + field

- Add `Commission` Pydantic model (see above)
- Add `commission: Optional[Union[Commission, float]] = None` to `StrategyParams` (line ~137)
- Add `field_validator("commission")` that coerces float/dict to `Commission`
- Add `commission` to `StrategyParamsDict` and `CalendarStrategyParamsDict`
- `CalendarStrategyParams` inherits the field from `StrategyParams`

### 2. `optopsy/pricing.py` -- Commission calculation + P&L integration

- Add `_calculate_commission(leg_def, commission_dict, has_stock_leg=False, num_shares=100) -> float` that implements the fee formula
- Modify `_assign_profit()` (line 142): add `commission=None` parameter
  - After computing `total_entry_cost`/`total_exit_proceeds` (lines 158-159), if commission is set:
    - Compute `total_commission` via `_calculate_commission()` x 2
    - Add `total_commission` column to DataFrame
    - Adjust `pct_change` to account for commission: `(exit - entry - commission) / |entry|`
  - `total_entry_cost` and `total_exit_proceeds` stay as pure option pricing (commission is tracked separately)

### 3. `optopsy/core.py` -- Thread commission through pipeline

- `_merge_legs()` (line 57): add `commission=None`, pass to `_assign_profit()`
- `_strategy_engine()` (line 81): add `commission=None`
  - Single-leg path (lines 139-143): apply commission to `pct_change` if set, add `total_commission` column
  - Multi-leg path: pass to `_merge_legs()`
- `_process_strategy()` (line 157): extract `commission` from validated params, convert to dict via `model_dump()`, pass to `_strategy_engine()` / `_merge_legs()` calls at lines 228-234 and 244-252
- `_process_calendar_strategy()` (line 262): extract commission from params, pass to `_calculate_calendar_pnl()` at lines 370-376

### 4. `optopsy/calendar.py` -- Calendar/diagonal commission support

- `_calculate_calendar_pnl()` (line 249): add `commission=None` parameter
  - After computing `total_entry_cost`/`total_exit_proceeds` (lines 328-329), apply commission same pattern as `_assign_profit()`

### 5. `optopsy/strategies/_helpers.py` -- Stock-leg commission (covered call / protective put)

- `_covered_with_stock()` (line 286): extract commission from kwargs/params
  - After computing `total_entry`/`total_exit` (lines 385-386), call `_calculate_commission()` with `has_stock_leg=True, num_shares=100`
  - Add `total_commission` to output DataFrame, adjust `pct_change` (lines 400-403)

### 6. `optopsy/output.py` -- Include commission in raw output

- In `_format_output()` (line 90): add `"total_commission"` to the optional column list alongside `"implied_volatility_entry"` and `"delta_entry"`
- In `_format_calendar_output()` (line 130): same treatment for raw output

### 7. `optopsy/__init__.py` -- Export Commission

- Add `Commission` to imports from `.types` and to `__all__`

### 8. `tests/test_commission.py` -- Comprehensive tests

- **Commission model**: float coercion, dict coercion, negative values rejected, all-zero = no effect
- **`_calculate_commission()`**: per-contract only, base+per-contract, min fee kicks in, per-share, combined
- **Single-leg integration**: `long_calls()` with/without commission, verify `pct_change` lower with commission, `total_commission` column present
- **Multi-leg integration**: spreads, butterflies, condors
- **Calendar integration**: calendar spreads with commission
- **Covered call / protective put**: commission with `per_share` for stock leg
- **Backward compatibility**: no commission param = identical results to current behavior

## File Summary

| File | Change |
|------|--------|
| `optopsy/types.py` | Add `Commission` model, add `commission` field to param models/TypedDicts |
| `optopsy/pricing.py` | Add `_calculate_commission()`, modify `_assign_profit()` |
| `optopsy/core.py` | Thread `commission` through `_strategy_engine`, `_merge_legs`, `_process_strategy`, `_process_calendar_strategy` |
| `optopsy/calendar.py` | Add `commission` param to `_calculate_calendar_pnl()` |
| `optopsy/strategies/_helpers.py` | Apply commission in `_covered_with_stock()` |
| `optopsy/output.py` | Include `total_commission` as optional raw column |
| `optopsy/__init__.py` | Export `Commission` |
| `tests/test_commission.py` | New test file |

## Verification

```bash
# Run all tests (existing + new)
uv run pytest tests/ -v

# Run only commission tests
uv run pytest tests/test_commission.py -v

# Verify backward compatibility (all existing tests pass unchanged)
uv run pytest tests/test_strategies.py -v

# Lint + format
uv run ruff check optopsy/ tests/
uv run ruff format --check optopsy/ tests/
```
