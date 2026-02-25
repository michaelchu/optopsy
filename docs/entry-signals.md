# Entry Signals

Filter strategy entries using technical analysis signals powered by [pandas-ta](https://github.com/twopirllc/pandas-ta). Use `apply_signal` to compute valid dates, then pass them as `entry_dates` or `exit_dates` to any strategy.

```python
from optopsy import long_calls, apply_signal, rsi_below, sustained, signal, day_of_week

# Enter only when RSI(14) is below 30
entry_dates = apply_signal(data, rsi_below(14, 30))
results = long_calls(data, entry_dates=entry_dates)

# Require RSI below 30 for 5 consecutive days
entry_dates = apply_signal(data, sustained(rsi_below(14, 30), days=5))
results = long_calls(data, entry_dates=entry_dates)

# Compose signals with & and |
sig = signal(rsi_below(14, 30)) & signal(day_of_week(3))  # Oversold + Thursday
entry_dates = apply_signal(data, sig)
results = long_calls(data, entry_dates=entry_dates)
```

## Available Signals

| Category | Signals | Default Parameters |
|----------|---------|-------------------|
| **RSI** | `rsi_below`, `rsi_above` | `period=14`, `threshold=30` / `70` |
| **SMA** | `sma_below`, `sma_above` | `period=20` |
| **MACD** | `macd_cross_above`, `macd_cross_below` | `fast=12`, `slow=26`, `signal_period=9` |
| **Bollinger Bands** | `bb_above_upper`, `bb_below_lower` | `length=20`, `std=2.0` |
| **EMA Crossover** | `ema_cross_above`, `ema_cross_below` | `fast=10`, `slow=50` |
| **ATR Volatility** | `atr_above`, `atr_below` | `period=14`, `multiplier=1.5` / `0.75` |
| **IV Rank** | `iv_rank_above`, `iv_rank_below` | `threshold=0.5`, `window=252` |
| **Calendar** | `day_of_week` | Days: `0`=Mon ... `4`=Fri |
| **Custom** | `custom_signal` | `flag_col='signal'` |

## Combinators

| Function | Description |
|----------|-------------|
| `sustained(signal, days=5)` | Require signal True for N consecutive bars |
| `and_signals(sig1, sig2, ...)` | All signals must be True |
| `or_signals(sig1, sig2, ...)` | At least one signal must be True |
| `Signal` class with `&` / `\|` | Fluent operator chaining |

## Signal Examples

### RSI - enter on oversold, exit on overbought

```python
import optopsy as op
from optopsy import apply_signal, rsi_below, rsi_above

entry_dates = apply_signal(data, rsi_below(period=14, threshold=30))
exit_dates = apply_signal(data, rsi_above(period=14, threshold=70))
results = op.long_calls(data, entry_dates=entry_dates, exit_dates=exit_dates)
```

### SMA - trend filter

Only enter when price is above its 50-day moving average:

```python
from optopsy import apply_signal, sma_above

entry_dates = apply_signal(data, sma_above(period=50))
results = op.short_puts(data, entry_dates=entry_dates)
```

### MACD - enter on bullish crossover

```python
from optopsy import apply_signal, macd_cross_above

entry_dates = apply_signal(data, macd_cross_above(fast=12, slow=26, signal_period=9))
results = op.long_call_spread(data, entry_dates=entry_dates)
```

### Bollinger Bands - mean reversion

Enter when price dips below the lower band:

```python
from optopsy import apply_signal, bb_below_lower

entry_dates = apply_signal(data, bb_below_lower(length=20, std=2.0))
results = op.long_puts(data, entry_dates=entry_dates)
```

### EMA Crossover - golden cross

Fast EMA crosses above slow EMA:

```python
from optopsy import apply_signal, ema_cross_above

entry_dates = apply_signal(data, ema_cross_above(fast=10, slow=50))
results = op.long_calls(data, entry_dates=entry_dates)
```

### ATR - low-volatility regime filter

Only sell premium in low-volatility regimes:

```python
from optopsy import apply_signal, atr_below

entry_dates = apply_signal(data, atr_below(period=14, multiplier=0.75))
results = op.iron_condor(data, entry_dates=entry_dates)
```

### Calendar - restrict entries to specific days

```python
from optopsy import apply_signal, day_of_week

# Enter only on Mondays and Fridays
entry_dates = apply_signal(data, day_of_week(0, 4))
results = op.short_straddles(data, entry_dates=entry_dates)
```

## Combining Multiple Signals

Use the `Signal` class with `&` (AND) and `|` (OR) operators, or the functional `and_signals` / `or_signals` helpers:

```python
from optopsy import apply_signal, signal, rsi_below, sma_above, atr_below, day_of_week
from optopsy import and_signals, or_signals

# Fluent API: oversold + uptrend + low volatility
entry = signal(rsi_below(14, 30)) & signal(sma_above(50)) & signal(atr_below(14, 0.75))
entry_dates = apply_signal(data, entry)
results = op.long_calls(data, entry_dates=entry_dates)

# Functional API: same logic
entry = and_signals(rsi_below(14, 30), sma_above(50), atr_below(14, 0.75))
entry_dates = apply_signal(data, entry)
results = op.long_calls(data, entry_dates=entry_dates)

# OR: enter when EITHER condition fires
from optopsy import macd_cross_above, bb_below_lower
entry = or_signals(macd_cross_above(), bb_below_lower())
entry_dates = apply_signal(data, entry)
results = op.long_call_spread(data, entry_dates=entry_dates)
```

## Sustained Signals

Require a condition to persist for multiple consecutive days before triggering:

```python
from optopsy import apply_signal, sustained, rsi_below, bb_below_lower

# RSI must stay below 30 for 5 straight days
entry_dates = apply_signal(data, sustained(rsi_below(14, 30), days=5))
results = op.long_calls(data, entry_dates=entry_dates)

# Bollinger Band breach sustained for 3 days
entry_dates = apply_signal(data, sustained(bb_below_lower(20, 2.0), days=3))
results = op.long_puts(data, entry_dates=entry_dates)
```

## Using Stock OHLCV Data

By default, signals compute indicators from the option chain's `underlying_price` column. For more accurate TA signals (especially ATR, which benefits from real high/low data), use `apply_signal` on a separate stock OHLCV DataFrame and pass the result as `entry_dates`:

```python
import pandas as pd
import optopsy as op
from optopsy import apply_signal, atr_above, ema_cross_above, signal

# Load OHLCV stock data (must have: underlying_symbol, quote_date, close;
# optional: open, high, low, volume)
stock_df = pd.read_csv("SPX_daily_ohlcv.csv", parse_dates=["quote_date"])

# Compute entry dates from stock data using real high/low for ATR
entry = signal(atr_above(period=14, multiplier=1.5)) & signal(ema_cross_above(10, 50))
entry_dates = apply_signal(stock_df, entry)

# Pass pre-computed dates to the strategy
results = op.long_straddles(data, entry_dates=entry_dates)
```

## IV Rank - volatility regime filter

IV Rank measures where current implied volatility sits relative to its trailing range. Requires an `implied_volatility` column in your options data.

### Sell premium when IV is elevated

```python
from optopsy import apply_signal, iv_rank_above

# Enter short strategies when IV rank is above 50th percentile (1-year lookback)
entry_dates = apply_signal(data, iv_rank_above(threshold=0.5, window=252))
results = op.iron_condor(data, entry_dates=entry_dates)
```

### Buy options when IV is cheap

```python
from optopsy import apply_signal, iv_rank_below

# Enter long strategies when IV rank is in the bottom 30%
entry_dates = apply_signal(data, iv_rank_below(threshold=0.3, window=252))
results = op.long_straddles(data, entry_dates=entry_dates)
```

!!! note
    IV rank signals work directly on options chain data (not stock OHLCV). The signal computes ATM implied volatility per quote date and ranks it over the trailing window.

## Custom Signal from DataFrame

Use `custom_signal()` to create a signal from any DataFrame with a boolean flag column. This lets you define arbitrary entry/exit conditions using external data sources, model outputs, or manual annotations.

```python
import pandas as pd
import optopsy as op

# Any DataFrame with dates and a boolean flag works
my_signals = pd.DataFrame({
    "underlying_symbol": ["SPY", "SPY", "SPY"],
    "quote_date": ["2018-01-02", "2018-01-03", "2018-01-04"],
    "buy": [True, False, True],
})

# Create a signal from the DataFrame
sig = op.custom_signal(my_signals, flag_col="buy")
entry_dates = op.apply_signal(my_signals, sig)

# Pass to any strategy
results = op.long_calls(data, entry_dates=entry_dates, raw=True)
```

The DataFrame must contain `underlying_symbol`, `quote_date`, and the flag column. Integer (0/1), nullable boolean, and NaN values are all handled — NaN is treated as False.

### Composing custom signals with built-in signals

```python
import optopsy as op

sig = op.custom_signal(my_signals, flag_col="buy")

# Combine with built-in signals using & and |
combined = op.signal(sig) & op.signal(op.day_of_week(1))
entry_dates = op.apply_signal(my_signals, combined)
results = op.long_calls(data, entry_dates=entry_dates)
```

## Custom Signal Functions

Any function matching the signature `(pd.DataFrame) -> pd.Series[bool]` can be used as a signal:

```python
import optopsy as op
from optopsy import apply_signal, signal, rsi_below

# Custom: only enter when underlying price is above 4000
def price_above_4000(data):
    return data["underlying_price"] > 4000

entry_dates = apply_signal(data, price_above_4000)
results = op.iron_condor(data, entry_dates=entry_dates)

# Combine custom signals with built-in ones
entry = signal(price_above_4000) & signal(rsi_below(14, 30))
entry_dates = apply_signal(data, entry)
results = op.long_calls(data, entry_dates=entry_dates)
```
