# Strategy Overview

Optopsy includes 28 built-in options strategies covering single-leg, multi-leg, and time-based strategies.

## Strategy Categories

### Single-Leg Strategies (4)
Basic directional plays with calls or puts.

- [Long Calls](strategies/singles.md#long-calls) - Bullish directional bet
- [Short Calls](strategies/singles.md#short-calls) - Bearish or neutral income
- [Long Puts](strategies/singles.md#long-puts) - Bearish directional bet
- [Short Puts](strategies/singles.md#short-puts) - Bullish income strategy

[Learn more →](strategies/singles.md)

### Straddles & Strangles (4)
Volatility-based strategies combining calls and puts.

- [Long Straddle](strategies/straddles-strangles.md#long-straddle) - Profit from big moves
- [Short Straddle](strategies/straddles-strangles.md#short-straddle) - Income from low volatility
- [Long Strangle](strategies/straddles-strangles.md#long-strangle) - Lower-cost volatility play
- [Short Strangle](strategies/straddles-strangles.md#short-strangle) - Wider profit zone income

[Learn more →](strategies/straddles-strangles.md)

### Vertical Spreads (4)
Limited-risk directional strategies.

- [Long Call Spread](strategies/spreads.md#long-call-spread) - Bullish debit spread
- [Short Call Spread](strategies/spreads.md#short-call-spread) - Bearish credit spread
- [Long Put Spread](strategies/spreads.md#long-put-spread) - Bearish debit spread
- [Short Put Spread](strategies/spreads.md#short-put-spread) - Bullish credit spread

[Learn more →](strategies/spreads.md)

### Butterfly Spreads (4)
Neutral strategies targeting specific price ranges.

- [Long Call Butterfly](strategies/butterflies.md#long-call-butterfly) - Profit at middle strike
- [Short Call Butterfly](strategies/butterflies.md#short-call-butterfly) - Profit from movement
- [Long Put Butterfly](strategies/butterflies.md#long-put-butterfly) - Bearish butterfly
- [Short Put Butterfly](strategies/butterflies.md#short-put-butterfly) - Inverse put butterfly

[Learn more →](strategies/butterflies.md)

### Iron Strategies (4)
Four-leg strategies with defined risk.

- [Iron Condor](strategies/iron-strategies.md#iron-condor) - Range-bound income
- [Reverse Iron Condor](strategies/iron-strategies.md#reverse-iron-condor) - Breakout play
- [Iron Butterfly](strategies/iron-strategies.md#iron-butterfly) - Tighter profit zone
- [Reverse Iron Butterfly](strategies/iron-strategies.md#reverse-iron-butterfly) - Long volatility

[Learn more →](strategies/iron-strategies.md)

### Covered Strategies (2)
Stock + option combinations (synthetic).

- [Covered Call](strategies/covered.md#covered-call) - Income on stock holdings
- [Protective Put](strategies/covered.md#protective-put) - Downside insurance

[Learn more →](strategies/covered.md)

### Calendar Spreads (4)
Same strike, different expirations.

- [Long Call Calendar](strategies/calendars.md#long-call-calendar) - Time decay play
- [Short Call Calendar](strategies/calendars.md#short-call-calendar) - Opposite calendar
- [Long Put Calendar](strategies/calendars.md#long-put-calendar) - Bearish time spread
- [Short Put Calendar](strategies/calendars.md#short-put-calendar) - Reverse put calendar

[Learn more →](strategies/calendars.md)

### Diagonal Spreads (4)
Different strikes and expirations.

- [Long Call Diagonal](strategies/diagonals.md#long-call-diagonal) - Hybrid spread
- [Short Call Diagonal](strategies/diagonals.md#short-call-diagonal) - Reverse call diagonal
- [Long Put Diagonal](strategies/diagonals.md#long-put-diagonal) - Bearish diagonal
- [Short Put Diagonal](strategies/diagonals.md#short-put-diagonal) - Bullish diagonal

[Learn more →](strategies/diagonals.md)

## Quick Reference Table

| Strategy | Legs | Market View | Max Profit | Max Loss | Example Use |
|----------|------|-------------|-----------|----------|-------------|
| Long Call | 1 | Bullish | Unlimited | Premium paid | Betting on rally |
| Short Put | 1 | Bullish | Premium received | Substantial | Income generation |
| Iron Condor | 4 | Neutral | Net credit | Difference in strikes | Range-bound markets |
| Long Straddle | 2 | High volatility | Unlimited | Premiums paid | Before earnings |
| Call Butterfly | 3 | Neutral | Width of wing | Net debit | Pinning at strike |
| Call Calendar | 2 | Neutral | Variable | Net debit | Time decay play |

## Strategy Selection Guide

### If you think the market will...

**Go Up Significantly**
- Long Calls
- Long Call Spread

**Go Down Significantly**
- Long Puts
- Long Put Spread

**Stay Flat**
- Short Straddle
- Short Strangle
- Iron Condor
- Iron Butterfly

**Move But Unsure Direction**
- Long Straddle
- Long Strangle

**Stay Near Current Price**
- Calendar Spreads
- Butterflies

### By Risk/Reward Profile

**Limited Risk, Limited Reward**
- All spreads (vertical, butterfly, iron condor)

**Limited Risk, Unlimited Reward**
- Long calls/puts
- Long straddles/strangles

**Substantial Risk, Limited Reward**
- Short calls/puts
- Short straddles/strangles

## Common Parameters

All strategies accept these common parameters:

- `max_entry_dte` - Maximum days to expiration at entry
- `exit_dte` - Days to expiration at exit
- `dte_interval` - Grouping interval for results
- `max_otm_pct` - Maximum out-of-the-money percentage
- `otm_pct_interval` - Grouping interval for OTM%
- `min_bid_ask` - Minimum bid-ask spread filter
- `raw` - Return raw trade data (default: aggregated stats)

See the [Parameters Guide](parameters.md) for complete details.

## Next Steps

- Dive into specific [strategy categories](#strategy-categories)
- Learn about [strategy parameters](parameters.md)
- See [examples](examples.md) of real backtests
- Check the [API Reference](api-reference.md) for function signatures
