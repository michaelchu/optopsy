# API Reference

Complete API documentation for Optopsy functions.

!!! info "Common Parameters"
    All strategy functions share common parameters. See the [Common Parameters](#common-parameters) section below for detailed documentation of `max_entry_dte`, `exit_dte`, `max_otm_pct`, `min_bid_ask`, slippage settings, and more.

## Data Loading

#### csv_data

Load options data from CSV file.

::: optopsy.datafeeds.csv_data

---

## Single-Leg Strategies

!!! note
    All single-leg strategies accept the same parameters. See [Common Parameters](#common-parameters) for full documentation.

#### long_calls

::: optopsy.strategies.long_calls

#### short_calls

::: optopsy.strategies.short_calls

#### long_puts

::: optopsy.strategies.long_puts

#### short_puts

::: optopsy.strategies.short_puts

---

## Straddles & Strangles

!!! note
    All straddle/strangle strategies accept the same parameters. See [Common Parameters](#common-parameters) for full documentation.

#### long_straddles

::: optopsy.strategies.long_straddles

#### short_straddles

::: optopsy.strategies.short_straddles

#### long_strangles

::: optopsy.strategies.long_strangles

#### short_strangles

::: optopsy.strategies.short_strangles

---

## Vertical Spreads

!!! note
    All vertical spread strategies accept the same parameters. See [Common Parameters](#common-parameters) for full documentation.

#### long_call_spread

::: optopsy.strategies.long_call_spread

#### short_call_spread

::: optopsy.strategies.short_call_spread

#### long_put_spread

::: optopsy.strategies.long_put_spread

#### short_put_spread

::: optopsy.strategies.short_put_spread

---

## Butterfly Spreads

!!! note
    All butterfly strategies accept the same parameters. See [Common Parameters](#common-parameters) for full documentation.

#### long_call_butterfly

::: optopsy.strategies.long_call_butterfly

#### short_call_butterfly

::: optopsy.strategies.short_call_butterfly

#### long_put_butterfly

::: optopsy.strategies.long_put_butterfly

#### short_put_butterfly

::: optopsy.strategies.short_put_butterfly

---

## Iron Strategies

!!! note
    All iron strategies accept the same parameters. See [Common Parameters](#common-parameters) for full documentation.

#### iron_condor

::: optopsy.strategies.iron_condor

#### reverse_iron_condor

::: optopsy.strategies.reverse_iron_condor

#### iron_butterfly

::: optopsy.strategies.iron_butterfly

#### reverse_iron_butterfly

::: optopsy.strategies.reverse_iron_butterfly

---

## Covered Strategies

!!! note
    All covered strategies accept the same parameters. See [Common Parameters](#common-parameters) for full documentation.

#### covered_call

::: optopsy.strategies.covered_call

#### protective_put

::: optopsy.strategies.protective_put

---

## Calendar Spreads

!!! note
    Calendar spreads have additional timing parameters (`front_dte_min`, `front_dte_max`, `back_dte_min`, `back_dte_max`) in addition to common parameters. See [Common Parameters](#common-parameters) and [Calendar/Diagonal Parameters](#calendardiagonal-parameters) for full documentation.

#### long_call_calendar

::: optopsy.strategies.long_call_calendar

#### short_call_calendar

::: optopsy.strategies.short_call_calendar

#### long_put_calendar

::: optopsy.strategies.long_put_calendar

#### short_put_calendar

::: optopsy.strategies.short_put_calendar

---

## Diagonal Spreads

!!! note
    Diagonal spreads have additional timing parameters (`front_dte_min`, `front_dte_max`, `back_dte_min`, `back_dte_max`) in addition to common parameters. See [Common Parameters](#common-parameters) and [Calendar/Diagonal Parameters](#calendardiagonal-parameters) for full documentation.

#### long_call_diagonal

::: optopsy.strategies.long_call_diagonal

#### short_call_diagonal

::: optopsy.strategies.short_call_diagonal

#### long_put_diagonal

::: optopsy.strategies.long_put_diagonal

#### short_put_diagonal

::: optopsy.strategies.short_put_diagonal

---

## Common Parameters

All strategy functions accept these common parameters:

#### Timing Parameters

- **max_entry_dte** (int, default=90): Maximum days to expiration at entry
- **exit_dte** (int, default=0): Days to expiration at exit
- **dte_interval** (int, default=7): Grouping interval for DTE ranges

#### Filtering Parameters

- **max_otm_pct** (float, default=0.5): Maximum out-of-the-money percentage
- **otm_pct_interval** (float, default=0.05): Grouping interval for OTM ranges
- **min_bid_ask** (float, default=0.05): Minimum bid-ask spread filter

#### Greeks Parameters

- **delta_min** (float, optional): Minimum delta filter
- **delta_max** (float, optional): Maximum delta filter
- **delta_interval** (float, optional): Grouping interval for delta ranges

#### Slippage Parameters

- **slippage** (str, default='mid'): Slippage mode - 'mid', 'spread', or 'liquidity'
- **fill_ratio** (float, default=0.5): Fill ratio for liquidity mode (0.0-1.0)
- **reference_volume** (int, default=1000): Volume threshold for liquid options

#### Output Parameters

- **raw** (bool, default=False): Return raw trade data instead of aggregated stats
- **drop_nan** (bool, default=True): Drop rows with NaN values

#### Calendar/Diagonal Parameters

These strategies have additional timing parameters:

- **front_dte_min** (int, default=20): Minimum DTE for front leg
- **front_dte_max** (int, default=40): Maximum DTE for front leg
- **back_dte_min** (int, default=50): Minimum DTE for back leg
- **back_dte_max** (int, default=90): Maximum DTE for back leg

---

## Return Values

#### Aggregated Results (default)

When `raw=False` (default), strategies return aggregated statistics:

**Columns:**
- `dte_range`: DTE interval group
- `otm_pct_range`: OTM percentage interval group
- `count`: Number of trades in group
- `mean`: Mean return
- `std`: Standard deviation of returns
- `min`: Minimum return
- `25%`: 25th percentile
- `50%`: Median return
- `75%`: 75th percentile
- `max`: Maximum return

#### Raw Trade Data

When `raw=True`, strategies return individual trade details:

**Columns (vary by strategy):**
- `underlying_symbol`: Ticker symbol
- `expiration`: Option expiration date
- `dte_entry`: Days to expiration at entry
- `strike` / `strike_leg1`, `strike_leg2`, etc.: Strike prices
- `entry`: Entry price/cost
- `exit`: Exit price/proceeds
- `pct_change`: Percentage return
- Additional strategy-specific columns

---

## Entry Signals

Functions for filtering strategy entries/exits using technical analysis or custom conditions. See the [Entry Signals](entry-signals.md) page for full usage examples.

#### apply_signal

::: optopsy.signals.apply_signal

#### custom_signal

::: optopsy.signals.custom_signal

#### iv_rank_above

::: optopsy.signals.iv_rank_above

#### iv_rank_below

::: optopsy.signals.iv_rank_below

---

## Simulation

Run chronological strategy simulations with capital tracking, position limits, and equity curve generation.

#### simulate

::: optopsy.simulator.simulate

#### SimulationResult

::: optopsy.simulator.SimulationResult

---

## Risk Metrics

Performance metrics for strategy evaluation. Used by `simulate()` internally and available for standalone use.

#### compute_risk_metrics

::: optopsy.metrics.compute_risk_metrics

#### sharpe_ratio

::: optopsy.metrics.sharpe_ratio

#### sortino_ratio

::: optopsy.metrics.sortino_ratio

#### max_drawdown

::: optopsy.metrics.max_drawdown

#### value_at_risk

::: optopsy.metrics.value_at_risk

#### conditional_value_at_risk

::: optopsy.metrics.conditional_value_at_risk

#### win_rate

::: optopsy.metrics.win_rate

#### profit_factor

::: optopsy.metrics.profit_factor

#### calmar_ratio

::: optopsy.metrics.calmar_ratio

#### omega_ratio

::: optopsy.metrics.omega_ratio

#### tail_ratio

::: optopsy.metrics.tail_ratio

---

## Examples

See the [Examples page](examples.md) for detailed usage examples.

## Type Hints and Validation

All strategy functions use Pydantic-based validation for parameters. Type errors produce clear, field-specific error messages.

```python
import pandas as pd
from typing_extensions import Unpack
from optopsy import StrategyParamsDict

def long_calls(data: pd.DataFrame, **kwargs: Unpack[StrategyParamsDict]) -> pd.DataFrame:
    ...
```

### Exported Types

| Type | Description |
|------|-------------|
| `StrategyParamsDict` | TypedDict for `Unpack[]` annotations on standard strategies |
| `StrategyParams` | Pydantic model for runtime validation of standard strategy parameters |
| `CalendarStrategyParamsDict` | TypedDict for `Unpack[]` annotations on calendar/diagonal strategies |
| `CalendarStrategyParams` | Pydantic model for calendar/diagonal parameters with cross-field validation |

### Using Type Hints

Import `StrategyParamsDict` or `CalendarStrategyParamsDict` for better IDE support:

```python
import optopsy as op
from optopsy import StrategyParamsDict

# Your IDE will now provide autocomplete for all parameters
results = op.iron_condor(
    data,
    max_entry_dte=45,      # Type: int
    exit_dte=21,           # Type: int
    slippage='liquidity',  # Type: Literal['mid', 'spread', 'liquidity']
    fill_ratio=0.5,        # Type: float
)
```

!!! warning "Strict Type Validation"
    Parameters are now validated with Pydantic. Boolean parameters like `raw` must be actual `bool` values — `raw=1` will be rejected. Use `raw=True` instead. Similarly, float parameters like `max_otm_pct` must be `float` — `max_otm_pct=5` will be rejected, use `max_otm_pct=5.0`.