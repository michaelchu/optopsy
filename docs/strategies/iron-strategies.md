# Iron Condors & Iron Butterflies

Four-leg strategies that combine credit spreads to create defined-risk, defined-reward positions. These are popular income strategies for neutral to range-bound markets.

## Iron Condor

### Description
An iron condor combines a bull put spread and a bear call spread, creating a wide profit zone. This is one of the most popular credit strategies.

**Composition:**
- Long 1 put at strike A (protection)
- Short 1 put at strike B (income)
- Short 1 call at strike C (income)
- Long 1 call at strike D (protection)

Where: A < B < C < D

### Market Outlook
- **Neutral** - Expect the underlying to stay between the short strikes
- Profits if price stays in the range at expiration
- Ideal for low-volatility, range-bound markets

### Profit/Loss
- **Maximum Profit**: Net credit received
- **Maximum Loss**: Width of spread - net credit
- **Breakeven**: Short put strike - net credit, Short call strike + net credit

### Example

```python
import optopsy as op

data = op.csv_data('SPX_options.csv')

# Backtest iron condors
results = op.iron_condor(
    data,
    max_entry_dte=45,
    exit_dte=21,
    max_otm_pct=0.30,  # Wide wings for high probability
    min_bid_ask=0.10
)

print(results)
```

### Use Cases
- Income generation in range-bound markets
- After high IV events (post-earnings IV crush)
- When you expect low volatility
- Monthly income strategies (45 DTE entry, 21 DTE exit)

### Management Guidelines
- **Take Profit**: Close at 50% of max profit
- **Stop Loss**: Close at 200% of credit received or 21 DTE
- **Rolling**: Roll untested side if challenged
- **Profit Zone**: Typically 60-70% probability of profit

---

## Reverse Iron Condor

### Description
The opposite of an iron condor - this strategy profits from large price movements in either direction while defining risk.

**Composition:**
- Short 1 put at strike A
- Long 1 put at strike B
- Long 1 call at strike C
- Short 1 call at strike D

Where: A < B < C < D

### Market Outlook
- **High Volatility Expected** - Anticipate breakout in either direction
- Profits if price moves significantly beyond inner strikes
- Defined-risk alternative to long straddles

### Profit/Loss
- **Maximum Profit**: Width of spread - net debit
- **Maximum Loss**: Net debit paid
- **Breakeven**: Long put strike + debit, Long call strike - debit

### Example

```python
results = op.reverse_iron_condor(
    data,
    max_entry_dte=30,
    exit_dte=0,
    max_otm_pct=0.25  # Setup for breakout moves
)
```

### Use Cases
- Before major events expecting big moves
- Defined-risk volatility plays
- When you expect a breakout but want limited loss

---

## Iron Butterfly

### Description
An iron butterfly is similar to an iron condor but with the short strikes at the same price (ATM), creating a tighter profit zone with higher potential profit.

**Composition:**
- Long 1 put at strike A (wing)
- Short 1 put at strike B (body)
- Short 1 call at strike B (body) - **same as short put**
- Long 1 call at strike C (wing)

Where: A < B < C

### Market Outlook
- **Very Neutral** - Expect price to stay at or very near current level
- Maximum profit if price is exactly at middle strike at expiration
- Higher reward but narrower profit zone than iron condor

### Profit/Loss
- **Maximum Profit**: Net credit received (larger than iron condor)
- **Maximum Loss**: Width of wing - net credit
- **Breakeven**: Short strike ± net credit

### Example

```python
results = op.iron_butterfly(
    data,
    max_entry_dte=45,
    exit_dte=21,
    max_otm_pct=0.05,  # ATM body for maximum credit
    min_bid_ask=0.15
)
```

### Use Cases
- Expecting price to pin at a specific level
- Around major strikes with high open interest
- When you want higher credit than iron condors
- Lower probability but higher reward than iron condors

### Pin Risk
- Stock prices tend to pin at strikes with high open interest
- Iron butterflies benefit from this pinning effect
- Monitor expiration week price action carefully

---

## Reverse Iron Butterfly

