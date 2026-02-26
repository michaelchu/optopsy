# Condor Spreads

Condor spreads use four legs of the same option type at four ascending strikes. Unlike iron condors (which use both calls and puts), condors use only calls or only puts.

## Long Call Condor

#### Description
A neutral strategy using all calls that profits when the underlying stays between the two short strikes.

**Composition:**
- Long 1 call at strike A (lowest)
- Short 1 call at strike B
- Short 1 call at strike C
- Long 1 call at strike D (highest)

Where: A < B < C < D

#### Example
```python
import optopsy as op
results = op.long_call_condor(data, max_entry_dte=45, exit_dte=21)
```

#### Use Cases
- Range-bound markets using only calls
- Alternative to iron condors when you only want to trade one option type
- Neutral income strategy

---

## Short Call Condor

#### Description
Profits from large price movements in either direction, using all calls.

**Composition:**
- Short 1 call at strike A (lowest)
- Long 1 call at strike B
- Long 1 call at strike C
- Short 1 call at strike D (highest)

Where: A < B < C < D

#### Example
```python
results = op.short_call_condor(data, max_entry_dte=30, exit_dte=0)
```

#### Use Cases
- Expecting a breakout but unsure of direction
- Defined-risk volatility play using only calls

---

## Long Put Condor

#### Description
A neutral strategy using all puts that profits when the underlying stays between the two short strikes.

**Composition:**
- Long 1 put at strike A (lowest)
- Short 1 put at strike B
- Short 1 put at strike C
- Long 1 put at strike D (highest)

Where: A < B < C < D

#### Example
```python
results = op.long_put_condor(data, max_entry_dte=45, exit_dte=21)
```

#### Use Cases
- Range-bound markets using only puts
- Alternative to iron condors when you prefer puts

---

## Short Put Condor

#### Description
Profits from large price movements in either direction, using all puts.

**Composition:**
- Short 1 put at strike A (lowest)
- Long 1 put at strike B
- Long 1 put at strike C
- Short 1 put at strike D (highest)

Where: A < B < C < D

#### Example
```python
results = op.short_put_condor(data, max_entry_dte=30, exit_dte=0)
```

#### Use Cases
- Expecting a breakout but unsure of direction
- Defined-risk volatility play using only puts

---

## Condor vs Iron Condor

| Feature | Condor | Iron Condor |
|---------|--------|-------------|
| Option types | All calls or all puts | Both calls and puts |
| Legs | 4 (same type) | 4 (mixed type) |
| Strike constraint | 4 ascending strikes | 4 ascending strikes |
| Profit zone | Between short strikes | Between short strikes |
| Typical use | Single-type preference | Most common choice |

Both strategies have the same payoff structure at expiration. The choice between them often comes down to liquidity and execution preference.
