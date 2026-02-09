# Butterfly Spreads

Butterfly spreads are three-leg strategies designed to profit when the underlying stays near a specific price. They offer defined risk and defined reward with neutral market outlooks.

## Long Call Butterfly

#### Description
Profits when the underlying stays at the middle strike at expiration.

**Composition:**
- Long 1 call at lower strike (wing)
- Short 2 calls at middle strike (body)
- Long 1 call at upper strike (wing)

#### Example
```python
import optopsy as op
results = op.long_call_butterfly(data, max_entry_dte=45, exit_dte=21)
```

---

## Short Call Butterfly

#### Description
Profits when the underlying moves away from the middle strike in either direction.

**Composition:**
- Short 1 call at lower strike
- Long 2 calls at middle strike
- Short 1 call at upper strike

#### Example
```python
results = op.short_call_butterfly(data, max_entry_dte=30, exit_dte=7)
```

---

## Long Put Butterfly

#### Description
Similar to long call butterfly but using puts. Profits at middle strike.

**Composition:**
- Long 1 put at lower strike (wing)
- Short 2 puts at middle strike (body)
- Long 1 put at upper strike (wing)

#### Example
```python
results = op.long_put_butterfly(data, max_entry_dte=45, exit_dte=21)
```

---

## Short Put Butterfly

#### Description
Profits when the underlying moves significantly away from the middle strike.

**Composition:**
- Short 1 put at lower strike
- Long 2 puts at middle strike
- Short 1 put at upper strike

#### Example
```python
results = op.short_put_butterfly(data, max_entry_dte=30, exit_dte=7)
```

---

## Key Characteristics

- **Equal Wing Width**: Wings are equidistant from the body
- **Low Cost**: Often entered for small debit or even credit
- **Defined Risk**: Maximum loss is limited to debit paid
- **High Precision**: Profits in narrow range around middle strike
