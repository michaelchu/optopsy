# Getting Started

This guide will walk you through setting up Optopsy and running your first backtest.

## Installation

Install Optopsy using pip:

```bash
# Core library
pip install optopsy

# With AI Chat UI (optional)
pip install optopsy[ui]
```

### Requirements

- Python 3.12-3.13
- Pandas 2.0 or higher
- NumPy 1.26 or higher

## Data Format

Optopsy requires historical options chain data with the following columns:

| Column | Description | Example |
|--------|-------------|---------|
| `underlying_symbol` | Ticker symbol | SPX, SPY, QQQ |
| `underlying_price` | Stock/index price | 4500.00 |
| `option_type` | Call or Put | 'c', 'p', 'call', 'put' |
| `expiration` | Option expiration date | 2023-01-20 |
| `quote_date` | Date of the quote | 2023-01-01 |
| `strike` | Strike price | 4500 |
| `bid` | Bid price | 10.50 |
| `ask` | Ask price | 11.00 |

### Optional Columns for Greeks Filtering

| Column | Description |
|--------|-------------|
| `delta` | Option delta |
| `gamma` | Option gamma |
| `theta` | Option theta |
| `vega` | Option vega |
| `volume` | Trading volume |
| `open_interest` | Open interest |

## Loading Data

### From CSV

Use `csv_data()` to load options data from a CSV file:

```python
import optopsy as op

data = op.csv_data(
    'options_data.csv',
    underlying_symbol=0,      # Column index or name
    underlying_price=1,
    option_type=2,
    expiration=3,
    quote_date=4,
    strike=5,
    bid=6,
    ask=7
)
```

The function accepts either:
- **Column indices** (integers): Position of each column
- **Column names** (strings): Header names from your CSV

### From DataFrame

If you already have a pandas DataFrame, ensure it has the required columns:

```python
import pandas as pd
import optopsy as op

# Your existing DataFrame
df = pd.read_csv('options_data.csv')

# Rename columns to match Optopsy's expected format
df = df.rename(columns={
    'Symbol': 'underlying_symbol',
    'UnderlyingPrice': 'underlying_price',
    'Type': 'option_type',
    'Expiration': 'expiration',
    'QuoteDate': 'quote_date',
    'Strike': 'strike',
    'Bid': 'bid',
    'Ask': 'ask'
})

# Now you can use it directly
results = op.long_calls(df)
```

## Running Your First Backtest

### Example: Long Calls

Let's backtest a simple long call strategy:

```python
import optopsy as op

# Load data
data = op.csv_data('SPX_2023.csv')

# Run backtest with default parameters
results = op.long_calls(data)

print(results)
```

### Example with Custom Parameters

Customize the backtest parameters:

```python
results = op.long_calls(
    data,
    max_entry_dte=60,        # Enter with 60 days to expiration
    exit_dte=30,             # Exit at 30 DTE
    dte_interval=7,          # Group results by 7-day intervals
    max_otm_pct=0.20,        # Maximum 20% out-of-the-money
    otm_pct_interval=0.05,   # Group by 5% OTM intervals
    min_bid_ask=0.10         # Minimum $0.10 bid-ask spread
)

print(results.head())
```

## Understanding the Output

### Aggregated Results (Default)

By default, strategies return aggregated statistics grouped by DTE and OTM% ranges:

```python
results = op.long_calls(data)
print(results.columns)
# ['dte_range', 'otm_pct_range', 'count', 'mean', 'std', 'min', '25%', '50%', '75%', 'max']
```

Example output:

| dte_range | otm_pct_range | count | mean | std | min | 50% | max |
|-----------|---------------|-------|------|-----|-----|-----|-----|
| (0, 7] | (0.0, 0.05] | 1250 | 0.23 | 0.45 | -1.0 | 0.15 | 2.8 |
| (0, 7] | (0.05, 0.10] | 980 | 0.18 | 0.52 | -1.0 | 0.10 | 3.2 |

### Raw Trade Data

Get individual trade details by setting `raw=True`:

```python
results = op.long_calls(data, raw=True)
print(results.columns)
# ['underlying_symbol', 'expiration', 'dte_entry', 'strike', 'entry', 'exit', 'pct_change', ...]
```

This gives you every individual trade for custom analysis.

## Next Steps

- Explore [all 28 strategies](strategies.md)
- Learn about [strategy parameters](parameters.md)
- Filter entries with [technical analysis signals](entry-signals.md)
- Try the [AI Chat UI](chat-ui.md) for natural language backtesting
- See more [examples](examples.md) with Greeks filtering and slippage
- Read the [API Reference](api-reference.md) for detailed function documentation

## Common Issues

### Date Format Errors

If you encounter date parsing errors, ensure your dates are in a standard format:
- ISO format: `2023-01-20`
- US format: `01/20/2023`
- European format: `20/01/2023`

The `csv_data()` function will attempt to auto-detect date formats.

### Missing Columns

If you see a "KeyError" for a column, check that:
1. The column exists in your data
2. You've specified the correct column index or name in `csv_data()`
3. Column names match exactly (case-sensitive)

### Empty Results

If your backtest returns no results:
- Check your parameter ranges (DTE, OTM%, etc.)
- Verify your data covers the time period you're testing
- Ensure bid/ask spreads meet the `min_bid_ask` threshold