### Description
The opposite of an iron butterfly - profits from large moves away from the center strike.

**Composition:**
- Short 1 put at strike A (wing)
- Long 1 put at strike B (body)
- Long 1 call at strike B (body) - **same as long put**
- Short 1 call at strike C (wing)

Where: A < B < C

### Market Outlook
- **High Volatility** - Expect significant move from current price
- Defined-risk alternative to long straddles
- Lower cost and defined max loss

### Profit/Loss
- **Maximum Profit**: Width of wing - net debit
- **Maximum Loss**: Net debit paid
- **Breakeven**: Long strike ± net debit

### Example

```python
results = op.reverse_iron_butterfly(
    data,
    max_entry_dte=30,
    exit_dte=7,
    max_otm_pct=0.10
)
```

### Use Cases
- Before major events (earnings, FDA decisions)
- When you expect explosive moves
- Defined-risk alternative to long straddles/strangles

---

## Strategy Comparison

| Strategy | Profit Zone | Max Profit | Max Loss | Best For |
|----------|-------------|-----------|----------|----------|
| Iron Condor | Wide range | Medium credit | Defined | Range-bound income |
| Reverse IC | Outside range | Defined | Net debit | Breakout plays |
| Iron Butterfly | Narrow (at ATM) | Higher credit | Defined | Pinning at strike |
| Reverse Iron Butterfly | Away from ATM | Defined | Net debit | Volatility explosion |

## Iron Condor vs Iron Butterfly

**Iron Condor:**
- ✅ Wider profit zone (60-70% probability)
- ✅ More forgiving if price moves
- ❌ Lower credit received
- **Use when**: Moderate confidence in range

**Iron Butterfly:**
- ✅ Higher credit (2-3x more)
- ❌ Narrower profit zone (40-50% probability)
- ❌ Less forgiving to price movement
- **Use when**: High confidence in pinning

## Advanced Example: Delta-Neutral Iron Condors

```python
# Target delta-neutral positioning
results = op.iron_condor(
    data,
    max_entry_dte=45,
    exit_dte=21,
    # Target specific delta for short strikes
    delta_min=0.15,  # ~15-20 delta short strikes
    delta_max=0.20,
    delta_interval=0.05,
    min_bid_ask=0.10,
    slippage='liquidity'
)
```

## Risk Management Best Practices

### Entry Checklist
- [ ] 45 DTE or less (optimal theta decay)
- [ ] Credit > 1/3 width of spreads
- [ ] Probability of profit > 60%
- [ ] Liquid strikes (tight bid-ask spreads)
- [ ] Defined position size (< 5% of account per trade)

### Management Rules
1. **Take Profit**: Close at 50% max profit (21 DTE)
2. **Stop Loss**: Close at 200-300% of credit or break-even
3. **Rolling**: Roll down/up untested side if challenged early
4. **Expiration**: Avoid holding through expiration (pin risk)

### Position Sizing
- Risk no more than 2-5% per trade
- Iron condors: Width determines risk per contract
- Example: $5 wide spreads for $2 credit = $300 max risk per IC

## Greeks Analysis

### Iron Condor Greeks
- **Theta**: Positive (time decay helps you)
- **Vega**: Negative (want volatility to decrease)
- **Delta**: Near zero (neutral position)
- **Gamma**: Negative (position against you if price moves)

**Optimal Conditions:**
- High IV → Sell when IV is elevated
- Decreasing volatility → IV crush benefits position
- Time passes → Theta decay increases profit

## Common Mistakes to Avoid

1. **Holding Too Long**: Exit at 50% profit, don't be greedy
2. **Wrong IV Environment**: Don't sell when IV is low
3. **Too Narrow**: Ensure adequate buffer between short strikes
4. **Ignoring Adjustments**: Have a plan if price threatens strikes
5. **Over-Sizing**: Respect max loss per position

## Next Steps

- Learn about [Butterfly Spreads](butterflies.md) for three-leg alternatives
- Explore [Calendar Spreads](calendars.md) for time-based strategies
- See more [Examples](../examples.md) with risk management
- Review [Parameters](../parameters.md) for optimization
