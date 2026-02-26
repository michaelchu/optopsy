# Optopsy

An AI-powered research and backtesting tool for options strategies.

## What is Optopsy?

Optopsy combines a Python backtesting engine with a conversational AI interface that fetches data from online or local sources, runs strategies, and interprets results — so you can go from *"How do iron condors perform on SPX?"* to detailed performance statistics in seconds, not spreadsheets.

## Key Features

- **28 Built-in Strategies** - From simple calls/puts to iron condors, butterflies, calendars, and diagonals
- **Strategy Simulation** - Chronological simulation with capital tracking, position limits, and equity curves via `simulate()`
- **Risk Metrics** - Sharpe, Sortino, VaR, CVaR, Calmar, Omega, tail ratio, and more via `compute_risk_metrics()`
- **Entry Signals** - Filter entries with TA indicators (RSI, MACD, Bollinger Bands, EMA, ATR, IV Rank) via [pandas-ta-classic](https://github.com/xgboosted/pandas-ta-classic)
- **Custom Signals** - Use `custom_signal()` to drive entries from any DataFrame with a boolean flag column
- **Greeks Filtering** - Filter options by delta to target specific probability ranges
- **Slippage Modeling** - Realistic fills with mid, spread, or liquidity-based slippage
- **Flexible Grouping** - Analyze results by DTE, OTM%, and delta intervals
- **Any Data Source** - Works with any options data in CSV or DataFrame format
- **Pandas Native** - Returns DataFrames that integrate with your existing workflow
- **AI Chat UI** - Interactive [AI-powered chat interface](chat-ui.md) with conversation starters, settings panel, and result caching

## Quick Example

```python
import optopsy as op

# Load your options data
data = op.csv_data('SPX_options.csv')

# Backtest an iron condor strategy
results = op.iron_condor(
    data,
    max_entry_dte=45,
    exit_dte=21,
    max_otm_pct=0.25
)

print(results)
```

## Installation

```bash
# Core library
pip install optopsy

# With AI Chat UI
pip install optopsy[ui]
```

**Requirements:** Python 3.12-3.13, Pandas 2.0+, NumPy 1.26+

## Getting Help

- Check the [Getting Started](getting-started.md) guide for a detailed walkthrough
- Browse [Strategies](strategies.md) for available options strategies
- Review [Parameters](parameters.md) for configuration options
- Learn about [Entry Signals](entry-signals.md) for TA-based entry filtering
- Try the [AI Chat UI](chat-ui.md) for natural language backtesting
- See [Examples](examples.md) for common use cases
- View the [API Reference](api-reference.md) for complete function documentation

## Contributing

Contributions are welcome! See the [Contributing Guide](contributing.md) for details.

## License

Optopsy is released under the AGPL-3.0 License. See the [GitHub repository](https://github.com/michaelchu/optopsy) for more information.
