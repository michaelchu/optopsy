# Covered Strategies

Covered strategies combine stock positions with options for income generation or downside protection.

!!! note "Synthetic Implementation"
    Optopsy simulates covered strategies using deep ITM calls as synthetic stock positions, since the library works with options data only.

## Covered Call

### Description
Generate income by selling calls against a long stock position (or synthetic long via deep ITM call).

**Composition:**
- Long underlying (simulated via long deep ITM call)
- Short 1 call at higher strike

### Example
```python
import optopsy as op
results = op.covered_call(data, max_entry_dte=45, exit_dte=21)
```

### Use Cases
- Generate income on stock holdings
- Willing to sell stock at higher price
- Neutral to slightly bullish outlook

---

## Protective Put (Married Put)

### Description
Buy downside protection by purchasing puts against a long stock position.

**Composition:**
- Long underlying (simulated via long deep ITM call)
- Long 1 put at lower strike for protection

### Example
```python
results = op.protective_put(data, max_entry_dte=90, exit_dte=60)
```

### Use Cases
- Hedging long stock positions
- Protection during uncertain periods
- Portfolio insurance
