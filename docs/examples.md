# Examples

This page provides real-world examples of using Optopsy for options backtesting.

## Basic Examples

#### Simple Long Calls Backtest

```python
import optopsy as op

# Load data
data = op.csv_data('SPX_2023.csv')

# Backtest long calls
results = op.long_calls(data)

print(results.head())
```

#### Iron Condor with Custom Parameters

```python
results = op.iron_condor(
    data,
    max_entry_dte=45,
    exit_dte=21,
    leg2_delta={"target": 0.25, "min": 0.20, "max": 0.30},  # short strikes
    leg3_delta={"target": 0.25, "min": 0.20, "max": 0.30},
    min_bid_ask=0.10
)

# Filter for best performing DTE ranges
best_dte = results[results['mean'] > 0.20]
print(best_dte)
```

## Advanced Examples

#### Delta-Targeted Iron Condors

Target specific delta ranges for short strikes:

```python
results = op.iron_condor(
    data,
    max_entry_dte=45,
    exit_dte=21,
    leg2_delta={"target": 0.16, "min": 0.15, "max": 0.20},
    leg3_delta={"target": 0.16, "min": 0.15, "max": 0.20},
    delta_interval=0.05,
    min_bid_ask=0.10
)

# Analyze by delta ranges
print(results.groupby('delta_range')['mean'].describe())
```

#### Earnings Straddle Strategy

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

# Backtest ATM straddles
results = op.long_straddles(
    earnings_df,
    max_entry_dte=7,  # Enter 1 week before
    exit_dte=0,       # Hold through earnings
    leg1_delta={"target": 0.50, "min": 0.45, "max": 0.55},  # ATM
)

print(results)
```

#### Time Decay Analysis

Compare different exit times for short strangles:

```python
exit_times = [0, 7, 14, 21, 30]
results_by_exit = {}

