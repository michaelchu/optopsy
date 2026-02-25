# Covered Strategies

Covered strategies combine stock positions with options for income generation or downside protection.

## Stock Data

Both `covered_call` and `protective_put` accept an optional `stock_data` parameter for actual stock prices. When provided, the underlying leg uses real stock close prices instead of a synthetic deep ITM call.

We recommend [yfinance](https://github.com/ranaroussi/yfinance) for downloading stock data:

```bash
pip install yfinance
```

The `stock_data` parameter accepts yfinance output directly — no manual transformation needed:

```python
import yfinance as yf
import optopsy as op

stock = yf.download("SPY", start="2023-01-01", end="2023-12-31")
data = op.csv_data("SPY_options.csv")

results = op.covered_call(data, stock_data=stock)
```

Any DataFrame with a `close`/`Close` column and dates (as index or column) will work. The `underlying_symbol` is inferred from the options data for single-symbol datasets.

!!! note "Synthetic Fallback"
    When `stock_data` is omitted, covered strategies use deep ITM calls as synthetic stock positions. This is useful when you only have options data available.

## Covered Call

#### Description
Generate income by selling calls against a long stock position.

**Composition:**
- Long underlying position (actual stock or synthetic deep ITM call)
- Short 1 call at higher strike

#### Example
```python
import yfinance as yf
import optopsy as op

# With actual stock data (recommended)
stock = yf.download("SPY", start="2023-01-01", end="2023-12-31")
results = op.covered_call(data, stock_data=stock, max_entry_dte=45, exit_dte=21)

# Without stock data (synthetic approach)
results = op.covered_call(data, max_entry_dte=45, exit_dte=21)
```

#### Use Cases
- Generate income on stock holdings
- Willing to sell stock at higher price
- Neutral to slightly bullish outlook

---

## Protective Put (Married Put) {#protective-put}

#### Description
Buy downside protection by purchasing puts against a long stock position.

**Composition:**
- Long underlying position (actual stock or synthetic deep ITM call)
- Long 1 put at lower strike for protection

#### Example
```python
import yfinance as yf
import optopsy as op

# With actual stock data (recommended)
stock = yf.download("SPY", start="2023-01-01", end="2023-12-31")
results = op.protective_put(data, stock_data=stock, max_entry_dte=90, exit_dte=60)

# Without stock data (synthetic approach)
results = op.protective_put(data, max_entry_dte=90, exit_dte=60)
```

#### Use Cases
- Hedging long stock positions
- Protection during uncertain periods
- Portfolio insurance
