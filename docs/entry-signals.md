# Entry Signals

Filter strategy entries using 80+ technical analysis signals powered by [pandas-ta-classic](https://github.com/xgboosted/pandas-ta-classic). Use `apply_signal` to compute valid dates, then pass them as `entry_dates` or `exit_dates` to any strategy.

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

### Momentum

| Signal | Description | Default Parameters |
|--------|-------------|-------------------|
| `rsi_below`, `rsi_above` | RSI threshold (oversold / overbought) | `period=14`, `threshold=30` / `70` |
| `macd_cross_above`, `macd_cross_below` | MACD / signal line crossover | `fast=12`, `slow=26`, `signal_period=9` |
| `stoch_below`, `stoch_above` | Stochastic %K threshold | `k_period=14`, `d_period=3`, `threshold=20` / `80` |
| `stochrsi_below`, `stochrsi_above` | Stochastic RSI %K threshold | `period=14`, `rsi_period=14`, `k_smooth=3`, `d_smooth=3`, `threshold=20` / `80` |
| `willr_below`, `willr_above` | Williams %R threshold | `period=14`, `threshold=-80` / `-20` |
| `cci_below`, `cci_above` | Commodity Channel Index threshold | `period=20`, `threshold=-100` / `100` |
| `roc_above`, `roc_below` | Rate of Change threshold | `period=10`, `threshold=0` |
| `ppo_cross_above`, `ppo_cross_below` | Percentage Price Oscillator crossover | `fast=12`, `slow=26`, `signal_period=9` |
| `tsi_cross_above`, `tsi_cross_below` | True Strength Index crossover | `long=25`, `short=13`, `signal_period=13` |
| `cmo_above`, `cmo_below` | Chande Momentum Oscillator threshold | `period=14`, `threshold=50` / `-50` |
| `uo_above`, `uo_below` | Ultimate Oscillator threshold | `fast=7`, `medium=14`, `slow=28`, `threshold=70` / `30` |
| `squeeze_on`, `squeeze_off` | Squeeze (BB inside/outside KC) | `bb_length=20`, `bb_std=2.0`, `kc_length=20`, `kc_scalar=1.5` |
| `ao_above`, `ao_below` | Awesome Oscillator threshold | `fast=5`, `slow=34`, `threshold=0` |
| `smi_cross_above`, `smi_cross_below` | Stochastic Momentum Index crossover | `fast=5`, `slow=20`, `signal_period=5` |
| `kst_cross_above`, `kst_cross_below` | Know Sure Thing crossover | *(uses pandas-ta defaults)* |
| `fisher_cross_above`, `fisher_cross_below` | Fisher Transform crossover | `period=9` |

### Overlap (Moving Averages)

| Signal | Description | Default Parameters |
|--------|-------------|-------------------|
| `sma_above`, `sma_below` | Price vs. Simple Moving Average | `period=20` |
| `ema_cross_above`, `ema_cross_below` | EMA fast/slow crossover | `fast=10`, `slow=50` |
| `dema_cross_above`, `dema_cross_below` | Double EMA crossover | `fast=10`, `slow=50` |
| `tema_cross_above`, `tema_cross_below` | Triple EMA crossover | `fast=10`, `slow=50` |
| `hma_cross_above`, `hma_cross_below` | Hull MA crossover | `fast=10`, `slow=50` |
| `kama_cross_above`, `kama_cross_below` | Kaufman Adaptive MA crossover | `fast=10`, `slow=50` |
| `wma_cross_above`, `wma_cross_below` | Weighted MA crossover | `fast=10`, `slow=50` |
| `zlma_cross_above`, `zlma_cross_below` | Zero-Lag MA crossover | `fast=10`, `slow=50` |
| `alma_cross_above`, `alma_cross_below` | Arnaud Legoux MA crossover | `fast=10`, `slow=50` |

### Volatility

| Signal | Description | Default Parameters |
|--------|-------------|-------------------|
| `atr_above`, `atr_below` | ATR vs. median ATR regime | `period=14`, `multiplier=1.0` |
| `bb_above_upper`, `bb_below_lower` | Price vs. Bollinger Bands | `length=20`, `std=2.0` |
| `kc_above_upper`, `kc_below_lower` | Price vs. Keltner Channel | `length=20`, `scalar=1.5` |
| `donchian_above_upper`, `donchian_below_lower` | Price vs. Donchian Channel | `lower_length=20`, `upper_length=20` |
| `natr_above`, `natr_below` | Normalized ATR threshold (% of price) | `period=14`, `threshold=2.0` / `1.0` |
| `massi_above`, `massi_below` | Mass Index threshold (reversal signal) | `fast=9`, `slow=25`, `threshold=27` / `26.5` |

### Trend

| Signal | Description | Default Parameters |
|--------|-------------|-------------------|
| `adx_above`, `adx_below` | Average Directional Index threshold | `period=14`, `threshold=25` / `20` |
| `aroon_cross_above`, `aroon_cross_below` | Aroon Up/Down crossover | `period=25` |
| `supertrend_buy`, `supertrend_sell` | Supertrend direction flip | `period=7`, `multiplier=3.0` |
| `psar_buy`, `psar_sell` | Parabolic SAR direction flip | `af0=0.02`, `af=0.02`, `max_af=0.2` |
| `chop_above`, `chop_below` | Choppiness Index threshold | `period=14`, `threshold=61.8` / `38.2` |
| `vhf_above`, `vhf_below` | Vertical Horizontal Filter threshold | `period=28`, `threshold=0.4` |

### Volume

Require OHLCV data with a `volume` column.

| Signal | Description | Default Parameters |
|--------|-------------|-------------------|
| `mfi_above`, `mfi_below` | Money Flow Index threshold | `period=14`, `threshold=80` / `20` |
| `obv_cross_above_sma`, `obv_cross_below_sma` | OBV vs. its SMA crossover | `sma_period=20` |
| `cmf_above`, `cmf_below` | Chaikin Money Flow threshold | `period=20`, `threshold=0.05` / `-0.05` |
| `ad_cross_above_sma`, `ad_cross_below_sma` | A/D Line vs. its SMA crossover | `sma_period=20` |

### IV Rank

Require options data with an `implied_volatility` column.

| Signal | Description | Default Parameters |
|--------|-------------|-------------------|
| `iv_rank_above`, `iv_rank_below` | IV rank percentile threshold | `threshold=0.5`, `window=252` |

### Calendar

| Signal | Description | Default Parameters |
|--------|-------------|-------------------|
| `day_of_week` | Restrict to specific weekdays | Days: `0`=Mon ... `4`=Fri |

### Custom

| Signal | Description | Default Parameters |
|--------|-------------|-------------------|
| `custom_signal` | Boolean flag from a DataFrame column | `flag_col='signal'` |

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

### Stochastic - oversold entry

```python
from optopsy import apply_signal, stoch_below

entry_dates = apply_signal(data, stoch_below(k_period=14, d_period=3, threshold=20))
results = op.long_calls(data, entry_dates=entry_dates)
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

### ADX - trend strength filter

Only enter trend-following strategies when ADX confirms a strong trend:

```python
from optopsy import apply_signal, adx_above, signal, ema_cross_above

entry = signal(adx_above(period=14, threshold=25)) & signal(ema_cross_above(10, 50))
entry_dates = apply_signal(data, entry)
results = op.long_calls(data, entry_dates=entry_dates)
```

### Supertrend - trend direction

Enter when Supertrend flips bullish:

```python
from optopsy import apply_signal, supertrend_buy

entry_dates = apply_signal(data, supertrend_buy(period=7, multiplier=3.0))
results = op.long_call_spread(data, entry_dates=entry_dates)
```

### ATR - low-volatility regime filter

Only sell premium in low-volatility regimes:

```python
from optopsy import apply_signal, atr_below

entry_dates = apply_signal(data, atr_below(period=14, multiplier=0.75))
results = op.iron_condor(data, entry_dates=entry_dates)
```

### Keltner Channel - breakout entry

Enter when price breaks above the upper Keltner Channel:

```python
from optopsy import apply_signal, kc_above_upper

entry_dates = apply_signal(data, kc_above_upper(length=20, scalar=1.5))
results = op.long_calls(data, entry_dates=entry_dates)
```

### Squeeze - volatility compression

Enter when the squeeze releases (Bollinger Bands expand outside Keltner Channels):

```python
from optopsy import apply_signal, squeeze_off

entry_dates = apply_signal(data, squeeze_off())
results = op.long_straddles(data, entry_dates=entry_dates)
```

### Volume - MFI oversold

Enter when Money Flow Index indicates oversold conditions:

```python
from optopsy import apply_signal, mfi_below

entry_dates = apply_signal(stock_df, mfi_below(period=14, threshold=20))
results = op.long_calls(data, entry_dates=entry_dates)
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

By default, signals compute indicators from the option chain's `close` column. For more accurate TA signals (especially those needing high/low/volume data), use `apply_signal` on a separate stock OHLCV DataFrame and pass the result as `entry_dates`:

```python
import pandas as pd
import optopsy as op
from optopsy import apply_signal, adx_above, supertrend_buy, signal

# Load OHLCV stock data (must have: underlying_symbol, quote_date, close;
# optional: open, high, low, volume)
stock_df = pd.read_csv("SPX_daily_ohlcv.csv", parse_dates=["quote_date"])

# Compute entry dates from stock data using real high/low for trend signals
entry = signal(adx_above(period=14, threshold=25)) & signal(supertrend_buy())
entry_dates = apply_signal(stock_df, entry)

# Pass pre-computed dates to the strategy
results = op.long_straddles(data, entry_dates=entry_dates)
```

!!! tip
    Signals that use high/low data (Stochastic, Williams %R, CCI, ATR, Keltner, Donchian, ADX, Aroon, Supertrend, PSAR, Choppiness, MFI, OBV, CMF, A/D) will fall back to using `close` as a proxy if `high` and `low` columns are not present. For best accuracy, provide real OHLCV data.

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

# Custom: only enter when close price is above 4000
def price_above_4000(data):
    return data["close"] > 4000

entry_dates = apply_signal(data, price_above_4000)
results = op.iron_condor(data, entry_dates=entry_dates)

# Combine custom signals with built-in ones
entry = signal(price_above_4000) & signal(rsi_below(14, 30))
entry_dates = apply_signal(data, entry)
results = op.long_calls(data, entry_dates=entry_dates)
```
