# Examples

This page provides real-world examples of using Optopsy for options backtesting.

## Basic Examples

### Simple Long Calls Backtest

```python
import optopsy as op

# Load data
data = op.csv_data('SPX_2023.csv')

# Backtest long calls
results = op.long_calls(data)

print(results.head())
```

### Iron Condor with Custom Parameters

```python
results = op.iron_condor(
    data,
    max_entry_dte=45,
    exit_dte=21,
    max_otm_pct=0.25,
    min_bid_ask=0.10
)

# Filter for best performing DTE ranges
best_dte = results[results['mean'] > 0.20]
print(best_dte)
```

## Advanced Examples

### Delta-Neutral Iron Condors

Target specific delta ranges for short strikes:

```python
results = op.iron_condor(
    data,
    max_entry_dte=45,
    exit_dte=21,
    delta_min=0.15,  # Target 15-20 delta
    delta_max=0.20,
    delta_interval=0.05,
    min_bid_ask=0.10
)

# Analyze by delta ranges
print(results.groupby('delta_range')['mean'].describe())
```

### Earnings Straddle Strategy

Backtest long straddles around earnings events:

```python
# Load earnings dates
earnings_dates = ['2023-01-15', '2023-04-15', '2023-07-15', '2023-10-15']

# Filter data around earnings (±7 days)
import pandas as pd
data['quote_date'] = pd.to_datetime(data['quote_date'])

earnings_data = []
for date in pd.to_datetime(earnings_dates):
    mask = (data['quote_date'] >= date - pd.Timedelta(days=7)) & \
           (data['quote_date'] <= date + pd.Timedelta(days=7))
    earnings_data.append(data[mask])

earnings_df = pd.concat(earnings_data)

# Backtest straddles
results = op.long_straddles(
    earnings_df,
    max_entry_dte=7,  # Enter 1 week before
    exit_dte=0,       # Hold through earnings
    max_otm_pct=0.05  # ATM straddles
)

print(results)
```

### Time Decay Analysis

Compare different exit times for short strangles:

```python
exit_times = [0, 7, 14, 21, 30]
results_by_exit = {}

for exit_dte in exit_times:
    results = op.short_strangles(
        data,
        max_entry_dte=45,
        exit_dte=exit_dte,
        max_otm_pct=0.30
    )
    results_by_exit[exit_dte] = results['mean'].mean()

# Plot results
import matplotlib.pyplot as plt
plt.bar(exit_times, results_by_exit.values())
plt.xlabel('Exit DTE')
plt.ylabel('Mean Return')
plt.title('Short Strangle Returns by Exit Time')
plt.show()
```

### Slippage Comparison

Compare different slippage models:

```python
slippage_modes = ['mid', 'spread', 'liquidity']
results_comparison = {}

for mode in slippage_modes:
    results = op.iron_condor(
        data,
        max_entry_dte=45,
        exit_dte=21,
        slippage=mode,
        fill_ratio=0.5,
        reference_volume=1000
    )
    results_comparison[mode] = results['mean'].mean()

print("Slippage Model Comparison:")
for mode, avg_return in results_comparison.items():
    print(f"{mode}: {avg_return:.2%}")
```

## Data Analysis Examples

### Raw Trade Data Analysis

Get individual trades for custom analysis:

```python
# Get raw trade data
trades = op.iron_condor(
    data,
    max_entry_dte=45,
    exit_dte=21,
    raw=True  # Return individual trades
)

# Custom analysis
import pandas as pd

# Win rate
win_rate = (trades['pct_change'] > 0).mean()
print(f"Win Rate: {win_rate:.1%}")

# Average winner vs loser
avg_winner = trades[trades['pct_change'] > 0]['pct_change'].mean()
avg_loser = trades[trades['pct_change'] < 0]['pct_change'].mean()
print(f"Avg Winner: {avg_winner:.2%}")
print(f"Avg Loser: {avg_loser:.2%}")

# Profit factor
total_profit = trades[trades['pct_change'] > 0]['pct_change'].sum()
total_loss = abs(trades[trades['pct_change'] < 0]['pct_change'].sum())
profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
print(f"Profit Factor: {profit_factor:.2f}")
```

### Monthly Performance

Analyze strategy performance by month:

```python
trades = op.short_puts(data, raw=True)

# Convert to datetime
trades['entry_date'] = pd.to_datetime(trades['quote_date'])
trades['month'] = trades['entry_date'].dt.to_period('M')

# Group by month
monthly_perf = trades.groupby('month').agg({
    'pct_change': ['count', 'mean', 'std', 'sum']
})

print(monthly_perf)
```

### Strike Selection Analysis

Analyze performance by OTM percentage:

