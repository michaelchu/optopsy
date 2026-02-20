# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment Setup

Always use the virtual environment for running commands:

```bash
# Activate the virtual environment before running any commands
source venv/bin/activate
```

## Build & Test Commands

All commands below assume the virtual environment is activated.

```bash
# Install in development mode (core only)
pip install -e .

# Install with UI/chat extras
pip install -e ".[ui]"

# Run all tests
pytest tests/ -v

# Run a specific test file
pytest tests/test_strategies.py -v

# Run tests matching a pattern
pytest tests/ -k "butterfly"

# Check code formatting
black --check optopsy/ tests/ setup.py

# Auto-format code
black optopsy/ tests/ setup.py
```

## Architecture Overview

Optopsy is a backtesting library for options strategies. It processes historical option chain data and generates performance statistics.

### Data Flow

1. **Input**: CSV with option chain data (underlying_symbol, underlying_price, option_type, expiration, quote_date, strike, bid, ask)
2. **Load**: `datafeeds.csv_data()` normalizes and imports the data
3. **Process**: Strategy functions in `strategies.py` call `core._process_strategy()` which:
   - Filters options by DTE, OTM %, bid-ask spread
   - Matches entry/exit prices across dates
   - Builds multi-leg positions via pandas merges
   - Applies strategy-specific rules (strike ordering, butterfly constraints)
   - Calculates P&L and percentage change
4. **Output**: DataFrame with either raw combinations or aggregated statistics (grouped by DTE intervals and OTM ranges)

### Key Modules

- **`strategies.py`** - Public API. Each strategy function (e.g., `long_calls`, `iron_condor`) wraps a helper that calls `_process_strategy()`
- **`core.py`** - Strategy execution engine. `_process_strategy()` orchestrates the pipeline; `_strategy_engine()` handles multi-leg joins
- **`rules.py`** - Strike validation rules (ascending order, butterfly equal-width wings, iron condor/butterfly constraints)
- **`definitions.py`** - Column definitions for 1/2/3/4-leg strategy outputs
- **`checks.py`** - Input validation for parameters and DataFrame dtypes
- **`datafeeds.py`** - CSV import with flexible column mapping

### Adding a New Strategy

1. Add public function in `strategies.py` that calls a helper (or create new helper)
2. Helper should call `_process_strategy()` with appropriate `leg_def`, `rules`, and column definitions
3. Add validation rule in `rules.py` if strategy has strike constraints
4. Update `definitions.py` if new column structure needed
5. Export in `__init__.py`
6. Add tests in `tests/test_strategies.py`

### Side Enum

```python
class Side(Enum):
    long = 1    # Buy (positive multiplier)
    short = -1  # Sell (negative multiplier)
```

Leg definitions use tuples: `(Side.long, _calls, quantity)` where quantity defaults to 1.

## AI Chat UI (`optopsy/ui/`)

An AI-powered chat interface for interactive options backtesting, built on Chainlit + LiteLLM.

### Running

```bash
# Install with UI extras
pip install -e ".[ui]"

# Launch (opens browser)
optopsy-chat

# With options
optopsy-chat run --port 9000 --headless --debug

# Cache management
optopsy-chat cache size          # show disk usage
optopsy-chat cache clear         # clear all cached data
optopsy-chat cache clear SPY     # clear specific symbol
```

### Configuration

Environment variables (set in `.env` or shell):

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | LLM provider API key (default provider) |
| `OPENAI_API_KEY` | Alternative LLM provider |
| `OPTOPSY_MODEL` | Override model (LiteLLM format, default: `anthropic/claude-haiku-4-5-20251001`) |
| `EODHD_API_KEY` | Enable EODHD data provider for live options/stock data |

### Module Structure

- **`cli.py`** — CLI entry point (`optopsy-chat`). Argparse with `run` and `cache` subcommands. Lazy imports so cache commands skip Chainlit startup.
- **`app.py`** — Chainlit web app. Handlers for `on_chat_start`, `on_chat_resume`, `on_message`. Delegates to `OptopsyAgent`.
- **`agent.py`** — `OptopsyAgent` class. Tool-calling loop over LiteLLM with streaming, message compaction (`_COMPACT_THRESHOLD = 300`), and max `_MAX_TOOL_ITERATIONS = 15`.
- **`tools.py`** — Tool registry. Core tools: `load_csv_data`, `list_data_files`, `preview_data`, `run_strategy` (all 28 strategies). Provider tools registered dynamically.

### Data Providers (`optopsy/ui/providers/`)

Pluggable provider system for fetching market data.

- **`base.py`** — Abstract `DataProvider` interface. Requires `name`, `env_key`, `get_tool_schemas()`, `execute(tool_name, arguments)`.
- **`eodhd.py`** — `EODHDProvider`. Fetches options chains and stock prices from EODHD API. Smart caching with gap detection (re-fetches only missing date ranges, interior gap threshold: 5 calendar days).
- **`cache.py`** — `ParquetCache`. File-based cache at `~/.optopsy/cache/{category}/{SYMBOL}.parquet`. Methods: `read()`, `write()`, `merge_and_save()`, `clear()`, `size()`, `total_size_bytes()`. No TTL — historical data is immutable.

### Adding a New Data Provider

1. Subclass `DataProvider` in `providers/`
2. Implement `name`, `env_key`, `get_tool_schemas()`, `get_tool_names()`, `execute()`
3. Register in `providers/__init__.py`
4. Provider is auto-detected if its `env_key` is set
