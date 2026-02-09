# Vertical Spreads

Vertical spreads combine buying and selling options of the same type (both calls or both puts) with different strikes but the same expiration. These strategies offer defined risk and defined reward.

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
results = op.short_call_spread(data, max_entry_dte=45, exit_dte=21, max_otm_pct=0.20)
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
results = op.short_put_spread(data, max_entry_dte=45, exit_dte=21, max_otm_pct=0.25)
```

---

## Comparison Table

| Spread | Direction | Type | Max Profit | Max Loss |
|--------|-----------|------|-----------|----------|
| Long Call | Bullish | Debit | Width - debit | Debit paid |
| Short Call | Bearish | Credit | Credit | Width - credit |
| Long Put | Bearish | Debit | Width - debit | Debit paid |
| Short Put | Bullish | Credit | Credit | Width - credit |
