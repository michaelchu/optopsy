# Strategy Parameters

All Optopsy strategies accept a common set of parameters for filtering, grouping, and output formatting. This guide covers all available parameters and their usage.

## Core Parameters

### Entry and Exit Timing

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

### Filtering Parameters

#### `max_otm_pct`
**Type:** `float` | **Default:** `0.5`

Maximum out-of-the-money percentage for option selection.

```python
results = op.short_puts(data, max_otm_pct=0.20)  # Max 20% OTM
```

**Examples:**
- `0.05` - Near ATM options (5% OTM max)
- `0.20` - Moderately OTM (20% OTM max)
- `0.50` - Wide range (50% OTM max)

**Calculation:**
```python
# For calls: (strike - underlying_price) / underlying_price
# For puts: (underlying_price - strike) / underlying_price
```

---

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

### Grouping and Aggregation

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

#### `otm_pct_interval`
**Type:** `float` | **Default:** `0.05`

Interval for grouping results by OTM percentage ranges.

```python
results = op.short_strangles(data, otm_pct_interval=0.10)  # 10% OTM buckets
```

**Examples:**
- `0.05` - Fine-grained: (0.0, 0.05], (0.05, 0.10], ...
- `0.10` - Coarse buckets: (0.0, 0.10], (0.10, 0.20], ...

---

### Output Control

#### `raw`
**Type:** `bool` | **Default:** `False`

Return raw trade data instead of aggregated statistics.

```python
# Aggregated statistics (default)
results = op.iron_condor(data, raw=False)
# Output: ['dte_range', 'otm_pct_range', 'count', 'mean', 'std', ...]

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

## Greeks Parameters

### Delta Filtering

#### `delta_min` / `delta_max`
**Type:** `float` | **Default:** `None`

Filter options by delta range.

```python
# Target 30-delta options
results = op.short_puts(
    data,
    delta_min=0.25,
    delta_max=0.35
)
```

**Common Delta Ranges:**
- `0.15-0.20` - 1 standard deviation OTM (~15-20% probability ITM)
- `0.25-0.35` - Popular for credit spreads
- `0.40-0.50` - Near-the-money options
- `0.50+` - In-the-money options

**Note:** Requires `delta` column in your data.

---

#### `delta_interval`
**Type:** `float` | **Default:** `None`

Group results by delta ranges.

```python
results = op.iron_condor(
    data,
    delta_interval=0.10  # Group by: (0.0,0.1], (0.1,0.2], etc.
)
```

---

## Slippage Parameters

### `slippage`
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
| `'liquidity'` | Volume-based dynamic | Dynamic | Dynamic | Realistic |

---

### `fill_ratio` (Liquidity Mode Only)
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

### `reference_volume` (Liquidity Mode Only)
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

    # Filtering
    max_otm_pct=0.30,
    min_bid_ask=0.15,
    delta_min=0.15,
    delta_max=0.20,

    # Grouping
    dte_interval=7,
    otm_pct_interval=0.05,
    delta_interval=0.05,

    # Slippage
    slippage='liquidity',
    fill_ratio=0.5,
    reference_volume=5000,

    # Output
    raw=False,
    drop_nan=True
)

print(results.head())
```

## Default Values Reference

### Standard Strategies

```python
default_kwargs = {
    "dte_interval": 7,
    "max_entry_dte": 90,
    "exit_dte": 0,
    "otm_pct_interval": 0.05,
    "max_otm_pct": 0.5,
    "min_bid_ask": 0.05,
    "drop_nan": True,
    "raw": False,
    "delta_min": None,
    "delta_max": None,
    "delta_interval": None,
    "slippage": "mid",
    "fill_ratio": 0.5,
    "reference_volume": 1000,
}
```

### Calendar & Diagonal Strategies

```python
calendar_default_kwargs = {
    "front_dte_min": 20,
    "front_dte_max": 40,
    "back_dte_min": 50,
    "back_dte_max": 90,
    "exit_dte": 7,
    "dte_interval": 7,
    "otm_pct_interval": 0.05,
    "max_otm_pct": 0.5,
    "min_bid_ask": 0.05,
    "drop_nan": True,
    "raw": False,
    "slippage": "mid",
    "fill_ratio": 0.5,
    "reference_volume": 1000,
}
```

## Next Steps

- See [Examples](examples.md) for real-world parameter usage
- Explore [Strategies](strategies.md) to understand strategy-specific considerations
- Review [API Reference](api-reference.md) for function signatures
