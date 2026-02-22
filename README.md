[![CI](https://github.com/michaelchu/optopsy/actions/workflows/ci.yml/badge.svg)](https://github.com/michaelchu/optopsy/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/optopsy.svg)](https://badge.fury.io/py/optopsy)
[![Downloads](https://pepy.tech/badge/optopsy)](https://pepy.tech/project/optopsy)
[![Python](https://img.shields.io/pypi/pyversions/optopsy)](https://pypi.org/project/optopsy/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

# Optopsy

A fast, flexible backtesting library for options strategies in Python.

Optopsy helps you answer questions like *"How do iron condors perform on SPX?"* or *"What delta range produces the best results for covered calls?"* by generating comprehensive performance statistics from historical options data.

[Full Documentation](https://michaelchu.github.io/optopsy/) | [API Reference](https://michaelchu.github.io/optopsy/api-reference/) | [Examples](https://michaelchu.github.io/optopsy/examples/)

## Features

- **28 Built-in Strategies** - From simple calls/puts to iron condors, butterflies, calendars, and diagonals
- **Entry Signals** - Filter entries with TA indicators (RSI, MACD, Bollinger Bands, EMA, ATR) via pandas-ta
- **Greeks Filtering** - Filter options by delta to target specific probability ranges
- **Slippage Modeling** - Realistic fills with mid, spread, or liquidity-based slippage
- **Flexible Grouping** - Analyze results by DTE, OTM%, and delta intervals
- **Any Data Source** - Works with any options data in CSV or DataFrame format
- **Pandas Native** - Returns DataFrames that integrate with your existing workflow
- **AI Chat UI** - Interactive AI-powered interface for running backtests with natural language

## AI Chat UI (Beta)

An AI-powered chat interface that lets you fetch data, run backtests, and interpret results using natural language.

![AI Chat UI](docs/images/chat-ui.png)

```bash
pip install optopsy[ui]
optopsy-chat
```

See the [Chat UI documentation](https://michaelchu.github.io/optopsy/chat-ui/) for setup and configuration details.

## Installation

```bash
# Core library only
pip install optopsy

# With AI Chat UI
pip install optopsy[ui]
```

**Requirements:** Python 3.12-3.13, Pandas 2.0+, NumPy 1.26+

## Quick Start

```python
import optopsy as op

# Load your options data
data = op.csv_data(
    "options_data.csv",
    underlying_symbol=0,
    underlying_price=1,
    option_type=2,
    expiration=3,
    quote_date=4,
    strike=5,
    bid=6,
    ask=7,
)

# Backtest long calls and get performance statistics
results = op.long_calls(data)
print(results)
```

**Output:**
```
   dte_range    otm_pct_range  count   mean    std    min    25%    50%    75%    max
0    (0, 7]   (-0.05, -0.0]    505   0.64   1.03  -1.00   0.14   0.37   0.87   7.62
1    (0, 7]    (-0.0, 0.05]    269   2.34   8.65  -1.00  -1.00  -0.89   1.16  68.00
2   (7, 14]   (-0.05, -0.0]    404   1.02   0.68  -0.46   0.58   0.86   1.32   4.40
...
```

Results are grouped by DTE (days to expiration) and OTM% (out-of-the-money percentage), showing descriptive statistics for percentage returns.

## Supported Strategies

| Category | Strategies |
|----------|------------|
| **Single Leg** | `long_calls`, `short_calls`, `long_puts`, `short_puts` |
| **Straddles/Strangles** | `long_straddles`, `short_straddles`, `long_strangles`, `short_strangles` |
| **Vertical Spreads** | `long_call_spread`, `short_call_spread`, `long_put_spread`, `short_put_spread` |
| **Butterflies** | `long_call_butterfly`, `short_call_butterfly`, `long_put_butterfly`, `short_put_butterfly` |
| **Iron Condors** | `iron_condor`, `reverse_iron_condor` |
| **Iron Butterflies** | `iron_butterfly`, `reverse_iron_butterfly` |
| **Covered** | `covered_call`, `protective_put` |
| **Calendar Spreads** | `long_call_calendar`, `short_call_calendar`, `long_put_calendar`, `short_put_calendar` |
| **Diagonal Spreads** | `long_call_diagonal`, `short_call_diagonal`, `long_put_diagonal`, `short_put_diagonal` |

## Documentation

- [Getting Started](https://michaelchu.github.io/optopsy/getting-started/) - Installation and first backtest
- [Strategies](https://michaelchu.github.io/optopsy/strategies/) - All 28 strategies explained
- [Parameters](https://michaelchu.github.io/optopsy/parameters/) - Configuration options reference
- [Entry Signals](https://michaelchu.github.io/optopsy/entry-signals/) - Technical analysis signal filters
- [Chat UI](https://michaelchu.github.io/optopsy/chat-ui/) - AI-powered chat interface
- [Examples](https://michaelchu.github.io/optopsy/examples/) - Common use cases and recipes
- [API Reference](https://michaelchu.github.io/optopsy/api-reference/) - Complete function documentation

## Contributing

Contributions are welcome! See the [Contributing Guide](https://michaelchu.github.io/optopsy/contributing/) for details.

## Disclaimer

Optopsy is intended for research and educational purposes only. Backtest results are based on historical data and simplified assumptions — they do not account for all real-world factors such as liquidity constraints, execution slippage, assignment risk, or changing market conditions. Past performance is not indicative of future results. Always perform your own due diligence before making any trading decisions.

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.
