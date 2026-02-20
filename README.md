[![CI](https://github.com/michaelchu/optopsy/actions/workflows/ci.yml/badge.svg)](https://github.com/michaelchu/optopsy/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/optopsy.svg)](https://badge.fury.io/py/optopsy)
[![Downloads](https://pepy.tech/badge/optopsy)](https://pepy.tech/project/optopsy)
[![Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

# Optopsy

A fast, flexible backtesting library for options strategies in Python.

Optopsy helps you answer questions like *"How do iron condors perform on SPX?"* or *"What delta range produces the best results for covered calls?"* by generating comprehensive performance statistics from historical options data.

📖 **[Full Documentation](https://michaelchu.github.io/optopsy/)** | [中文版](https://michaelchu.github.io/optopsy/zh/) | [API Reference](https://michaelchu.github.io/optopsy/api-reference/) | [Examples](https://michaelchu.github.io/optopsy/examples/)

## Features

- **28 Built-in Strategies** - From simple calls/puts to iron condors, butterflies, calendars, and diagonals
- **Greeks Filtering** - Filter options by delta to target specific probability ranges
- **Slippage Modeling** - Realistic fills with mid, spread, or liquidity-based slippage
- **Flexible Grouping** - Analyze results by DTE, OTM%, and delta intervals
- **Any Data Source** - Works with any options data in CSV or DataFrame format
- **Pandas Native** - Returns DataFrames that integrate with your existing workflow

## 🤖 AI Chat UI ✨ NEW (Beta)

Optopsy now includes an AI-powered chat interface that lets you fetch data, run backtests, and interpret results using natural language — no code required.

![AI Chat UI](docs/images/chat-ui.png)

**What it does:**
- Fetches historical options data via the [EODHD US Stock Options Data API (1.0.0)](https://eodhd.com/financial-apis/options-data-api) (API key required)
- Runs any of the 28 built-in strategies via conversational prompts
- Explains results and compares strategies side by side
- Works with any OpenAI-compatible LLM (GPT-4o, Claude, Llama, etc. via [LiteLLM](https://github.com/BerriAI/litellm))

**Install and run:**

```bash
pip install optopsy[ui]
```

Create a `.env` file with your API keys (see `.env.example`):

```
ANTHROPIC_API_KEY=sk-...   # or OPENAI_API_KEY for OpenAI models
EODHD_API_KEY=...
```

Defaults to Claude Haiku 4.5 for its low cost and generous rate limits. To use a different model, set `OPTOPSY_MODEL` and the matching API key:

```
OPTOPSY_MODEL=gpt-4o
OPENAI_API_KEY=sk-...
```

Then launch:

```bash
optopsy-chat
```

**Example prompts:**
- *"Fetch AAPL options from the last 3 months and run a short put spread"*
- *"Compare iron condors vs iron butterflies on SPY"*
- *"Show me covered call performance with 30-delta entries"*

## Installation

```bash
# Core library only
pip install optopsy

# With AI Chat UI
pip install optopsy[ui]
```

**Requirements:** Python 3.10+, Pandas 2.0+, NumPy 1.26+

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

## Configuration Options

All strategy functions accept these optional parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `dte_interval` | 7 | Group results by DTE intervals (days) |
| `max_entry_dte` | 90 | Maximum days to expiration at entry |
| `exit_dte` | 0 | Target DTE for exit (0 = expiration) |
| `otm_pct_interval` | 0.05 | OTM percentage interval for grouping |
| `max_otm_pct` | 0.5 | Maximum OTM percentage to consider |
| `min_bid_ask` | 0.05 | Minimum bid/ask to filter out worthless options |
| `raw` | False | Return individual trades instead of grouped stats |
| `slippage` | "mid" | Slippage mode: "mid", "spread", or "liquidity" |
| `fill_ratio` | 0.5 | Base fill ratio for liquidity mode (0.0-1.0) |
| `reference_volume` | 1000 | Volume threshold for liquid options |

### Example: Custom Parameters

```python
# Short puts with 30-60 DTE, held to expiration
results = op.short_puts(
    data,
    dte_interval=30,
    max_entry_dte=60,
    exit_dte=0,
    otm_pct_interval=0.10,
)
```

### Calendar and Diagonal Spread Parameters

Calendar and diagonal spreads use different parameters to manage two expirations:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `front_dte_min` | 20 | Minimum DTE for front (near-term) leg |
| `front_dte_max` | 40 | Maximum DTE for front leg |
| `back_dte_min` | 50 | Minimum DTE for back (longer-term) leg |
| `back_dte_max` | 90 | Maximum DTE for back leg |
| `exit_dte` | 7 | Days before front expiration to exit |

```python
# Long call calendar: short front-month, long back-month at same strike
results = op.long_call_calendar(
    data,
    front_dte_min=25,
    front_dte_max=35,
    back_dte_min=50,
    back_dte_max=70,
    exit_dte=7,
)

# Diagonal spread: different strikes and expirations
results = op.long_call_diagonal(data, raw=True)
```

## Greeks Support

Filter and group options by delta for more precise strategy targeting.

### Loading Data with Greeks

```python
data = op.csv_data(
    "options_with_greeks.csv",
    underlying_symbol=0,
    underlying_price=1,
    option_type=2,
    expiration=3,
    quote_date=4,
    strike=5,
    bid=6,
    ask=7,
    delta=8,  # Optional: column index for delta
)
```

### Delta Filtering

Target specific delta ranges at entry:

```python
# Only 30-delta calls (delta between 0.25 and 0.35)
results = op.long_calls(data, delta_min=0.25, delta_max=0.35)

# High-probability short puts (delta >= -0.20)
results = op.short_puts(data, delta_max=-0.20)

# ATM straddles (delta around 0.50/-0.50)
results = op.long_straddles(data, delta_min=0.45, delta_max=0.55)
```

### Delta Grouping

Analyze performance across delta ranges:

```python
# Group results by 0.10 delta intervals
results = op.long_calls(data, delta_interval=0.10)
```

**Output:**
```
   delta_range  dte_range  otm_pct_range  count   mean    std
0   (0.2, 0.3]   (7, 14]  (-0.10, -0.05]     42  -0.15   0.52
1   (0.3, 0.4]   (7, 14]  (-0.05, -0.00]     48   0.22   0.41
2   (0.4, 0.5]   (7, 14]  (-0.00,  0.05]     35   0.45   0.33
...
```

## Slippage Modeling

Model realistic fill prices with three slippage modes:

| Mode | Description |
|------|-------------|
| `mid` | Uses midpoint price (default) |
| `spread` | Assumes worst-case fill at full bid-ask spread |
| `liquidity` | Adjusts slippage based on volume |

### Basic Usage

```python
# Default: mid-price fills (optimistic)
results = op.long_calls(data)

# Full spread slippage (conservative)
results = op.long_calls(data, slippage="spread")
```

### Liquidity-Based Slippage

For more realistic modeling, use volume data to estimate slippage:

```python
# Load data with volume
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
    volume=9,  # Volume column
)

# Liquidity-based slippage
results = op.iron_condor(
    data,
    slippage="liquidity",
    fill_ratio=0.5,        # Base fill ratio (0.0-1.0)
    reference_volume=1000,  # Volume threshold for "liquid"
)
```

With `liquidity` mode:
- High-volume options get fills closer to mid-price
- Low-volume options get fills closer to the spread edge
- `fill_ratio=0.5` means liquid options fill at 50% of the spread from mid

## Raw Trade Data

Get individual trades instead of grouped statistics:

```python
trades = op.iron_condor(data, raw=True)
print(trades.columns)
# ['underlying_symbol', 'expiration', 'dte_entry', 'strike_leg1',
#  'strike_leg2', 'strike_leg3', 'strike_leg4', 'total_entry_cost',
#  'total_exit_proceeds', 'pct_change', ...]
```

## Data Format

Optopsy expects options chain data with these columns:

| Column | Type | Description |
|--------|------|-------------|
| `underlying_symbol` | string | Ticker symbol (e.g., "SPX") |
| `underlying_price` | float | Price of underlying at quote time |
| `option_type` | string | "call" or "put" (or "c"/"p") |
| `expiration` | datetime | Option expiration date |
| `quote_date` | datetime | Date of the quote |
| `strike` | float | Strike price |
| `bid` | float | Bid price |
| `ask` | float | Ask price |
| `delta` | float | *(Optional)* Delta Greek |

### Using DataFrames Directly

If your data is already in a DataFrame:

```python
import pandas as pd
import optopsy as op

# Your DataFrame just needs the required columns
df = pd.read_csv("my_data.csv")
df.columns = ['underlying_symbol', 'underlying_price', 'option_type',
              'expiration', 'quote_date', 'strike', 'bid', 'ask']
df['expiration'] = pd.to_datetime(df['expiration'])
df['quote_date'] = pd.to_datetime(df['quote_date'])

# Pass directly to strategy functions
results = op.short_strangles(df)
```

## Data Sources

Optopsy works with any historical options data. Some sources:

- [EODHD US Stock Options Data API (1.0.0)](https://eodhd.com/financial-apis/options-data-api) - Built-in integration via the chat UI (API key required)
- [HistoricalOptionData.com](https://historicaloptiondata.com/) - Free samples available
- [CBOE DataShop](https://datashop.cboe.com/) - Official exchange data
- [Polygon.io](https://polygon.io/) - Options data API
- Your broker's data export

## Documentation

See the [Wiki](https://github.com/michaelchu/optopsy/wiki) for detailed API reference and examples.

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

```bash
# Development setup
git clone https://github.com/michaelchu/optopsy.git
cd optopsy
pip install -e ".[ui]"

# Run tests
pytest tests/ -v

# Format code
black optopsy/ tests/
```

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.
