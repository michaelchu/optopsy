# Straddles & Strangles

Straddles and strangles are volatility-based strategies that combine calls and puts to profit from large price movements (long) or low volatility (short).

## Long Straddle

### Description
A long straddle consists of buying a call and a put at the **same strike**, typically at-the-money. This strategy profits from large price movements in either direction.

**Composition:**
- Long 1 call at strike X
- Long 1 put at strike X

### Market Outlook
- **High Volatility Expected** - Anticipate a significant move up or down
- Direction doesn't matter, only magnitude
- Common before earnings announcements or major events

### Profit/Loss
- **Maximum Profit**: Unlimited (in either direction)
- **Maximum Loss**: Total premiums paid (if price stays at strike)
- **Breakeven**: Strike ± total premium paid

### Example

```python
import optopsy as op

data = op.csv_data('SPX_options.csv')

# Backtest long straddles
results = op.long_straddles(
    data,
    max_entry_dte=30,
    exit_dte=0,  # Hold to expiration
    max_otm_pct=0.05  # Near ATM
)

print(results)
```

### Use Cases
- Earnings plays expecting big moves
- Before Fed announcements or major economic data
- When implied volatility is low but you expect an explosion
- Binary events (FDA approvals, court rulings)

---

## Short Straddle

### Description
A short straddle consists of selling a call and a put at the **same strike**. This strategy profits when the price stays near the strike at expiration.

**Composition:**
- Short 1 call at strike X
- Short 1 put at strike X

### Market Outlook
- **Low Volatility Expected** - Price stays stable
- Maximum profit if price is exactly at strike at expiration
- Profits erode if price moves significantly in either direction

### Profit/Loss
- **Maximum Profit**: Total premiums received
- **Maximum Loss**: Unlimited (if price moves far from strike)
- **Breakeven**: Strike ± total premium received

### Example

```python
results = op.short_straddles(
    data,
    max_entry_dte=45,
    exit_dte=21,
    max_otm_pct=0.05,  # ATM straddles
    min_bid_ask=0.20    # Ensure liquid options
)
```

### Use Cases
- High implied volatility environments
- After earnings when IV crush is expected
- Range-bound markets
- Income generation in low-volatility periods

### ⚠️ Risk Warning
Short straddles have unlimited risk in both directions. Consider iron butterflies for defined-risk alternatives.

---

## Long Strangle

### Description
A long strangle consists of buying an OTM call and an OTM put at **different strikes**. This is similar to a long straddle but cheaper with wider breakevens.

**Composition:**
- Long 1 OTM put at strike X
- Long 1 OTM call at strike Y (Y > X)

### Market Outlook
- **High Volatility Expected** - Anticipate a large move
- Lower cost than straddles but requires bigger move to profit
- Better risk/reward than straddles for explosive moves

### Profit/Loss
- **Maximum Profit**: Unlimited (in either direction)
- **Maximum Loss**: Total premiums paid
- **Breakeven**: Put strike - total premium, Call strike + total premium

### Example

```python
results = op.long_strangles(
    data,
    max_entry_dte=45,
    exit_dte=21,
    max_otm_pct=0.20  # Wider strikes for lower cost
)
```

### Use Cases
- Lower-cost volatility plays
- Before major events with unknown outcomes
- When you expect a significant move but want to reduce cost
- Higher probability of profit than straddles on massive moves

---

## Short Strangle

### Description
A short strangle consists of selling an OTM call and an OTM put at **different strikes**. This provides a wider profit zone than a short straddle.

**Composition:**
- Short 1 OTM put at strike X
- Short 1 OTM call at strike Y (Y > X)

### Market Outlook
- **Low to Moderate Volatility** - Price stays in a range
- Wider profit zone than short straddles
- More forgiving if price moves moderately

### Profit/Loss
- **Maximum Profit**: Total premiums received
- **Maximum Loss**: Unlimited (past short strikes)
- **Breakeven**: Put strike - total premium, Call strike + total premium

### Example

```python
results = op.short_strangles(
    data,
    max_entry_dte=45,
    exit_dte=21,
    max_otm_pct=0.30,  # Wide strikes for safer range
    min_bid_ask=0.15
)
```

### Use Cases
- Income in range-bound markets
- Higher probability of success than short straddles
- After high IV events (post-earnings)
- When you expect low volatility but want buffer

### Management Tips
- Consider closing at 50% of max profit
- Roll untested side if needed
- Monitor position size carefully due to undefined risk

---

## Strategy Comparison

| Strategy | Strikes | Premium | Profit Zone | Best For |
|----------|---------|---------|-------------|----------|
| Long Straddle | Same | Higher cost | Wide (any big move) | Maximum volatility plays |
| Long Strangle | Different | Lower cost | Wider breakevens | Lower-cost volatility |
| Short Straddle | Same | Higher credit | Narrow (at strike) | Maximum income, low vol |
| Short Strangle | Different | Lower credit | Wider range | Safer income, moderate vol |

## Greeks Considerations

### For Long Straddles/Strangles
- **Positive Vega** - Benefit from volatility increases
- **Negative Theta** - Time decay works against you
- **Trade**: Buy when IV is low, sell when IV spikes

### For Short Straddles/Strangles
- **Negative Vega** - Hurt by volatility increases
- **Positive Theta** - Time decay works for you
- **Trade**: Sell when IV is high, benefit from IV crush

## Example: IV Filtering

```python
# Target high IV environments for short strangles
results = op.short_strangles(
    data,
    max_entry_dte=45,
    exit_dte=21,
    max_otm_pct=0.25,
    # Filter for liquid, high IV options
    min_bid_ask=0.15,
    slippage='liquidity'
)
```

## Risk Management

**For Long Positions:**
- Risk is limited to premiums paid
- Consider exiting at 100% loss or 200%+ gain
- Profits can be substantial on big moves

**For Short Positions:**
- ⚠️ Risk is unlimited
- Consider stop losses or conversion to iron condors/butterflies
- Close early at 50-75% max profit
- Position size conservatively (small % of account)

## Next Steps

- Learn about [Vertical Spreads](spreads.md) for defined-risk alternatives
- Explore [Iron Butterflies](iron-strategies.md) for defined-risk volatility plays
- See more [Examples](../examples.md) with IV analysis
