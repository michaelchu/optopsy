# Calendar Spreads

Calendar spreads (also called time spreads or horizontal spreads) use options with the same strike but different expiration dates. They profit from time decay differential and changes in implied volatility.

## Long Call Calendar

### Description
Sell a near-term call and buy a longer-term call at the same strike. Profits from time decay and volatility expansion in the back month.

**Composition:**
- Short 1 front-month call (near expiration)
- Long 1 back-month call (longer expiration)
- Both at the same strike

### Example
```python
import optopsy as op

results = op.long_call_calendar(
    data,
    front_dte_min=20,
    front_dte_max=40,
    back_dte_min=50,
    back_dte_max=90,
    exit_dte=7  # Exit 7 days before front expiration
)
```

### Use Cases
- Neutral markets near the strike
- Expecting volatility increase
- Time decay plays

---

## Short Call Calendar

### Description
Buy the near-term call, sell the longer-term call. Profits from significant movement away from strike.

**Composition:**
- Long 1 front-month call
- Short 1 back-month call
- Both at the same strike

### Example
```python
results = op.short_call_calendar(
    data,
    front_dte_min=20,
    front_dte_max=40,
    back_dte_min=50,
    back_dte_max=90
)
```

---

## Long Put Calendar

### Description
Similar to long call calendar but with puts. Profits from neutral price action at the strike.

**Composition:**
- Short 1 front-month put
- Long 1 back-month put
- Both at the same strike

### Example
```python
results = op.long_put_calendar(data)
```

---

## Short Put Calendar

### Description
Opposite of long put calendar. Profits from movement away from strike.

**Composition:**
- Long 1 front-month put
- Short 1 back-month put
- Both at the same strike

### Example
```python
results = op.short_put_calendar(data)
```

---

## Key Parameters

Calendar spreads use different default parameters:

```python
calendar_default_kwargs = {
    "front_dte_min": 20,      # Min DTE for front leg
    "front_dte_max": 40,      # Max DTE for front leg
    "back_dte_min": 50,       # Min DTE for back leg
    "back_dte_max": 90,       # Max DTE for back leg
    "exit_dte": 7,            # Exit 7 days before front expiration
    "dte_interval": 7,
    "otm_pct_interval": 0.05,
    "max_otm_pct": 0.5,
}
```

## Best Practices

- Exit before front leg expiration to avoid assignment
- Target strikes near current price
- Monitor volatility skew between expirations
- Consider IV changes in back month