```python
results = op.short_puts(
    data,
    max_entry_dte=45,
    exit_dte=21,
    max_otm_pct=0.50,
    otm_pct_interval=0.05
)

# Find optimal OTM range
optimal = results.loc[results['mean'].idxmax()]
print(f"Optimal OTM Range: {optimal['otm_pct_range']}")
print(f"Mean Return: {optimal['mean']:.2%}")
print(f"Count: {optimal['count']:.0f}")
```

## Multi-Strategy Comparison

Compare multiple strategies:

```python
strategies = {
    'Long Calls': op.long_calls,
    'Short Puts': op.short_puts,
    'Iron Condor': op.iron_condor,
    'Long Straddle': op.long_straddles
}

comparison = {}
for name, strategy_func in strategies.items():
    results = strategy_func(
        data,
        max_entry_dte=45,
        exit_dte=21
    )
    comparison[name] = {
        'mean': results['mean'].mean(),
        'std': results['std'].mean(),
        'max': results['max'].max(),
        'min': results['min'].min()
    }

# Display comparison
df_comparison = pd.DataFrame(comparison).T
print(df_comparison)
```

## Portfolio Simulation

Simulate a portfolio of multiple strategies:

```python
# Define portfolio allocation
portfolio = {
    'iron_condor': 0.50,
    'short_strangles': 0.30,
    'long_call_spread': 0.20
}

# Get raw trades for each strategy
trades = {}
trades['iron_condor'] = op.iron_condor(data, raw=True)
trades['short_strangles'] = op.short_strangles(data, raw=True)
trades['long_call_spread'] = op.long_call_spread(data, raw=True)

# Weight returns by allocation
for strategy, weight in portfolio.items():
    trades[strategy]['weighted_return'] = trades[strategy]['pct_change'] * weight

# Combine all trades
all_trades = pd.concat([
    trades[s][['quote_date', 'weighted_return']]
    for s in portfolio.keys()
])

# Aggregate by date
portfolio_returns = all_trades.groupby('quote_date')['weighted_return'].sum()

print(f"Portfolio Mean Return: {portfolio_returns.mean():.2%}")
print(f"Portfolio Std Dev: {portfolio_returns.std():.2%}")
print(f"Sharpe Ratio (annualized): {(portfolio_returns.mean() / portfolio_returns.std()) * (252**0.5):.2f}")
```

## Performance Metrics

Calculate comprehensive performance statistics:

```python
def calculate_metrics(trades_df):
    """Calculate performance metrics for a strategy."""
    returns = trades_df['pct_change']

    metrics = {
        'Total Trades': len(returns),
        'Win Rate': (returns > 0).mean(),
        'Mean Return': returns.mean(),
        'Median Return': returns.median(),
        'Std Dev': returns.std(),
        'Max Win': returns.max(),
        'Max Loss': returns.min(),
        'Profit Factor': returns[returns > 0].sum() / abs(returns[returns < 0].sum()),
        'Sharpe Ratio': returns.mean() / returns.std() if returns.std() > 0 else 0
    }

    return pd.Series(metrics)

# Apply to strategy
trades = op.iron_condor(data, raw=True)
metrics = calculate_metrics(trades)
print(metrics)
```

## Working with Different Data Sources

### Historical Options Data Providers

```python
# Example: Loading from different CSV formats

# Format 1: CBOE data export
data = op.csv_data(
    'cboe_spx.csv',
    underlying_symbol='underlying_symbol',
    underlying_price='underlying_bid_1545',
    option_type='option_type',
    expiration='expiration',
    quote_date='quote_date',
    strike='strike',
    bid='bid',
    ask='ask'
)

# Format 2: Indexed columns
data = op.csv_data(
    'provider_data.csv',
    underlying_symbol=0,
    underlying_price=1,
    option_type=2,
    expiration=3,
    quote_date=4,
    strike=5,
    bid=6,
    ask=7
)
```

## Best Practices

### 1. Always Use Filters

```python
# Bad: No filtering
results = op.iron_condor(data)

# Good: Filtered for quality
results = op.iron_condor(
    data,
    max_entry_dte=45,
    exit_dte=21,
    min_bid_ask=0.10,  # Ensure liquidity
    max_otm_pct=0.30
)
```

### 2. Compare Apples to Apples

```python
# Use same parameters when comparing strategies
params = {
    'max_entry_dte': 45,
    'exit_dte': 21,
    'max_otm_pct': 0.25
}

ic_results = op.iron_condor(data, **params)
strangle_results = op.short_strangles(data, **params)
```

### 3. Realistic Slippage

```python
# Use liquidity mode for realistic results
results = op.iron_condor(
    data,
    slippage='liquidity',
    fill_ratio=0.5,
    reference_volume=1000
)
```

## Next Steps

- Review [Strategy documentation](strategies.md) for specific strategy details
- Check [Parameters](parameters.md) for all configuration options
- See [API Reference](api-reference.md) for function signatures
- Explore the `samples/` directory in the repository for more examples
