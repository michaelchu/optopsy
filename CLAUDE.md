# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Test Commands

```bash
# Install in development mode
pip install -e .

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
