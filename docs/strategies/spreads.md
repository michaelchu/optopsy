# Vertical & Ratio Spreads

Vertical spreads combine buying and selling options of the same type (both calls or both puts) with different strikes but the same expiration. Ratio spreads extend this concept with unequal quantities on each leg.

## Long Call Spread (Bull Call Spread) {#long-call-spread}

#### Description
A bullish strategy that buys a lower strike call and sells a higher strike call, reducing cost but capping upside.

**Composition:**
- Long 1 call at lower strike X
- Short 1 call at higher strike Y

#### Example
```python
import optopsy as op
results = op.long_call_spread(data, max_entry_dte=45, exit_dte=21)
```

---

## Short Call Spread (Bear Call Spread) {#short-call-spread}

#### Description
A bearish credit strategy profiting when the underlying stays below the short strike.

**Composition:**
- Short 1 call at lower strike X
- Long 1 call at higher strike Y (protection)

#### Example
```python
results = op.short_call_spread(data, max_entry_dte=45, exit_dte=21)
```

---

## Long Put Spread (Bear Put Spread) {#long-put-spread}

#### Description
A bearish strategy profiting from downward moves with defined risk.

**Composition:**
- Short 1 put at lower strike X
- Long 1 put at higher strike Y

#### Example
```python
results = op.long_put_spread(data, max_entry_dte=45, exit_dte=21)
```

---

## Short Put Spread (Bull Put Spread) {#short-put-spread}

#### Description
A bullish credit strategy profiting when the underlying stays above the short strike.

**Composition:**
- Long 1 put at lower strike X (protection)
- Short 1 put at higher strike Y

#### Example
```python
results = op.short_put_spread(data, max_entry_dte=45, exit_dte=21)
```

---

---

## Call Back Spread (Call Ratio Backspread) {#call-back-spread}

#### Description
A bullish ratio strategy that profits from large upward moves. The 2:1 long-to-short ratio provides unlimited upside potential.

**Composition:**
- Short 1 call at lower strike (ITM)
- Long 2 calls at higher strike (OTM)

#### Example
```python
results = op.call_back_spread(data, max_entry_dte=45, exit_dte=21)
```

---

## Put Back Spread (Put Ratio Backspread) {#put-back-spread}

#### Description
A bearish ratio strategy that profits from large downward moves. The 2:1 long-to-short ratio provides large downside profit potential.

**Composition:**
- Short 1 put at higher strike (ITM)
- Long 2 puts at lower strike (OTM)

#### Example
```python
results = op.put_back_spread(data, max_entry_dte=45, exit_dte=21)
```

---

## Call Front Spread (Call Ratio Spread) {#call-front-spread}

#### Description
A neutral-to-slightly-bullish strategy that profits from time decay when the underlying stays near the short strike.

**Composition:**
- Long 1 call at lower strike (ITM)
- Short 2 calls at higher strike (OTM)

#### Example
```python
results = op.call_front_spread(data, max_entry_dte=45, exit_dte=21)
```

---

## Put Front Spread (Put Ratio Spread) {#put-front-spread}

#### Description
A neutral-to-slightly-bearish strategy that profits from time decay when the underlying stays near the short strike.

**Composition:**
- Long 1 put at higher strike (ITM)
- Short 2 puts at lower strike (OTM)

#### Example
```python
results = op.put_front_spread(data, max_entry_dte=45, exit_dte=21)
```

---

## Comparison Table

### Vertical Spreads

| Spread | Direction | Type | Max Profit | Max Loss |
|--------|-----------|------|-----------|----------|
| Long Call | Bullish | Debit | Width - debit | Debit paid |
| Short Call | Bearish | Credit | Credit | Width - credit |
| Long Put | Bearish | Debit | Width - debit | Debit paid |
| Short Put | Bullish | Credit | Credit | Width - credit |

### Ratio Spreads

| Spread | Direction | Ratio | Max Profit | Max Loss |
|--------|-----------|-------|-----------|----------|
| Call Back | Very bullish | 1:2 | Unlimited | Limited |
| Put Back | Very bearish | 1:2 | Large | Limited |
| Call Front | Neutral | 1:2 | Net credit | Unlimited above strike |
| Put Front | Neutral | 1:2 | Net credit | Unlimited below strike |
