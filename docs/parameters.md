# Strategy Parameters

All Optopsy strategies accept a common set of parameters for filtering, grouping, and output formatting. This guide covers all available parameters and their usage.

!!! warning "Strict Parameter Validation"
    Parameters are validated at runtime using Pydantic. This means:

    - **Boolean parameters** (`raw`, `drop_nan`) must be actual `bool` values. `raw=1` or `raw=0` will raise a validation error — use `raw=True` or `raw=False`.
    - **Float parameters** (`min_bid_ask`, `delta_interval`) must be `float` type. `min_bid_ask=5` will be rejected — use `min_bid_ask=5.0`.
    - **Integer parameters** (`max_entry_dte`, `exit_dte`, etc.) reject `float` and `bool` values.
    - **Calendar/diagonal cross-field rules** are enforced: `front_dte_min` must be &le; `front_dte_max`, `back_dte_min` must be &le; `back_dte_max`, and `front_dte_max` must be &lt; `back_dte_min`.

    Validation errors include the field name and constraint for easy debugging.

## Core Parameters

#### Entry and Exit Timing

#### `max_entry_dte`
**Type:** `int` | **Default:** `90`

Maximum days to expiration at strategy entry.

```python
results = op.iron_condor(data, max_entry_dte=45)  # Enter at 45 DTE or less
```

**Use Cases:**
- `max_entry_dte=30` - Short-term trades
- `max_entry_dte=60` - Medium-term trades
- `max_entry_dte=90` - Longer-term positions

---

#### `exit_dte`
**Type:** `int` | **Default:** `0`

Days to expiration when the strategy exits. Use `0` to hold until expiration.

```python
results = op.long_calls(data, max_entry_dte=60, exit_dte=30)  # Exit at 30 DTE
```

**Use Cases:**
- `exit_dte=0` - Hold to expiration
- `exit_dte=21` - Exit 3 weeks before expiration
- `exit_dte=7` - Exit 1 week before expiration

---

#### Filtering Parameters

#### `min_bid_ask`
**Type:** `float` | **Default:** `0.05`

Minimum bid-ask spread required for option liquidity.

```python
results = op.iron_condor(data, min_bid_ask=0.10)  # Require $0.10+ spread
```

**Use Cases:**
- `0.05` - Less liquid underlyings
- `0.10` - Standard liquidity requirement
- `0.20` - High liquidity requirement (SPX, SPY)

---

#### Grouping and Aggregation

#### `dte_interval`
**Type:** `int` | **Default:** `7`

Interval for grouping results by DTE ranges.

```python
results = op.long_calls(data, dte_interval=14)  # Group by 14-day buckets
```

**Examples:**
- `7` - Weekly groupings: (0,7], (7,14], (14,21], ...
- `14` - Bi-weekly groupings: (0,14], (14,28], ...
- `30` - Monthly groupings: (0,30], (30,60], ...

---

#### `delta_interval`
**Type:** `float` | **Default:** `0.05`

Interval for grouping results by delta ranges in aggregated output.

```python
results = op.iron_condor(
    data,
    delta_interval=0.10  # Group by: (0.0,0.1], (0.1,0.2], etc.
)
```

---

#### Output Control

#### `raw`
**Type:** `bool` | **Default:** `False`

Return raw trade data instead of aggregated statistics.

```python
# Aggregated statistics (default)
results = op.iron_condor(data, raw=False)
# Output: ['dte_range', 'delta_range', 'count', 'mean', 'std', ...]

# Raw trade data
trades = op.iron_condor(data, raw=True)
# Output: ['expiration', 'strike_leg1', 'strike_leg2', 'entry', 'exit', 'pct_change', ...]
```

**Use Cases:**
- `raw=False` - Performance statistics, backtesting results
- `raw=True` - Custom analysis, detailed inspection, debugging

---

#### `drop_nan`
**Type:** `bool` | **Default:** `True`

Drop rows with NaN values in the results.

```python
results = op.long_calls(data, drop_nan=False)  # Keep NaN values
```

---

## Per-Leg Delta Targeting

Optopsy uses per-leg delta targeting to select option strikes. Each leg of a strategy has its own delta parameter (`leg1_delta`, `leg2_delta`, etc.) that takes a `TargetRange` value specifying the ideal delta and an acceptable range.

#### `TargetRange`

A `TargetRange` has three fields:

| Field | Description |
|-------|-------------|
| `target` | Ideal delta value (the engine picks the strike closest to this) |
| `min` | Minimum acceptable delta (options below this are excluded) |
| `max` | Maximum acceptable delta (options above this are excluded) |

All values are unsigned (0–1 for delta). The ordering constraint `min <= target <= max` is enforced.

```python
from optopsy import TargetRange

# Target 30-delta options, accepting anything between 20 and 40
delta = TargetRange(target=0.30, min=0.20, max=0.40)
```

You can also pass a plain dict:

```python
results = op.short_puts(
    data,
    leg1_delta={"target": 0.30, "min": 0.20, "max": 0.40}
)
```

