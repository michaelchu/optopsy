# Diagonal Spreads

Diagonal spreads combine elements of vertical spreads and calendar spreads, using different strikes AND different expirations. These hybrid strategies offer flexible profit zones and directional bias.

## Long Call Diagonal

#### Description
Buy a longer-term call at one strike and sell a shorter-term call at a different strike. Combines time decay and directional movement.

**Composition:**
- Short 1 front-month call
- Long 1 back-month call
- Different strikes for each leg

#### Example
```python
import optopsy as op

results = op.long_call_diagonal(
    data,
    front_dte_min=20,
    front_dte_max=40,
    back_dte_min=50,
    back_dte_max=90,
    exit_dte=7
)
```

#### Use Cases
- Bullish to neutral bias with income
- More flexible than calendars
- Adjustable directional exposure

---

## Short Call Diagonal

#### Description
Opposite of long call diagonal. Buy near-term, sell longer-term at different strikes.

**Composition:**
- Long 1 front-month call
- Short 1 back-month call
- Different strikes for each leg

#### Example
```python
results = op.short_call_diagonal(data)
```

---

## Long Put Diagonal

#### Description
Similar structure to call diagonals but using puts. Allows bearish to neutral positioning.

**Composition:**
- Short 1 front-month put
- Long 1 back-month put
- Different strikes for each leg

#### Example
```python
results = op.long_put_diagonal(data)
```

---

## Short Put Diagonal

#### Description
Opposite of long put diagonal with reversed expiration dates.

**Composition:**
- Long 1 front-month put
- Short 1 back-month put
- Different strikes for each leg

#### Example
```python
results = op.short_put_diagonal(data)
```

---

## Diagonal vs Calendar

| Feature | Calendar Spread | Diagonal Spread |
|---------|----------------|-----------------|
| Strikes | Same | Different |
| Directional | Neutral | Can be directional |
| Complexity | Simple | More complex |
| Flexibility | Limited | High |

## Parameters

Diagonal spreads use calendar spread parameters but evaluate all strike combinations:

```python
results = op.long_call_diagonal(
    data,
    front_dte_min=20,
    front_dte_max=40,
    back_dte_min=50,
    back_dte_max=90,
    max_otm_pct=0.30  # Wider range for strike selection
)
```

## Strategy Tips

- Start with calendar, adjust strikes as market moves
- Monitor both time decay and directional movement
- More management-intensive than calendars
- Can convert to vertical spreads or calendars
