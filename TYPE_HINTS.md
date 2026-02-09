# Type Hints for Strategy Parameters

As of version 2.2.0, Optopsy provides TypedDict definitions for strategy parameters to enable better IDE autocomplete and type checking.

## Usage

### Basic Example

```python
import optopsy as op
from optopsy import StrategyParams

# Type hints enable IDE autocomplete for all parameters
results = op.iron_condor(
    data,
    max_entry_dte=45,      # IDE will show type: int
    exit_dte=21,            # IDE will show type: int
    max_otm_pct=0.25,       # IDE will show type: float
    slippage='liquidity',   # IDE will show valid values: 'mid', 'spread', 'liquidity'
    fill_ratio=0.5,         # IDE will show type: float
)
```

### Type Definitions

#### StrategyParams

Used by all standard strategies (singles, spreads, butterflies, iron condors, etc.):

```python
class StrategyParams(TypedDict, total=False):
    # Timing parameters
    max_entry_dte: int
    exit_dte: int
    dte_interval: int

    # Filtering parameters
    max_otm_pct: float
    otm_pct_interval: float
    min_bid_ask: float

    # Greeks filtering (optional)
    delta_min: Optional[float]
    delta_max: Optional[float]
    delta_interval: Optional[float]

    # Slippage settings
    slippage: Literal["mid", "spread", "liquidity"]
    fill_ratio: float
    reference_volume: int

    # Output control
    raw: bool
    drop_nan: bool
```

#### CalendarStrategyParams

Used by calendar and diagonal spread strategies (extends StrategyParams):

```python
class CalendarStrategyParams(StrategyParams):
    # Additional timing parameters for calendar/diagonal strategies
    front_dte_min: int
    front_dte_max: int
    back_dte_min: int
    back_dte_max: int
```

## Benefits

1. **IDE Autocomplete**: Your IDE will suggest valid parameter names as you type
2. **Type Checking**: Static type checkers (mypy, pyright) can validate parameter types
3. **Documentation**: Hover over parameters to see their types and descriptions
4. **Literal Types**: `slippage` parameter uses `Literal` to show only valid values

## Function Signatures

All strategy functions now use `Unpack[StrategyParams]`:

```python
from typing_extensions import Unpack

def iron_condor(
    data: pd.DataFrame,
    **kwargs: Unpack[StrategyParams]
) -> pd.DataFrame:
    ...
```

This preserves backward compatibility while adding type information. Note that `Unpack` is imported from `typing_extensions` for compatibility with Python 3.8+.

## Exporting Types

The types are exported from the main package:

```python
import optopsy as op

# Access types directly
params: op.StrategyParams = {
    "max_entry_dte": 45,
    "exit_dte": 21,
}

results = op.iron_condor(data, **params)
```

## Backward Compatibility

This change is fully backward compatible:
- Existing code continues to work without modifications
- Type hints are optional and only enhance IDE support
- No runtime validation is performed (TypedDict is a static type only)