#### `leg1_delta` / `leg2_delta` / `leg3_delta` / `leg4_delta`
**Type:** `TargetRange | dict | None` | **Default:** strategy-dependent

Per-leg delta targeting. The number of legs depends on the strategy:

| Strategy Type | Legs Used |
|---------------|-----------|
| Single-leg (calls, puts) | `leg1_delta` |
| Straddles, strangles, vertical spreads | `leg1_delta`, `leg2_delta` |
| Butterflies | `leg1_delta`, `leg2_delta`, `leg3_delta` |
| Iron condors, iron butterflies | `leg1_delta`, `leg2_delta`, `leg3_delta`, `leg4_delta` |
| Covered strategies | `leg1_delta` (stock), `leg2_delta` (option) |

Each strategy has sensible defaults. For example:

| Role | Default Delta |
|------|--------------|
| Standard OTM leg | `target=0.30, min=0.20, max=0.40` |
| ATM leg | `target=0.50, min=0.40, max=0.60` |
| OTM wing | `target=0.10, min=0.05, max=0.20` |
| Deep ITM (stock proxy) | `target=0.80, min=0.60, max=0.95` |

**Examples:**

```python
# Single-leg: target 20-delta puts
results = op.short_puts(
    data,
    leg1_delta={"target": 0.20, "min": 0.15, "max": 0.25}
)

# Iron condor: customize short strike deltas
results = op.iron_condor(
    data,
    leg2_delta={"target": 0.30, "min": 0.25, "max": 0.35},  # short put
    leg3_delta={"target": 0.30, "min": 0.25, "max": 0.35},  # short call
)
```

!!! note "Delta column required"
    Your data must include a `delta` column. This is a **required** column in Optopsy.

---

## Early Exit Parameters

Early exits let you close positions before the scheduled `exit_dte` based on P&L thresholds or a maximum holding period. When an early exit triggers, the `exit_type` column in raw output indicates which condition fired.

#### `stop_loss`
**Type:** `float | None` | **Default:** `None`

Close the position early if unrealized P&L drops to or below this threshold. Must be a **negative** float.

```python
results = op.short_puts(
    data,
    stop_loss=-0.50,  # Close if losing 50% or more
    raw=True
)
```

---

#### `take_profit`
**Type:** `float | None` | **Default:** `None`

Close the position early if unrealized P&L reaches or exceeds this threshold. Must be a **positive** float.

```python
results = op.iron_condor(
    data,
    take_profit=0.50,  # Close if gaining 50% or more
    raw=True
)
```

---

#### `max_hold_days`
**Type:** `int | None` | **Default:** `None`

Close the position after holding for this many calendar days, regardless of P&L. Must be a positive integer.

```python
results = op.short_puts(
    data,
    max_hold_days=21,  # Exit after 21 calendar days
    raw=True
)
```

---

#### `exit_type` Column Values

When early exits are enabled and `raw=True`, the output includes an `exit_type` column:

| Value | Meaning |
|-------|---------|
| `stop_loss` | Position hit the stop-loss threshold |
| `take_profit` | Position hit the take-profit threshold |
| `max_hold` | Position reached the maximum holding period |
| `expiration` | Position exited at scheduled `exit_dte` (no early exit triggered) |

**Priority:** If multiple conditions trigger on the same day, priority is: `stop_loss` > `take_profit` > `max_hold`.

---

## Commission Parameters

#### `commission`
**Type:** `Commission | float | None` | **Default:** `None`

Commission fee structure applied to entry and exit trades. Accepts three forms:

**Float shorthand** — interpreted as per-contract fee:

```python
results = op.short_puts(data, commission=0.65)  # $0.65 per contract
```

**Commission object** — full fee structure:

```python
from optopsy import Commission

results = op.iron_condor(
    data,
    commission=Commission(
        per_contract=0.65,  # Per option contract
        base_fee=9.99,      # Flat fee per trade
    )
)
```

**Commission fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `per_contract` | `float` | `0.0` | Fee per option contract |
| `per_share` | `float` | `0.0` | Fee per share (for stock legs in covered strategies) |
| `base_fee` | `float` | `0.0` | Flat fee per trade |
| `min_fee` | `float` | `0.0` | Minimum fee per trade |

When set, commission costs are subtracted from P&L in the output.

---

## Slippage Parameters

#### `slippage`
**Type:** `str` | **Default:** `'mid'`

Slippage model for fill price calculation.

```python
results = op.long_calls(data, slippage='liquidity')
```

**Options:**

| Mode | Description | Buy Fill | Sell Fill | Best For |
|------|-------------|----------|-----------|----------|
| `'mid'` | Mid-price between bid/ask | (bid+ask)/2 | (bid+ask)/2 | Ideal/optimistic |
| `'spread'` | Worst-case spread | Ask | Bid | Conservative |
| `'liquidity'` | Volume-based dynamic | Dynamic | Dynamic | Realistic (volume) |
| `'per_leg'` | Scales with leg count | Dynamic | Dynamic | Realistic (complexity) |

