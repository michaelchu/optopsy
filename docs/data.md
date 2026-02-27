# Data Management

Optopsy includes a standalone data package for downloading, caching, and managing historical market data. It works independently of the AI Chat UI — no Chainlit dependency required.

## Installation

```bash
pip install optopsy[data]
```

This installs the `optopsy-data` CLI and the provider/cache system. The `optopsy[ui]` extra includes the data package automatically.

## CLI Reference

### Download Data

Download historical options and stock data from configured providers:

```bash
# Download options data for one or more symbols (requires EODHD_API_KEY)
optopsy-data download SPY
optopsy-data download SPY AAPL TSLA

# Download stock price history instead of options
optopsy-data download SPY --stocks

# Verbose output for debugging
optopsy-data download SPY -v
```

Re-running the download command only fetches new data since your last download — it won't re-download what you already have.

!!! tip "Development"
    If developing with `uv`, prefix commands with `uv run` (e.g., `uv run optopsy-data download SPY`).

### List Available Symbols

Query the provider for symbols with available options data:

```bash
# List all available symbols
optopsy-data symbols

# Search for a specific symbol
optopsy-data symbols -q SPY
```

### Cache Management

Manage the local Parquet cache:

```bash
# Show per-symbol disk usage
optopsy-data cache size

# Clear all cached data
optopsy-data cache clear

# Clear a specific symbol
optopsy-data cache clear SPY
```

## Configuration

Set `EODHD_API_KEY` in your environment or a `.env` file to enable the built-in EODHD provider:

```bash
export EODHD_API_KEY=your-key-here
```

## Cache System

Downloaded data is stored locally as Parquet files at `~/.optopsy/cache/`:

```
~/.optopsy/cache/
├── options/
│   ├── SPY.parquet
│   └── AAPL.parquet
└── stocks/
    ├── SPY.parquet
    └── AAPL.parquet
```

The cache uses smart gap detection — when you re-download a symbol, only missing date ranges are fetched from the API. Interior gaps larger than 5 calendar days trigger a re-fetch for that range. Historical data is treated as immutable (no TTL expiration).

You can override the base data directory with the `OPTOPSY_DATA_DIR` environment variable (default: `~/.optopsy`).

## Data Providers

EODHD is the built-in provider for downloading historical options chains and stock prices via the [EODHD API](https://eodhd.com/financial-apis/options-data-api).

The provider system is pluggable — you can build custom providers by subclassing `DataProvider`:

```python
from optopsy.data.providers.base import DataProvider

class MyProvider(DataProvider):
    name = "my_provider"
    env_key = "MY_PROVIDER_API_KEY"

    def get_tool_schemas(self): ...
    def get_tool_names(self): ...
    async def execute(self, tool_name, arguments): ...
```

Providers are auto-detected when their `env_key` environment variable is set. See the [Plugins](plugins.md) guide for packaging custom providers as installable plugins.
