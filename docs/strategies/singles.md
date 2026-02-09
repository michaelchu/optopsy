# Single-Leg Strategies

Single-leg strategies involve buying or selling a single call or put option. These are the simplest options strategies and form the building blocks for more complex multi-leg strategies.

## Long Calls

#### Description
A long call gives you the right to buy the underlying at the strike price. This is a bullish strategy with unlimited profit potential and limited risk (the premium paid).

#### Market Outlook
- **Bullish** - Expect significant upward price movement
- Profits increase as the underlying rises above the strike + premium paid

#### Profit/Loss
- **Maximum Profit**: Unlimited (underlying price - strike - premium)
- **Maximum Loss**: Premium paid (if underlying stays below strike)
- **Breakeven**: Strike + premium paid

#### Example

```python
import optopsy as op

data = op.csv_data('SPX_options.csv')

# Backtest long calls with 30-60 DTE range
results = op.long_calls(
    data,
    max_entry_dte=60,
    exit_dte=30,
    max_otm_pct=0.10  # Slightly OTM calls
)

print(results)
```

#### Use Cases
- Betting on a strong rally
- Lower-cost alternative to buying stock
- Earnings plays expecting a positive surprise
- Breakout trades

---

## Short Calls

#### Description
A short call obligates you to sell the underlying at the strike if exercised. This is a bearish or neutral income strategy with limited profit and theoretically unlimited risk.

#### Market Outlook
- **Bearish to Neutral** - Expect price to stay flat or decline
- Profits if the underlying stays below the strike at expiration

#### Profit/Loss
- **Maximum Profit**: Premium received
- **Maximum Loss**: Unlimited (underlying price - strike - premium)
- **Breakeven**: Strike + premium received

#### Example

```python
results = op.short_calls(
    data,
    max_entry_dte=45,
    exit_dte=0,  # Hold to expiration
    max_otm_pct=0.30  # Sell OTM calls for income
)
```

#### Use Cases
- Generating income in neutral/bearish markets
- Covered call strategies (with stock holdings)
- High-probability income trades

#### ⚠️ Risk Warning
Short naked calls have unlimited risk if the underlying rises significantly. Consider defined-risk alternatives like call spreads.

---

## Long Puts

#### Description
A long put gives you the right to sell the underlying at the strike price. This is a bearish strategy with substantial profit potential and limited risk (the premium paid).

#### Market Outlook
- **Bearish** - Expect significant downward price movement
- Profits increase as the underlying falls below the strike - premium paid

#### Profit/Loss
- **Maximum Profit**: Strike - premium - 0 (if underlying goes to zero)
- **Maximum Loss**: Premium paid (if underlying stays above strike)
- **Breakeven**: Strike - premium paid

#### Example

```python
results = op.long_puts(
    data,
    max_entry_dte=45,
    exit_dte=21,
    max_otm_pct=0.15  # Moderately OTM puts
)
```

#### Use Cases
- Betting on a market decline
- Portfolio hedging
- Earnings plays expecting negative news
- Breakdown trades

---

## Short Puts

#### Description
A short put obligates you to buy the underlying at the strike if exercised. This is a bullish income strategy where you collect premium, hoping the option expires worthless.

#### Market Outlook
- **Bullish to Neutral** - Expect price to stay flat or rise
- Profits if the underlying stays above the strike at expiration

#### Profit/Loss
- **Maximum Profit**: Premium received
- **Maximum Loss**: Strike - premium (if underlying goes to zero)
- **Breakeven**: Strike - premium received

#### Example

```python
results = op.short_puts(
    data,
    max_entry_dte=45,
    exit_dte=21,
    max_otm_pct=0.20,  # 20% OTM for safer premium
    min_bid_ask=0.10
)
```

#### Use Cases
- Generating income in bullish markets
- Getting "paid to wait" to buy stock at a lower price
- High-probability credit strategies
- Wheel strategy (sell puts, get assigned, sell calls)

#### Assignment Considerations
If the option is in-the-money at expiration, you'll be obligated to buy shares at the strike price. Ensure you have capital or can close before expiration.

---

## Greeks Filtering

All single-leg strategies support delta filtering to target specific probability ranges:

```python
# Target 0.30 delta options (roughly 30% probability ITM)
results = op.long_calls(
    data,
    delta_min=0.25,
    delta_max=0.35,
    delta_interval=0.05  # Group results by delta ranges
)
```

## Slippage Models

Configure realistic fill prices:

```python
# Use liquidity-based slippage
results = op.long_calls(
    data,
    slippage='liquidity',
    fill_ratio=0.5,  # 50% through the spread
    reference_volume=1000  # Minimum volume for liquid options
)
```

Available slippage modes:
- `'mid'` - Fill at mid-price (bid+ask)/2 (default)
- `'spread'` - Buy at ask, sell at bid (worst case)
- `'liquidity'` - Dynamic fill based on volume/open interest

## Comparison Table

| Strategy | Direction | Max Profit | Max Loss | Best When |
|----------|-----------|-----------|----------|-----------|
| Long Call | Bullish | Unlimited | Premium | Expecting rally |
| Short Call | Bearish/Neutral | Premium | Unlimited | Expecting decline/flat |
| Long Put | Bearish | Substantial | Premium | Expecting drop |
| Short Put | Bullish/Neutral | Premium | Substantial | Expecting rise/flat |

## Next Steps

- Learn about [Straddles & Strangles](straddles-strangles.md)
- Explore [Vertical Spreads](spreads.md) for defined-risk alternatives
- See more [Examples](../examples.md)
