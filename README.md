![Badge](https://hitscounter.dev/api/hit?url=https%3A%2F%2Fgithub.com%2Fmichaelchu%2Foptopsy&label=Visitors&icon=suitcase-lg&color=%239ec5fe&message=&style=flat&tz=Canada%2FEastern)
![Badge](https://hitscounter.dev/api/hit?url=https%3A%2F%2Fmichaelchu.github.io%2Foptopsy%2F&label=Docs&icon=github&color=%23d2f4ea&message=&style=flat&tz=Canada%2FEastern)
[![CI](https://github.com/goldspanlabs/optopsy/actions/workflows/ci.yml/badge.svg)](https://github.com/goldspanlabs/optopsy/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/optopsy.svg)](https://badge.fury.io/py/optopsy)
[![Python](https://img.shields.io/pypi/pyversions/optopsy)](https://pypi.org/project/optopsy/)



<img src="docs/assets/logo.png" alt="Optopsy" width="150">

A nimble backtesting and statistics library for options strategies.

Optopsy is a Python backtesting engine that lets you go from *"How do 45-DTE iron condors on SPX perform with a 50% profit target and 2x stop loss vs holding to expiration?"* to detailed performance statistics in seconds, not spreadsheets.

[Full Documentation](https://michaelchu.github.io/optopsy/) | [API Reference](https://michaelchu.github.io/optopsy/api-reference/) | [Examples](https://michaelchu.github.io/optopsy/examples/)

## 🤖 Looking for AI/LLM integration?

[optopsy-mcp](https://github.com/goldspanlabs/optopsy-mcp) provides a high-performance MCP server for strategy screening and backtesting. Powered by a complete Rust rewrite of the Optopsy engine, it is specifically built for seamless interaction with Large Language Models.

## Features

- **38 Built-in Strategies** - From simple calls/puts to iron condors, butterflies, condors, ratio spreads, collars, calendars, and diagonals
- **Per-Leg Delta Targeting** - Select strikes by delta with `target, min, max` per leg
- **Trade Simulator** - Chronological simulation with capital tracking, position limits, and equity curves via `simulate()`
- **Portfolio Simulation** - Weighted multi-strategy portfolio backtesting via `simulate_portfolio()`
- **Early Exits** - Stop-loss, take-profit, and max-hold-days rules for automatic position management
- **Commissions** - Model broker fees with per-contract, base fee, and min fee structures
- **Risk Metrics** - Sharpe, Sortino, VaR, CVaR, Calmar, Omega, tail ratio, and more via `compute_risk_metrics()`
- **80+ Entry Signals** - Filter entries with TA indicators (RSI, MACD, Bollinger Bands, EMA, ATR, IV Rank) via [pandas-ta-classic](https://github.com/xgboosted/pandas-ta-classic)
- **Custom Signals** - Use `custom_signal()` to drive entries from any DataFrame with a boolean flag column
- **Slippage Modeling** - Realistic fills with mid, spread, liquidity-based, or per-leg slippage
- **Live Data Providers** - Fetch options chains and stock prices directly from supported data sources (e.g. EODHD)
- **Smart Caching** - Automatic local caching of fetched data with gap detection for efficient re-fetches
- **Plugin System** - Extend with custom strategies, signals, and data providers via entry points

## Installation

```bash
# Core library only (latest stable release)
pip install optopsy

# With Data CLI (download & cache market data)
pip install optopsy[data]
```

**Requirements:** Python 3.12-3.13, Pandas 2.0+, NumPy 1.26+

## Data Management

Optopsy includes a standalone data CLI for downloading and caching historical market data.

```bash
pip install optopsy[data]

# Download historical options data (requires EODHD_API_KEY)
optopsy-data download SPY
optopsy-data download SPY AAPL TSLA

# Download stock price history
optopsy-data download SPY --stocks

# List available symbols
optopsy-data symbols
optopsy-data symbols -q SPY

# Cache management
optopsy-data cache size
optopsy-data cache clear
```

Data is cached locally as Parquet files at `~/.optopsy/cache/`. Re-running download only fetches new data since your last download. See the [Data Management documentation](https://michaelchu.github.io/optopsy/data/) for full details.

## Core Library Quick Start

```python
import optopsy as op

# Load your options data
data = op.csv_data(
    "options_data.csv",
    underlying_symbol=0,
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
   dte_range   delta_range  count   mean    std    min    25%    50%    75%    max
0    (0, 7]   (0.2, 0.3]    505   0.64   1.03  -1.00   0.14   0.37   0.87   7.62
1    (0, 7]   (0.3, 0.4]    269   2.34   8.65  -1.00  -1.00  -0.89   1.16  68.00
2   (7, 14]   (0.2, 0.3]    404   1.02   0.68  -0.46   0.58   0.86   1.32   4.40
...
```

Results are grouped by DTE (days to expiration) and delta range, showing descriptive statistics for percentage returns.

## Simulator

Run a full trade-by-trade simulation with capital tracking, position limits, and performance metrics:

```python
result = op.simulate(
    data,
    op.long_calls,
    capital=100_000,
    quantity=1,
    max_positions=1,
    selector="nearest",       # "nearest", "highest_premium", "lowest_premium", or custom callable
    max_entry_dte=45,
    exit_dte=14,
)

print(result.summary)         # win rate, profit factor, max drawdown, etc.
print(result.trade_log)       # per-trade P&L, entry/exit dates, equity
print(result.equity_curve)    # portfolio value over time
```

The simulator works with all 38 strategies. It selects one trade per entry date, enforces concurrent position limits, and computes a full equity curve with metrics like win rate, profit factor, max drawdown, and average days in trade.

## Supported Strategies

| Category | Strategies |
|----------|------------|
| **Single Leg** | `long_calls`, `short_calls`, `long_puts`, `short_puts` |
| **Straddles/Strangles** | `long_straddles`, `short_straddles`, `long_strangles`, `short_strangles` |
| **Vertical Spreads** | `long_call_spread`, `short_call_spread`, `long_put_spread`, `short_put_spread` |
| **Butterflies** | `long_call_butterfly`, `short_call_butterfly`, `long_put_butterfly`, `short_put_butterfly` |
| **Ratio Spreads** | `call_back_spread`, `put_back_spread`, `call_front_spread`, `put_front_spread` |
| **Iron Condors** | `iron_condor`, `reverse_iron_condor` |
| **Iron Butterflies** | `iron_butterfly`, `reverse_iron_butterfly` |
| **Condors** | `long_call_condor`, `short_call_condor`, `long_put_condor`, `short_put_condor` |
| **Covered & Collar** | `covered_call`, `protective_put`, `collar`, `cash_secured_put` (supports actual stock data via [yfinance](https://github.com/ranaroussi/yfinance)) |
| **Calendar Spreads** | `long_call_calendar`, `short_call_calendar`, `long_put_calendar`, `short_put_calendar` |
| **Diagonal Spreads** | `long_call_diagonal`, `short_call_diagonal`, `long_put_diagonal`, `short_put_diagonal` |

## Documentation

- [Getting Started](https://michaelchu.github.io/optopsy/getting-started/) - Installation and first backtest
- [Strategies](https://michaelchu.github.io/optopsy/strategies/) - All 38 strategies explained
- [Parameters](https://michaelchu.github.io/optopsy/parameters/) - Configuration options reference
- [Entry Signals](https://michaelchu.github.io/optopsy/entry-signals/) - Technical analysis signal filters
- [Data Management](https://michaelchu.github.io/optopsy/data/) - Standalone data CLI and caching
- [Examples](https://michaelchu.github.io/optopsy/examples/) - Common use cases and recipes
- [API Reference](https://michaelchu.github.io/optopsy/api-reference/) - Complete function documentation

## Star History

[![Star History Chart](https://app.repohistory.com/api/svg?repo=goldspanlabs/optopsy&type=Date&background=FFFFFF&color=62C3F8)](https://app.repohistory.com/star-history)

## Disclaimer

Optopsy is intended for research and educational purposes only. Backtest results are based on historical data and simplified assumptions — they do not account for all real-world factors such as liquidity constraints, execution slippage, assignment risk, or changing market conditions. Past performance is not indicative of future results. Always perform your own due diligence before making any trading decisions.

## License

This project is licensed under the GNU Affero General Public License v3.0 - see the [LICENSE](LICENSE) file for details.
