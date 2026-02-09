# Optopsy Documentation

A fast, flexible backtesting library for options strategies in Python.

## What is Optopsy?

Optopsy helps you answer questions like *"How do iron condors perform on SPX?"* or *"What delta range produces the best results for covered calls?"* by generating comprehensive performance statistics from historical options data.

## Key Features

- **28 Built-in Strategies** - From simple calls/puts to iron condors, butterflies, calendars, and diagonals
- **Greeks Filtering** - Filter options by delta to target specific probability ranges
- **Slippage Modeling** - Realistic fills with mid, spread, or liquidity-based slippage
- **Flexible Grouping** - Analyze results by DTE, OTM%, and delta intervals
- **Any Data Source** - Works with any options data in CSV or DataFrame format
- **Pandas Native** - Returns DataFrames that integrate with your existing workflow

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
pip install optopsy
```

**Requirements:** Python 3.8+, Pandas 2.0+, NumPy 1.26+

## Getting Help

- Check the [Getting Started](getting-started.md) guide for a detailed walkthrough
- Browse [Strategies](strategies.md) for available options strategies
- Review [Parameters](parameters.md) for configuration options
- See [Examples](examples.md) for common use cases
- View the [API Reference](api-reference.md) for complete function documentation

## Contributing

Contributions are welcome! See the [Contributing Guide](contributing.md) for details.

## License

Optopsy is released under the GPL-3.0 License. See the [GitHub repository](https://github.com/michaelchu/optopsy) for more information.