---

#### `fill_ratio` (Liquidity Mode Only)
**Type:** `float` | **Default:** `0.5`

Base fill ratio for liquidity-based slippage (0.0 = bid/ask, 1.0 = ask/bid).

```python
results = op.iron_condor(
    data,
    slippage='liquidity',
    fill_ratio=0.3  # More conservative fill (30% through spread)
)
```

**Examples:**
- `0.0` - Worst case (buy at ask, sell at bid)
- `0.5` - Mid-point (default)
- `1.0` - Best case (buy at bid, sell at ask - unrealistic)

---

#### `reference_volume` (Liquidity Mode Only)
**Type:** `int` | **Default:** `1000`

Volume threshold for determining liquid options in liquidity mode.

```python
results = op.short_strangles(
    data,
    slippage='liquidity',
    reference_volume=5000  # Higher threshold for SPX
)
```

**Guidelines:**
- `500-1000` - Less liquid underlyings
- `1000-2000` - Standard liquidity (default)
- `5000+` - Highly liquid (SPX, SPY, QQQ)

**Note:** Requires `volume` or `open_interest` column in your data.

---

#### `per_leg_slippage` (Per-Leg Mode Only)
**Type:** `float` | **Default:** `0.073`

Additive penalty per additional leg beyond the first. The effective fill ratio
increases with strategy complexity:
`effective_ratio = min(fill_ratio + per_leg_slippage * (num_legs - 1), 1.0)`

```python
results = op.iron_condor(
    data,
    slippage='per_leg',
    fill_ratio=0.25,          # 1-leg base: 75% edge retained
    per_leg_slippage=0.073,   # penalty per extra leg
)
# 1-leg: ratio=0.250 (75% edge), 2-leg: 0.323 (~68%), 3-leg: 0.396 (~60%), 4-leg: 0.469 (~53%)
```

**Notes:**
- All legs in a strategy receive the same effective ratio (package pricing).
- The ratio is clamped to 1.0 (equivalent to `'spread'` mode).
- Does not require a `volume` column.

---

## Calendar & Diagonal Parameters

Calendar and diagonal spreads use different timing parameters:

#### `front_dte_min` / `front_dte_max`
**Type:** `int` | **Default:** `20` / `40`

DTE range for the front-month leg.

```python
results = op.long_call_calendar(
    data,
    front_dte_min=25,
    front_dte_max=35  # Front leg between 25-35 DTE
)
```

---

#### `back_dte_min` / `back_dte_max`
**Type:** `int` | **Default:** `50` / `90`

DTE range for the back-month leg.

```python
results = op.long_call_diagonal(
    data,
    back_dte_min=60,
    back_dte_max=120  # Back leg between 60-120 DTE
)
```

---

## Complete Example

Combining multiple parameters:

```python
import optopsy as op

data = op.csv_data('SPX_options.csv')

results = op.iron_condor(
    data,
    # Timing
    max_entry_dte=45,
    exit_dte=21,

    # Per-leg delta targeting
    leg2_delta={"target": 0.20, "min": 0.15, "max": 0.25},
    leg3_delta={"target": 0.20, "min": 0.15, "max": 0.25},

    # Filtering
    min_bid_ask=0.15,

    # Grouping
    dte_interval=7,
    delta_interval=0.05,

    # Slippage
    slippage='liquidity',
    fill_ratio=0.5,
    reference_volume=5000,

    # Early exits
    stop_loss=-1.0,
    take_profit=0.50,

    # Commission
    commission=0.65,

    # Output
    raw=False,
    drop_nan=True
)

print(results.head())
```

## Default Values Reference

#### Standard Strategies

```python
default_params = {
    "dte_interval": 7,
    "max_entry_dte": 90,
    "exit_dte": 0,
    "min_bid_ask": 0.05,
    "delta_interval": 0.05,
    "leg1_delta": None,   # strategy-specific defaults applied by helpers
    "leg2_delta": None,
    "leg3_delta": None,
    "leg4_delta": None,
    "drop_nan": True,
    "raw": False,
    "slippage": "mid",
    "fill_ratio": 0.5,
    "reference_volume": 1000,
    "per_leg_slippage": 0.073,
    "stop_loss": None,
    "take_profit": None,
    "max_hold_days": None,
    "commission": None,
}
```

#### Calendar & Diagonal Strategies

```python
calendar_default_params = {
    "front_dte_min": 20,
    "front_dte_max": 40,
    "back_dte_min": 50,
    "back_dte_max": 90,
    "exit_dte": 7,
    "dte_interval": 7,
    "min_bid_ask": 0.05,
    "delta_interval": 0.05,
    "drop_nan": True,
    "raw": False,
    "slippage": "mid",
    "fill_ratio": 0.5,
    "reference_volume": 1000,
    "per_leg_slippage": 0.073,
}
```

## Next Steps

- See [Examples](examples.md) for real-world parameter usage
- Explore [Strategies](strategies.md) to understand strategy-specific considerations
- Review [API Reference](api-reference.md) for function signatures