for exit_dte in exit_times:
    results = op.short_strangles(
        data,
        max_entry_dte=45,
        exit_dte=exit_dte,
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

#### Slippage Comparison

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

## Early Exit Examples

#### Stop Loss and Take Profit

Close positions early based on P&L thresholds:

```python
# Short puts with early exit rules
trades = op.short_puts(
    data,
    max_entry_dte=45,
    exit_dte=0,
    stop_loss=-1.0,      # Close if losing 100%+
    take_profit=0.50,     # Close if gaining 50%+
    raw=True
)

# Analyze exit types
print(trades['exit_type'].value_counts())

# Compare returns by exit type
print(trades.groupby('exit_type')['pct_change'].describe())
```

#### Maximum Holding Period

Limit how long positions are held:

```python
trades = op.iron_condor(
    data,
    max_entry_dte=45,
    max_hold_days=21,     # Exit after 21 calendar days
    take_profit=0.50,     # Or take profit at 50%
    raw=True
)

print(f"Average days held: {trades['days_held'].mean():.0f}")
```

## Commission Examples

#### Per-Contract Commission

```python
# Simple per-contract fee
results = op.short_puts(data, commission=0.65, raw=True)
```

#### Full Fee Structure

```python
from optopsy import Commission

results = op.iron_condor(
    data,
    commission=Commission(
        per_contract=0.65,
        base_fee=4.95,
    ),
    raw=True
)
```

## Data Analysis Examples

#### Raw Trade Data Analysis

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

#### Monthly Performance

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

#### Strike Selection Analysis

Analyze performance by delta range:

```python
results = op.short_puts(
    data,
    max_entry_dte=45,
    exit_dte=21,
    delta_interval=0.05,
)

# Find optimal delta range
optimal = results.loc[results['mean'].idxmax()]
print(f"Optimal Delta Range: {optimal['delta_range']}")
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

Simulate a weighted portfolio across multiple strategies using `simulate_portfolio()`:

```python
import optopsy as op

spy = op.csv_data('SPY_2023.csv')
qqq = op.csv_data('QQQ_2023.csv')

result = op.simulate_portfolio(
    legs=[
        {
            "data": spy,
            "strategy": op.short_puts,
            "weight": 0.6,
            "max_entry_dte": 45,
            "exit_dte": 14,
        },
        {
            "data": qqq,
            "strategy": op.iron_condor,
            "weight": 0.4,
            "max_entry_dte": 30,
            "exit_dte": 7,
        },
    ],
    capital=100_000,
)

# Portfolio-level summary
print(result.summary)

# Combined trade log (includes a 'leg' column)
print(result.trade_log)

# Portfolio equity curve
print(result.equity_curve)

# Access individual leg results
for name, leg_result in result.leg_results.items():
    print(f"\n{name}:")
    print(leg_result.summary)
```

## Strategy Simulation

Use `simulate()` for chronological backtesting with capital tracking, position limits, and a full equity curve:

```python
import optopsy as op

data = op.csv_data('SPX_2023.csv')

# Simulate short puts with $100k capital
result = op.simulate(
    data,
    op.short_puts,
    capital=100_000,
    quantity=1,
    max_positions=2,
    multiplier=100,
    selector='nearest',        # Pick ATM strike per entry date
    max_entry_dte=45,
    exit_dte=14,
)

# Summary statistics (includes Sharpe, Sortino, VaR, max drawdown, etc.)
print(result.summary)

# Individual trade log with P&L
print(result.trade_log)

# Equity curve indexed by exit date
print(result.equity_curve)
```

The `selector` parameter controls how a trade is picked when multiple candidates exist for the same entry date:

| Selector | Behavior |
|----------|----------|
| `'nearest'` | Closest to ATM (lowest absolute OTM%) |
| `'highest_premium'` | Largest credit received |
| `'lowest_premium'` | Cheapest debit paid |
| `'first'` | First candidate (deterministic) |

You can also pass a custom callable as the selector.

## Risk Metrics

Optopsy provides built-in risk metrics via the `metrics` module. These are used automatically by `simulate()` and are also available standalone:

```python
import optopsy as op

trades = op.iron_condor(data, raw=True)
returns = trades['pct_change']

# Individual metrics
print(f"Sharpe: {op.sharpe_ratio(returns):.2f}")
print(f"Sortino: {op.sortino_ratio(returns):.2f}")
print(f"Win Rate: {op.win_rate(returns):.1%}")
print(f"Profit Factor: {op.profit_factor(returns):.2f}")
print(f"VaR (95%): {op.value_at_risk(returns, 0.95):.2%}")
print(f"CVaR (95%): {op.conditional_value_at_risk(returns, 0.95):.2%}")
print(f"Max Drawdown: {op.max_drawdown_from_returns(returns):.2%}")
print(f"Calmar: {op.calmar_ratio(returns):.2f}")
print(f"Omega: {op.omega_ratio(returns):.2f}")
print(f"Tail Ratio: {op.tail_ratio(returns):.2f}")

# Or compute all at once
all_metrics = op.compute_risk_metrics(returns)
print(all_metrics)
```

## Custom Signal Entry Example

Use `custom_signal()` to drive entries from any external data source:

```python
import pandas as pd
import optopsy as op

# Load your own signal data (model output, manual flags, external indicator, etc.)
my_flags = pd.DataFrame({
    "underlying_symbol": ["SPY"] * 5,
    "quote_date": pd.date_range("2023-01-02", periods=5, freq="B"),
    "go": [True, False, True, False, True],
})

sig = op.custom_signal(my_flags, flag_col="go")
entry_dates = op.apply_signal(my_flags, sig)

data = op.csv_data('SPY_2023.csv')
results = op.long_calls(data, entry_dates=entry_dates)
print(results)
```

## Performance Metrics (Manual)

Calculate performance statistics manually from raw trades:

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

!!! tip
    For most use cases, prefer `op.simulate()` or `op.compute_risk_metrics()` over manual calculations — they handle edge cases, annualisation, and additional metrics automatically.

## Working with Different Data Sources

#### Historical Options Data Providers

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

#### 1. Always Use Filters

```python
# Bad: No filtering
results = op.iron_condor(data)

# Good: Filtered for quality
results = op.iron_condor(
    data,
    max_entry_dte=45,
    exit_dte=21,
    min_bid_ask=0.10,
    leg2_delta={"target": 0.20, "min": 0.15, "max": 0.25},
    leg3_delta={"target": 0.20, "min": 0.15, "max": 0.25},
)
```

#### 2. Compare Apples to Apples

```python
# Use same parameters when comparing strategies
params = {
    'max_entry_dte': 45,
    'exit_dte': 21,
}

ic_results = op.iron_condor(data, **params)
strangle_results = op.short_strangles(data, **params)
```

#### 3. Realistic Slippage

```python
# Use liquidity mode for realistic results
results = op.iron_condor(
    data,
    slippage='liquidity',
    fill_ratio=0.5,
    reference_volume=1000
)
```

## Entry Signal Examples

Optopsy supports filtering entries with technical analysis indicators. See the [Entry Signals](entry-signals.md) page for the full reference. Here's a quick example:

```python
from optopsy import apply_signal, rsi_below, sma_above, signal

# Enter long calls only when RSI < 30 AND price is above the 50-day SMA
entry = signal(rsi_below(14, 30)) & signal(sma_above(50))
entry_dates = apply_signal(data, entry)
results = op.long_calls(data, entry_dates=entry_dates)
```

## Data Sources

Optopsy works with any historical options data in CSV or DataFrame format. Some sources:

- [EODHD US Stock Options Data API](https://eodhd.com/financial-apis/options-data-api) - Built-in integration via the [Chat UI](chat-ui.md) (API key required)
- [HistoricalOptionData.com](https://historicaloptiondata.com/) - Free samples available
- [CBOE DataShop](https://datashop.cboe.com/) - Official exchange data
- [Polygon.io](https://polygon.io/) - Options data API
- Your broker's data export (Schwab, IBKR, Tastytrade, etc.)

## Next Steps

- Review [Strategy documentation](strategies.md) for specific strategy details
- Check [Parameters](parameters.md) for all configuration options
- Learn about [Entry Signals](entry-signals.md) for TA-based filtering
- Try the [AI Chat UI](chat-ui.md) for natural language backtesting
- See [API Reference](api-reference.md) for function signatures
